import datetime

import fire
import pycardano

from uada.onchain import parameter_auth_nft, uada
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
    wallet: str = "admin",
):
    # Get payment address
    payment_vkey, payment_skey, payment_address = get_signing_info(
        wallet, network=network
    )
    treasury_vkey, treasury_skey, treasury_address = get_signing_info(
        "treasury", network=network
    )
    (
        auth_nft_script,
        auth_nft_policy_id,
        auth_nft_address,
    ) = get_contract(module_name(parameter_auth_nft), True)

    params_datum = uada.UAdaFeeParams(
        mint_fee_min=1_000_000,
        mint_fee_percent=uada.Fraction(3, 1000),
        withdrawal_fee_min=1_000_000,
        withdrawal_fee_percent=uada.Fraction(3, 1000),
        treasury_address=to_address(treasury_address),
        treasury_out_datum=uada.NoOutputDatum(),
    )
    auth_nft_token = uada.Token(auth_nft_policy_id.payload, b"")

    # Build the transaction
    builder = TransactionBuilder(context)
    builder.add_input_address(payment_address)
    builder.add_output(
        with_min_lovelace(
            TransactionOutput(
                address=payment_address,
                amount=Value(
                    coin=1_000_000, multi_asset=asset_from_token(auth_nft_token, 1)
                ),
                datum=params_datum,
            ),
            context,
        )
    )
    builder.add_minting_script(
        auth_nft_script,
        Redeemer(uada.Nothing()),
    )
    builder.mint = asset_from_token(auth_nft_token, 1)
    builder.required_signers = [payment_vkey.hash()]

    # Sign the transaction
    signed_tx = builder.build_and_sign(
        signing_keys=[payment_skey],
        change_address=payment_address,
    )

    # Submit the transaction
    context.submit_tx(signed_tx)

    show_tx(signed_tx)


if __name__ == "__main__":
    fire.Fire(main)
