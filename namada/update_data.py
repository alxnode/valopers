import json
import os
import time
import requests
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
    except Exception as e:
        logger.error(f"Error fetching MASP indexer data: {e}")
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
    except Exception as e:
        logger.error(f"Error fetching RPC data: {e}")
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
    except Exception as e:
        logger.error(f"Error fetching Namada indexer data: {e}")
        namada_indexer.update({
            "latest_block_height": None,
            "network": None,
            "active": False
        })
    namada_indexer["last_check"] = int(time.time())

def merge_external_data(infrastructure_data, external_data, section):
    """
    Merge missing indexer/RPC data from external files into infrastructure data.
    """
    existing_urls = {item['url']: item for item in infrastructure_data.get(section, [])}

    for external_item in external_data:
        url = external_item.get("url")
        if url in existing_urls:
            # Update existing entry
            logger.info(f"Updating {section} for {url}")
            existing_urls[url].update(external_item)
        else:
            # Add new entry if not present
            logger.info(f"Adding new {section} for {url}")
            infrastructure_data[section].append(external_item)

def update_data():
    """
    Update infrastructure.json with local and external repository data.
    """
    # Load local infrastructure.json
    try:
        with open(INFRASTRUCTURE_PATH, "r") as f:
            infrastructure_data = json.load(f)
    except FileNotFoundError:
        logger.error(f"{INFRASTRUCTURE_PATH} not found.")
        return
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from {INFRASTRUCTURE_PATH}.")
        return

    # Load external repo data for MASP Indexers
    masp_indexers_data = load_external_json("masp-indexers.json")
    merge_external_data(infrastructure_data, masp_indexers_data, "masp_indexers")
    
    # Update MASP Indexers
    for masp_indexer in infrastructure_data.get("masp_indexers", []):
        fetch_masp_indexer_data(masp_indexer)

    # Load external repo data for RPCs
    rpc_data = load_external_json("rpc.json")
    merge_external_data(infrastructure_data, rpc_data, "rpc")
    
    # Update RPCs
    for rpc in infrastructure_data.get("rpc", []):
        fetch_rpc_data(rpc)

    # Load external repo data for Namada Indexers
    namada_indexers_data = load_external_json("namada-indexers.json")
    merge_external_data(infrastructure_data, namada_indexers_data, "namada_indexers")
    
    # Update Namada Indexers
    for namada_indexer in infrastructure_data.get("namada_indexers", []):
        fetch_namada_indexer_data(namada_indexer)

    # Save updated infrastructure.json
    try:
        with open(INFRASTRUCTURE_PATH, "w") as f:
            json.dump(infrastructure_data, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving {INFRASTRUCTURE_PATH}: {e}")

def load_external_json(filename):
    """
    Load JSON data from the external repository.
    """
    try:
        external_file_path = os.path.join(EXTERNAL_REPO_PATH, filename)
        if os.path.exists(external_file_path):
            with open(external_file_path, "r") as f:
                return json.load(f)
        else:
            logger.warning(f"{filename} not found in {EXTERNAL_REPO_PATH}.")
            return []
    except Exception as e:
        logger.error(f"Error loading {filename}: {e}")
        return []

if __name__ == "__main__":
    update_data()
