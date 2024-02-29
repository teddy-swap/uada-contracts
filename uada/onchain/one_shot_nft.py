"""
NFT with a unique name that can only be minted once.
"""

from uada.onchain.util import *


def bytes_big_from_unsigned_int(b: int) -> bytes:
    """Converts an integer into the corresponding bytestring, big/network byteorder, unsigned"""
    assert b >= 0
    if b == 0:
        return b"\x00"
    acc = b""
    while b > 0:
        acc = cons_byte_string(b % 256, acc)
        b //= 256
    return acc


def one_shot_nft_name(spent_utxo: TxOutRef) -> TokenName:
    return sha2_256(bytes_big_from_unsigned_int(spent_utxo.idx) + spent_utxo.id.tx_id)


def validator(unique_utxo_index: int, context: ScriptContext) -> None:
    """
    One-shot minting policy. Ensures that the name of the resulting NFT is unique,
    being the hash of a consumed UTxO.
    """
    policy_id = get_minting_purpose(context).policy_id

    if unique_utxo_index < 0:
        # A negative utxo index indicates that the token should be burned
        # which is always fine (as long as it is actually a burn)
        assert all(
            [
                name_amount[1] < 0
                for name_amount in context.tx_info.mint[policy_id].items()
            ]
        ), "Trying to mint in burn tx"
    else:
        # Check that
        # 1. only one token of the own policy id is minted
        # 2. the tokenname is the hash of the spent UTxO indicated by the redeemer

        spent_input = context.tx_info.inputs[unique_utxo_index].out_ref
        required_token_name = one_shot_nft_name(spent_input)

        check_mint_exactly_one_with_name(
            context.tx_info.mint, policy_id, required_token_name
        )
