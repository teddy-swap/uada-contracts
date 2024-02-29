import datetime

import fire
import pycardano

from uada.onchain import uada
from uada.utils.network import show_tx, context
from uada.utils.to_script_context import to_address
from opshin.prelude import Token
from pycardano import (
    OgmiosChainContext,
    TransactionBuilder,
    Redeemer,
    AuxiliaryData,
    AlonzoMetadata,
    Metadata,
    TransactionOutput,
    Value,
)

from .util import (
    token_from_string,
    asset_from_token,
    module_name,
    with_min_lovelace,
    sorted_utxos,
    amount_of_token_in_value,
    SAMPLE_STAKE_KEY,
    combine_with_stake_key,
)
from ..utils import get_signing_info, ogmios_url, network, kupo_url, get_address
from ..utils.contracts import get_contract


def main(
    wallet: str = "minter",
    stake_key: str = SAMPLE_STAKE_KEY,
):
    # Get payment address
    payment_vkey, payment_skey, payment_address = get_signing_info(
        wallet, network=network
    )
    combined_address = combine_with_stake_key(payment_address, stake_key)

    # Build the transaction
    builder = TransactionBuilder(context)
    payment_utxos = context.utxos(payment_address) + context.utxos(combined_address)
    for u in payment_utxos:
        builder.add_input(u)

    trash_address = get_address("trash")
    builder.add_output(
        with_min_lovelace(
            TransactionOutput(
                trash_address,
                Value(
                    0,
                    sum(
                        (u.output.amount.multi_asset for u in payment_utxos),
                        pycardano.MultiAsset(),
                    ),
                ),
            ),
            context,
        )
    )

    # Sign the transaction
    signed_tx = builder.build_and_sign(
        signing_keys=[payment_skey],
        change_address=combined_address,
    )

    # Submit the transaction
    context.submit_tx(signed_tx)

    show_tx(signed_tx)


if __name__ == "__main__":
    fire.Fire(main)
