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
from ..utils import get_signing_info, ogmios_url, network, kupo_url
from ..utils.contracts import get_contract
from pycardano.crypto import bech32


def main(
    wallet: str = "minter",
    stake_key: str = SAMPLE_STAKE_KEY,
):
    # Get payment address
    payment_vkey, payment_skey, payment_address = get_signing_info(
        wallet, network=network
    )
    (
        uada_script,
        uada_policy_id,
        uada_address,
    ) = get_contract(module_name(uada), True)
    uada_staking_address = pycardano.Address(
        staking_part=uada_address.payment_part, network=network
    )
    combined_payment_address = combine_with_stake_key(payment_address, stake_key)

    uada_registration_cert = pycardano.StakeRegistration(
        pycardano.StakeCredential(uada_staking_address.staking_part)
    )

    # Build the transaction
    builder = TransactionBuilder(context)
    builder.add_input_address(combined_payment_address)
    builder.add_input_address(payment_address)
    builder.certificates = [uada_registration_cert]

    # Sign the transaction
    signed_tx = builder.build_and_sign(
        signing_keys=[payment_skey],
        change_address=combined_payment_address,
    )

    # Submit the transaction
    context.submit_tx(signed_tx)

    show_tx(signed_tx)


if __name__ == "__main__":
    fire.Fire(main)
