import datetime

import fire
import pycardano

from uada.onchain import uada, one_shot_nft, parameter_auth_nft
from uada.utils.from_script_context import from_address
from uada.utils.network import show_tx, context
from uada.utils.to_script_context import to_address, to_tx_out_ref
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
    Withdrawals,
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
from ..utils.contracts import get_contract, get_ref_utxo


def main(
    wallet: str = "minter",
    stake_key: str = SAMPLE_STAKE_KEY,
    admin_wallet: str = "admin",
    # put positive number for extending, negative for withdrawing
    amount_to_mint: int = 2_000_000,
):
    # Load script info
    (
        uada_script,
        uada_policy_id,
        uada_address,
    ) = get_contract(module_name(uada), True)
    uada_ref_utxo = get_ref_utxo(uada_script, context)
    (
        one_shot_nft_script,
        one_shot_nft_policy_id,
        _,
    ) = get_contract(module_name(one_shot_nft), True)
    (
        _,
        auth_nft_policy_id,
        _,
    ) = get_contract(module_name(parameter_auth_nft), True)

    # Get payment address
    payment_vkey, payment_skey, payment_address = get_signing_info(
        wallet, network=network
    )
    combined_payment_address = combine_with_stake_key(payment_address, stake_key)

    admin_vkey, admin_skey, admin_address = get_signing_info(
        admin_wallet, network=network
    )

    combined_uada_address = combine_with_stake_key(uada_address, stake_key)
    # find the uada staking position
    uada_position_utxo = None
    uada_position_datum = None
    for utxo in context.utxos(combined_uada_address):
        try:
            uada_position_datum = uada.UAdaStakingPosition.from_cbor(
                utxo.output.datum.cbor
            )
        except Exception:
            continue
        if uada_position_datum.policy_id != one_shot_nft_policy_id.payload:
            continue
        uada_position_utxo = utxo
        break
    assert uada_position_utxo is not None, "No uada staking position found"

    payment_utxos = context.utxos(combined_payment_address)
    # find the own input with the unique nft
    unique_nft_utxo = None
    for utxo in payment_utxos:
        if utxo.output.amount.multi_asset.get(one_shot_nft_policy_id, {}).get(
            pycardano.AssetName(uada_position_datum.token_name)
        ):
            unique_nft_utxo = utxo
            break
    assert unique_nft_utxo is not None, "No unique nft found"

    all_utxos_sorted = sorted_utxos(payment_utxos + [uada_position_utxo])
    unique_nft_input_index = all_utxos_sorted.index(unique_nft_utxo)
    spending_redeemer = Redeemer(
        uada.WithdrawUAdaStakingPosition(
            unique_nft_input_index=unique_nft_input_index,
        )
    )

    # find the fee parameters
    param_utxo = None
    auth_nft_datum = None
    for utxo in context.utxos(admin_address):
        if not utxo.output.amount.multi_asset.get(auth_nft_policy_id):
            continue
        try:
            auth_nft_datum = uada.UAdaFeeParams.from_cbor(utxo.output.datum.cbor)
        except Exception:
            continue
        param_utxo = utxo
    assert auth_nft_datum is not None, "No auth nft found"
    treasury_address = from_address(auth_nft_datum.treasury_address)
    if isinstance(auth_nft_datum.treasury_out_datum, uada.NoOutputDatum):
        treasury_out_datum = None
        treasury_out_datum_hash = None
    elif isinstance(auth_nft_datum.treasury_out_datum, uada.SomeOutputDatum):
        treasury_out_datum = auth_nft_datum.treasury_out_datum.datum
        treasury_out_datum_hash = pycardano.datum_hash(treasury_out_datum)
    else:
        treasury_out_datum = None
        treasury_out_datum_hash = auth_nft_datum.treasury_out_datum.datum_hash
    fee_min = auth_nft_datum.mint_fee_min
    fee_percent = auth_nft_datum.mint_fee_percent
    fee = uada.compute_fee(amount_to_mint, fee_percent, fee_min)

    all_ref_utxos_sorted = sorted_utxos(
        [param_utxo] + ([uada_ref_utxo] if uada_ref_utxo else [])
    )
    param_utxo_index = all_ref_utxos_sorted.index(param_utxo)

    uada_mint_redeemer = Redeemer(uada.Nothing())
    uada_wdrl_redeemer = Redeemer(
        uada.ContractInteractionRedeemer(
            parameter_auth_nft_ref_utxo_index=param_utxo_index,
            treasury_payout_tx_out_index=0,
        )
    )

    uada_token = Token(
        uada_policy_id.payload,
        b"uADA",
    )

    # Build the transaction
    builder = TransactionBuilder(context)
    builder.auxiliary_data = AuxiliaryData(
        data=AlonzoMetadata(
            metadata=Metadata({674: {"msg": ["Extend/PartialWithdraw uADA"]}})
        )
    )
    for u in payment_utxos:
        builder.add_input(u)

    builder.add_script_input(
        uada_position_utxo,
        uada_ref_utxo or uada_script,
        None,
        spending_redeemer,
    )
    builder.add_minting_script(
        uada_ref_utxo or uada_script,
        uada_mint_redeemer,
    )
    builder.mint = asset_from_token(uada_token, amount_to_mint)
    builder.reference_inputs.add(param_utxo)
    if fee >= 1_000_000:
        builder.add_output(
            TransactionOutput(
                address=treasury_address,
                amount=Value(
                    coin=fee,
                ),
                datum=treasury_out_datum,
                datum_hash=treasury_out_datum_hash,
            ),
        )
    if uada_position_utxo.output.amount.coin + amount_to_mint != 0:
        builder.add_output(
            TransactionOutput(
                address=uada_position_utxo.output.address,
                amount=uada_position_utxo.output.amount.coin + amount_to_mint,
                datum=uada_position_datum,
            ),
        )
    builder.withdrawals = Withdrawals(
        {
            bytes(
                pycardano.Address(
                    staking_part=uada_address.payment_part, network=network
                )
            ): 0
        }
    )
    builder.add_withdrawal_script(uada_ref_utxo or uada_script, uada_wdrl_redeemer)

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
