import json
import os
import time
import requests
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger()

# Paths
INFRASTRUCTURE_PATH = "namada/infrastructure.json"
EXTERNAL_REPO_PATH = "external-repo/user-and-dev-tools/mainnet"

def fetch_masp_indexer_data(masp_indexer):
    """
    Fetch and update data for MASP indexers.
    """
    try:
        response = requests.get(f"{masp_indexer['url']}/api/v1/height", timeout=10)
        if response.status_code == 200:
            masp_indexer.update({
                "latest_block_height": response.json().get("block_height"),
                "active": True
            })
        else:
            raise Exception("Invalid response code")
    except Exception:
        masp_indexer.update({
            "latest_block_height": None,
            "active": False
        })
    masp_indexer["last_check"] = int(time.time())

def fetch_rpc_data(rpc):
    """
    Fetch and update data for RPCs.
    """
    try:
        response = requests.get(f"{rpc['url']}/status", timeout=10)
        if response.status_code == 200:
            data = response.json().get("result", {})
            node_info = data.get("node_info", {})
            sync_info = data.get("sync_info", {})

            rpc.update({
                "earliest_block_height": sync_info.get("earliest_block_height"),
                "latest_block_height": sync_info.get("latest_block_height"),
                "indexer": node_info.get("other", {}).get("tx_index"),
                "network": node_info.get("network"),
                "catchup": sync_info.get("catching_up", False),
                "active": True
            })
        else:
            raise Exception("Invalid response code")
    except Exception:
        rpc.update({
            "earliest_block_height": None,
            "latest_block_height": None,
            "indexer": None,
            "network": None,
            "catchup": None,
            "active": False
        })
    rpc["last_check"] = int(time.time())

def fetch_namada_indexer_data(namada_indexer):
    """
    Fetch and update data for Namada indexers.
    """
    try:
        response = requests.get(f"{namada_indexer['url']}/api/v1/chain/block/latest", timeout=10)
        if response.status_code == 200:
            latest_block_height = response.json().get("block")
            params_response = requests.get(f"{namada_indexer['url']}/api/v1/chain/parameters", timeout=10)
            network = params_response.json().get("chainId") if params_response.status_code == 200 else None

            namada_indexer.update({
                "latest_block_height": latest_block_height,
                "network": network,
                "active": True
            })
        else:
            raise Exception("Invalid response code")
    except Exception:
        namada_indexer.update({
            "latest_block_height": None,
            "network": None,
            "active": False
        })
    namada_indexer["last_check"] = int(time.time())

def update_data():
    """
    Update infrastructure.json with local and external repository data.
    """
    # Load local infrastructure.json
    with open(INFRASTRUCTURE_PATH, "r") as f:
        infrastructure_data = json.load(f)

    # Update MASP Indexers
    masp_indexers_data = []
    for filename in os.listdir(EXTERNAL_REPO_PATH):
        if filename == "masp-indexers.json":
            external_file_path = os.path.join(EXTERNAL_REPO_PATH, filename)
            with open(external_file_path, "r") as f:
                masp_indexers_data = json.load(f)
            break  # Only fetch this file once

    for masp_indexer in infrastructure_data.get("masp_indexers", []):
        fetch_masp_indexer_data(masp_indexer)

    # Update RPCs
    rpc_data = []
    for filename in os.listdir(EXTERNAL_REPO_PATH):
        if filename == "rpc.json":
            external_file_path = os.path.join(EXTERNAL_REPO_PATH, filename)
            with open(external_file_path, "r") as f:
                rpc_data = json.load(f)
            break  # Only fetch this file once

    for rpc in infrastructure_data.get("rpc", []):
        fetch_rpc_data(rpc)

    # Update Namada Indexers
    namada_indexers_data = []
    for filename in os.listdir(EXTERNAL_REPO_PATH):
        if filename == "namada-indexers.json":
            external_file_path = os.path.join(EXTERNAL_REPO_PATH, filename)
            with open(external_file_path, "r") as f:
                namada_indexers_data = json.load(f)
            break  # Only fetch this file once

    for namada_indexer in infrastructure_data.get("namada_indexers", []):
        fetch_namada_indexer_data(namada_indexer)

    # Save updated infrastructure.json
    with open(INFRASTRUCTURE_PATH, "w") as f:
        json.dump(infrastructure_data, f, indent=4)

if __name__ == "__main__":
    update_data()
