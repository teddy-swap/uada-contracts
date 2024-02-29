import os

import blockfrost
import ogmios

import pycardano
from pycardano import Network, OgmiosChainContext

ogmios_host = os.getenv("OGMIOS_API_HOST", "localhost")
ogmios_port = os.getenv("OGMIOS_API_PORT", "1337")
ogmios_protocol = os.getenv("OGMIOS_API_PROTOCOL", "ws")
ogmios_url = f"{ogmios_protocol}://{ogmios_host}:{ogmios_port}"

kupo_host = os.getenv("KUPO_API_HOST", None)
kupo_port = os.getenv("KUPO_API_PORT", "80")
kupo_protocol = os.getenv("KUPO_API_PROTOCOL", "http")
kupo_url = (
    f"{kupo_protocol}://{kupo_host}:{kupo_port}" if kupo_host is not None else None
)

network = Network.TESTNET

blockfrost_project_id = os.getenv("BLOCKFROST_PROJECT_ID", None)
blockfrost_client = blockfrost.BlockFrostApi(
    blockfrost_project_id,
    base_url=blockfrost.ApiUrls.mainnet.value
    if network == Network.MAINNET
    else blockfrost.ApiUrls.preprod.value,
)


# Load chain context
try:
    context = OgmiosChainContext(ogmios_url, network=network, kupo_url=kupo_url)
except Exception as e:
    try:
        context = ogmios.OgmiosChainContext(
            host=ogmios_host,
            port=int(ogmios_port),
            secure=ogmios_protocol == "wss",
        )
    except Exception as e:
        print("No ogmios available")
        context = None


def show_tx(signed_tx: pycardano.Transaction):
    print(f"transaction id: {signed_tx.id}")
    print(
        f"Cardanoscan: https://{'preprod.' if network == Network.TESTNET else ''}cexplorer.io/tx/{signed_tx.id}"
    )
