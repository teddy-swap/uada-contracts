from opshin.prelude import *
from uada.onchain.utils.ext_interval import *
from opshin.std.builtins import *

EMTPY_TOKENNAME_DICT: Dict[bytes, int] = {}
EMPTY_VALUE_DICT: Value = {}


def get_minting_purpose(context: ScriptContext) -> Minting:
    purpose = context.purpose
    assert isinstance(purpose, Minting)
    return purpose


def get_spending_purpose(context: ScriptContext) -> Spending:
    purpose = context.purpose
    assert isinstance(purpose, Spending)
    return purpose


def get_script_hash(context: ScriptContext) -> bytes:
    purpose = context.purpose
    if isinstance(purpose, Minting):
        return purpose.policy_id
    elif isinstance(purpose, Spending):
        own_address = own_spent_utxo(context.tx_info.inputs, purpose).address
        return own_address.payment_credential.credential_hash
    elif isinstance(purpose, Rewarding):
        staking_credential = purpose.staking_credential
        assert isinstance(staking_credential, StakingHash), "Invalid staking credential"
        return staking_credential.value.credential_hash
    assert False, "Invalid purpose"
    return b""


@dataclass
class UAdaStakingPosition(PlutusData):
    """
    Position that locks ADA, can be redeemed by owner of the NFT
    """

    CONSTR_ID = 1
    # the fields specify the token that is able to unlock the staking position
    policy_id: PolicyId
    token_name: TokenName


def merge_without_duplicates(a: List[bytes], b: List[bytes]) -> List[bytes]:
    """
    Merge two lists without duplicates
    Note: The cost of this is O(n^2), can we assume that the lists are small?
    Rough estimate allows 1000 bytes / 32 bytes per policy id ~ 31 policy ids
    However for token names no lower bound on the length is given, so we assume 1000 bytes / 1 byte per token name ~ 1000 token names
    """
    return [x for x in a if not x in b] + b


def _subtract_token_names(
    a: Dict[TokenName, int], b: Dict[TokenName, int]
) -> Dict[TokenName, int]:
    """
    Subtract b from a, return a - b
    """
    if not b:
        return a
    elif not a:
        return {tn_amount[0]: -tn_amount[1] for tn_amount in b.items()}
    return {
        tn: a.get(tn, 0) - b.get(tn, 0)
        for tn in merge_without_duplicates(a.keys(), b.keys())
    }


def subtract_value(a: Value, b: Value) -> Value:
    """
    Subtract b from a, return a - b
    """
    if not b:
        return a
    elif not a:
        return {
            pid_tokens[0]: {
                tn_amount[0]: -tn_amount[1] for tn_amount in pid_tokens[1].items()
            }
            for pid_tokens in b.items()
        }
    return {
        pid: _subtract_token_names(
            a.get(pid, EMTPY_TOKENNAME_DICT), b.get(pid, EMTPY_TOKENNAME_DICT)
        )
        for pid in merge_without_duplicates(a.keys(), b.keys())
    }


def _add_token_names(
    a: Dict[TokenName, int], b: Dict[TokenName, int]
) -> Dict[TokenName, int]:
    """
    Add b to a, return a + b
    """
    if not a:
        return b
    if not b:
        return a
    return {
        tn: a.get(tn, 0) + b.get(tn, 0)
        for tn in merge_without_duplicates(a.keys(), b.keys())
    }


def add_value(a: Value, b: Value) -> Value:
    """
    Add b to a, return a + b
    """
    if not a:
        return b
    if not b:
        return a
    return {
        pid: _add_token_names(
            a.get(pid, EMTPY_TOKENNAME_DICT), b.get(pid, EMTPY_TOKENNAME_DICT)
        )
        for pid in merge_without_duplicates(a.keys(), b.keys())
    }


def total_value(value_store_inputs: List[TxOut]) -> Value:
    """
    Calculate the total value of all inputs
    """
    total_value = EMPTY_VALUE_DICT
    for txo in value_store_inputs:
        total_value = add_value(total_value, txo.value)
    return total_value


def check_mint_exactly_n_with_name(
    mint: Value, n: int, policy_id: PolicyId, required_token_name: TokenName
) -> None:
    """
    Check that exactly n token with the given name is minted
    from the given policy
    """
    assert mint[policy_id][required_token_name] == n, "Exactly n token must be minted"
    assert len(mint[policy_id]) == 1, "No other token must be minted"


def check_mint_exactly_one_with_name(
    mint: Value, policy_id: PolicyId, required_token_name: TokenName
) -> None:
    """
    Check that exactly one token with the given name is minted
    from the given policy
    """
    check_mint_exactly_n_with_name(mint, 1, policy_id, required_token_name)


def token_present_in_output(
    token: Union[Token, UAdaStakingPosition], output: TxOut
) -> bool:
    """
    Returns whether the given token is contained in the output
    """
    return (
        output.value.get(token.policy_id, EMTPY_TOKENNAME_DICT).get(token.token_name, 0)
        > 0
    )


def only_one_input_from_address(address: Address, inputs: List[TxInInfo]) -> bool:
    return sum([int(i.resolved.address == address) for i in inputs]) == 1


def only_one_output_to_address(address: Address, outputs: List[TxOut]) -> bool:
    return sum([int(i.address == address) for i in outputs]) == 1


def user_signed_tx(address: Address, tx_info: TxInfo) -> bool:
    return address.payment_credential.credential_hash in tx_info.signatories
