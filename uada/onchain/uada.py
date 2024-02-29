from uada.onchain.util import *
from uada.onchain.utils.ext_fraction import *


@dataclass
class WithdrawUAdaStakingPosition(PlutusData):
    CONSTR_ID = 1
    unique_nft_input_index: int


@dataclass
class ContractInteractionRedeemer(PlutusData):
    CONSTR_ID = 2
    parameter_auth_nft_ref_utxo_index: int
    treasury_payout_tx_out_index: int


@dataclass
class UAdaFeeParams(PlutusData):
    """
    Parameters for the UAda fee contract
    Fees in ADA that are charged for minting and withdrawing
    """

    CONSTR_ID = 5
    mint_fee_min: int
    mint_fee_percent: Union[Fraction, Nothing]
    withdrawal_fee_min: int
    withdrawal_fee_percent: Union[Fraction, Nothing]
    treasury_address: Address
    treasury_out_datum: OutputDatum


UAdaRedeemer = Union[WithdrawUAdaStakingPosition, Nothing, ContractInteractionRedeemer]


def all_lovelace_unlocked_from_script(
    script_credential: ScriptCredential,
    tx_info: TxInfo,
) -> int:
    """
    Return the total amount of tokens unlocked from the script.
    """
    inputs = tx_info.inputs
    total = 0
    for tx_out in inputs:
        resolved = tx_out.resolved
        payment_cred = resolved.address.payment_credential
        if script_credential == payment_cred:
            total += resolved.value.get(b"", EMTPY_TOKENNAME_DICT).get(b"", 0)
    return total


def all_lovelace_locked_in_script(
    script_credential: ScriptCredential,
    tx_info: TxInfo,
) -> int:
    """
    Return the total amount of tokens locked in the script.
    """
    outputs = tx_info.outputs
    total = 0
    for tx_out in outputs:
        payment_cred = tx_out.address.payment_credential
        if script_credential == payment_cred:
            total += tx_out.value.get(b"", EMTPY_TOKENNAME_DICT).get(b"", 0)
    return total


def check_withdrawal_invoked(
    own_script_credential: ScriptCredential,
    tx_info: TxInfo,
):
    """
    Check if the withdrawal is invoked
    """
    own_staking_credential = StakingHash(own_script_credential)
    assert (
        own_staking_credential in tx_info.wdrl.keys()
    ), "Staking credential missing in withdrawal map"


def compute_fee(
    volume: int,
    fee_percent: Union[Fraction, Nothing],
    min_fee: int,
) -> int:
    """
    Compute the fee for a given volume, fee percent and minimum fee
    """
    expected_fee = min_fee
    if isinstance(fee_percent, Fraction):
        fraction_fee = ceil_fraction(mul_fraction_int(fee_percent, volume))
        if fraction_fee > expected_fee:
            expected_fee = fraction_fee
    return expected_fee


def check_pays_fee_to_treasury(
    volume: int,
    fee_percent: Union[Fraction, Nothing],
    min_fee: int,
    txouts: List[TxOut],
    payout_index: int,
    treasury_address: Address,
    treasury_out_datum: OutputDatum,
) -> None:
    expected_fee = compute_fee(volume, fee_percent, min_fee)

    if expected_fee >= 1_000_000:
        payout_tx_out = txouts[payout_index]
        assert treasury_address == payout_tx_out.address, "Fee not paid to treasury"
        assert treasury_out_datum == payout_tx_out.datum, "Payout datum is incorrect"
        assert (
            payout_tx_out.value[b""][b""] >= expected_fee
        ), "Not enough lovelace paid to treasury"


def validator(
    parameter_auth_nft_policy_id: PolicyId,
    datum: Union[UAdaStakingPosition, Nothing],
    redeemer: UAdaRedeemer,
    context: ScriptContext,
) -> None:
    """
    Validator for uADA
    :param one_shot_nft_policy_id: The policy id of the one-shot NFT that controls spending of staking positions
    :param datum: The datum attached to a staking position, if invoked as a spending transaction
    :param redeemer: The redeemer attached to the transaction, only relevant to spending and specifies the input that holds the unique NFT
    :param context: The context of the transaction
    :return: Either fails with an error message or returns successfully
    """
    tx_info = context.tx_info
    purpose = context.purpose
    own_script_hash = get_script_hash(context)
    own_script_credential = ScriptCredential(own_script_hash)

    if isinstance(purpose, Minting):
        # In any case, the staking credential must be present in the withdrawal map
        # It controls the circulating supply invariant

        check_withdrawal_invoked(own_script_credential, tx_info)

        # No need to validate anything further (withdrawal takes care of the circulating supply invariant)
        pass

    elif (
        isinstance(purpose, Spending)
        and isinstance(datum, UAdaStakingPosition)
        and isinstance(redeemer, WithdrawUAdaStakingPosition)
    ):
        # In any case, the staking credential must be present in the withdrawal map
        # It controls the circulating supply invariant

        check_withdrawal_invoked(own_script_credential, tx_info)

        # Verify that the nft given in the datum is present in a spent input

        spent_input = tx_info.inputs[redeemer.unique_nft_input_index]
        assert token_present_in_output(
            datum, spent_input.resolved
        ), "Unique NFT not present in spent input"
    elif isinstance(purpose, Rewarding) and isinstance(
        redeemer, ContractInteractionRedeemer
    ):
        # In this case, the withdrawal was obviously invoked (it is being invoked in this branch)

        # Verify the circulating supply invariant
        uada_policy_id: PolicyId = own_script_hash
        uada_token_name: TokenName = b"uADA"

        tokens_unlocked_from_contract = all_lovelace_unlocked_from_script(
            own_script_credential, tx_info
        )
        tokens_locked_in_contract = all_lovelace_locked_in_script(
            own_script_credential, tx_info
        )
        expected_diff = tokens_locked_in_contract - tokens_unlocked_from_contract
        check_mint_exactly_n_with_name(
            tx_info.mint, expected_diff, uada_policy_id, uada_token_name
        )

        # Verify that the fee is being paid to the treasury
        params_ref_input = tx_info.reference_inputs[
            redeemer.parameter_auth_nft_ref_utxo_index
        ].resolved
        assert token_present_in_output(
            Token(parameter_auth_nft_policy_id, b""), params_ref_input
        ), "Auth NFT not present in parameter reference input"
        fee_params: UAdaFeeParams = resolve_datum_unsafe(
            params_ref_input,
            tx_info,
        )
        if expected_diff < 0:
            check_pays_fee_to_treasury(
                -expected_diff,
                fee_params.withdrawal_fee_percent,
                fee_params.withdrawal_fee_min,
                tx_info.outputs,
                redeemer.treasury_payout_tx_out_index,
                fee_params.treasury_address,
                fee_params.treasury_out_datum,
            )
        else:
            check_pays_fee_to_treasury(
                expected_diff,
                fee_params.mint_fee_percent,
                fee_params.mint_fee_min,
                tx_info.outputs,
                redeemer.treasury_payout_tx_out_index,
                fee_params.treasury_address,
                fee_params.treasury_out_datum,
            )
    else:
        assert False, "Invalid purpose, datum or redeemer combination"
