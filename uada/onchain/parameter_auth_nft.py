"""
NFT that authenticates the parameter of the UAda contract
Can only be minted by the admin and until the latest mint time (to ensure that no further minting is possible)
"""

from uada.onchain.util import *
from uada.onchain.utils.ext_interval import *


def validator(
    admin: PubKeyHash,
    latest_mint_time: int,
    _: Nothing,
    context: ScriptContext,
) -> None:
    """
    Validator for the parameter authentication NFT
    """
    policy_id = get_minting_purpose(context).policy_id
    tx_info = context.tx_info

    # Check that

    # 1. only one token of the own policy id is minted
    # 2. the tokenname is empty
    check_mint_exactly_one_with_name(tx_info.mint, policy_id, b"")

    # 3. the signature of the admin is present
    assert admin in tx_info.signatories, "Admin signature missing"

    # 4. the mint time is before the latest mint time
    assert before_ext(
        tx_info.valid_range, FinitePOSIXTime(latest_mint_time)
    ), "Mint time is after the latest mint time"
