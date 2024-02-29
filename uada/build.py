import datetime
import subprocess
from math import ceil

import fire
import sys
from pathlib import Path
from typing import Union

from uplc.ast import PlutusByteString, plutus_cbor_dumps, PlutusInteger

from uada.offchain.util import module_name
from uada.utils import get_signing_info, network
from .utils.contracts import get_contract

from uada.onchain import (
    uada,
    one_shot_nft,
    parameter_auth_nft,
)


def build_compressed(
    type: str, script: Union[Path, str], cli_options=("--cf",), args=()
):
    script = Path(script)
    command = [
        sys.executable,
        "-m",
        "opshin",
        *cli_options,
        "build",
        type,
        script,
        *args,
        "--recursion-limit",
        "2000",
    ]
    subprocess.run(command)

    built_contract = Path(f"build/{script.stem}/script.cbor")
    built_contract_compressed_cbor = Path(f"build/tmp.cbor")

    with built_contract_compressed_cbor.open("wb") as fp:
        subprocess.run(["plutonomy-cli", built_contract, "--default"], stdout=fp)

    subprocess.run(
        [
            sys.executable,
            "-m",
            "uplc",
            "build",
            "--from-cbor",
            built_contract_compressed_cbor,
            "-o",
            f"build/{script.stem}_compressed",
            "--recursion-limit",
            "2000",
        ]
    )


def main(
    admin_wallet: str = "admin",
    latest_mint_time: datetime.datetime = datetime.datetime.now()
    + datetime.timedelta(days=30),
):
    build_compressed(
        "minting",
        one_shot_nft.__file__,
    )

    admin_vkey, admin_skey, admin_address = get_signing_info(
        admin_wallet, network=network
    )
    build_compressed(
        "minting",
        parameter_auth_nft.__file__,
        args=[
            plutus_cbor_dumps(PlutusByteString(admin_vkey.hash().payload)).hex(),
            plutus_cbor_dumps(
                PlutusInteger(ceil(latest_mint_time.timestamp()) * 1000)
            ).hex(),
        ],
    )

    _, parameter_auth_nft_policy_id, _ = get_contract(
        module_name(parameter_auth_nft), True
    )
    build_compressed(
        "any",
        uada.__file__,
        args=[
            plutus_cbor_dumps(
                PlutusByteString(parameter_auth_nft_policy_id.payload)
            ).hex(),
        ],
        cli_options=("--cf", "--force-three-params"),
    )


if __name__ == "__main__":
    fire.Fire(main)
