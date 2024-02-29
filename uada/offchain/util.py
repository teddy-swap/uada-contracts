from pathlib import Path
from typing import List

import pycardano

from opshin.prelude import Token
from pycardano import MultiAsset, ScriptHash, Asset, AssetName, Value, Network
from uada.utils import network

SAMPLE_STAKE_KEY = (
    "stake_test1uz7lwepxz9v0ks5tmx6m6nt436jm9c9r88mdlsydt70vnng9sr59q"
    if network == Network.TESTNET
    else "stake1uyhs4xn8355pjxw7tgfnaqty7q8sgf2k2t5dwx2w9mhm38cdufzdg"
)


def token_from_string(token: str) -> Token:
    if token == "lovelace":
        return Token(b"", b"")
    policy_id, token_name = token.split(".")
    return Token(
        policy_id=bytes.fromhex(policy_id),
        token_name=bytes.fromhex(token_name),
    )


def asset_from_token(token: Token, amount: int) -> MultiAsset:
    return MultiAsset(
        {ScriptHash(token.policy_id): Asset({AssetName(token.token_name): amount})}
    )


def module_name(module):
    return Path(module.__file__).stem


def with_min_lovelace(
    output: pycardano.TransactionOutput, context: pycardano.ChainContext
):
    min_lvl = pycardano.min_lovelace(context, output)
    output.amount.coin = max(output.amount.coin, min_lvl + 500000)
    return output


def sorted_utxos(txs: List[pycardano.UTxO]):
    return sorted(
        txs,
        key=lambda u: (u.input.transaction_id.payload, u.input.index),
    )


def amount_of_token_in_value(
    token: Token,
    value: Value,
) -> int:
    return value.multi_asset.get(ScriptHash(token.policy_id), {}).get(
        AssetName(token.token_name), 0
    )


def combine_with_stake_key(
    address: pycardano.Address, stake_key: str
) -> pycardano.Address:
    return pycardano.Address(
        address.payment_part,
        pycardano.Address.from_primitive(stake_key).staking_part,
        network=address.network,
    )
