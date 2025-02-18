import json
import time
import requests
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
TIMEOUT = 10
INFRASTRUCTURE_PATH = "namada/infrastructure.json"
EXTERNAL_REPO_PATH = "external-repo/user-and-dev-tools/mainnet"

def normalize_url(url: str) -> str:
    """Normalize the URL by stripping trailing slashes."""
    return url.rstrip('/')

def safe_request(url: str, timeout: int = TIMEOUT) -> Optional[Dict[str, Any]]:
    """Make a safe HTTP request with error handling."""
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Request failed for {url}: {str(e)}")
        return None

def parse_timestamp(timestamp_str: str) -> Optional[int]:
    """Parse timestamp string to Unix timestamp."""
    try:
        if 'Z' in timestamp_str:
            timestamp_str = timestamp_str.replace('Z', '+00:00')
        dt = datetime.fromisoformat(timestamp_str)
        return int(dt.timestamp())
    except (ValueError, TypeError) as e:
        logger.error(f"Error parsing timestamp {timestamp_str}: {str(e)}")
        return None

def fetch_snapshot_data(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch and update snapshot data based on provider."""
    provider = snapshot.get("provider")
    
    provider_configs = {
        "itrocket": {
            "url": "https://server-5.itrocket.net/mainnet/namada/.current_state.json",
            "parser": lambda data: {
                "url": f"https://server-5.itrocket.net/mainnet/namada/{data.get('snapshot_name')}" if data.get('snapshot_name') else snapshot.get("url"),
                "height": data.get("snapshot_height"),
                "timestamp": parse_timestamp(data.get("snapshot_block_time")),
                "snapshot_size": data.get("snapshot_size")
            }
        },
        "Mandragora": {
            "url": "https://snapshots2.mandragora.io/namada-full/info.json",
            "parser": lambda data: {
                "url": "https://snapshots2.mandragora.io/namada-full/latest",  # Static URL for latest snapshot
                "height": data.get("snapshot_height"),
                "timestamp": parse_timestamp(data.get("snapshot_taken_at")),
                "snapshot_size": data.get("data_size")
            }
        }
    }

    if provider in provider_configs:
        config = provider_configs[provider]
        data = safe_request(config["url"])
        
        if data:
            try:
                update_data = config["parser"](data)
                snapshot.update(update_data)
            except Exception as e:
                logger.error(f"Error parsing data for provider {provider}: {str(e)}")
                snapshot.update({"height": None, "timestamp": None, "snapshot_size": None})
        else:
            snapshot.update({"height": None, "timestamp": None, "snapshot_size": None})
    else:
        snapshot.update({"height": None, "timestamp": None, "snapshot_size": None})
    
    return snapshot

def update_rpc_data(rpc: Dict[str, Any], current_time: int) -> None:
    """Update RPC endpoint data."""
    url = normalize_url(rpc.get("RPC Address", ""))
    if not url:
        logger.warning(f"Missing 'RPC Address' in RPC data: {rpc}")
        return

    logger.info(f"Updating RPC: {url}")
    data = safe_request(f"{url}/status")
    
    if data:
        result = data.get("result", {})
        node_info = result.get("node_info", {})
        sync_info = result.get("sync_info", {})
        
        # Update RPC data with new values
        updated_data = {
            "earliest_block_height": sync_info.get("earliest_block_height"),
            "latest_block_height": sync_info.get("latest_block_height"),
            "indexer": node_info.get("other", {}).get("tx_index"),
            "network": node_info.get("network"),
            "catchup": sync_info.get("catching_up", False),
            "active": True,
            "last_check": current_time  # Ensure last_check is included in the update
        }
        rpc.update(updated_data)
        logger.info(f"Successfully updated RPC data for {url}")
    else:
        # Update with default values on failure
        updated_data = {
            "earliest_block_height": None,
            "latest_block_height": None,
            "indexer": None,
            "network": None,
            "catchup": None,
            "active": False,
            "last_check": current_time  # Still update last_check even on failure
        }
        rpc.update(updated_data)
        logger.warning(f"Failed to update RPC data for {url}")

def update_indexer_data(indexer: Dict[str, Any], current_time: int) -> None:
    """Update indexer data."""
    url = indexer.get("url", "")
    if not url:
        logger.warning(f"Missing 'url' in indexer: {indexer}")
        return

    latest_block = safe_request(f"{url}/api/v1/chain/block/latest")
    params = safe_request(f"{url}/api/v1/chain/parameters")
    
    if latest_block and params:
        indexer.update({
            "latest_block_height": latest_block.get("block"),
            "network": params.get("chainId"),
            "active": True,
            "last_check": current_time
        })
    else:
        indexer.update({
            "latest_block_height": None,
            "network": None,
            "active": False,
            "last_check": current_time
        })

def update_masp_indexer_data(masp_indexer: Dict[str, Any], current_time: int) -> None:
    """Update MASP indexer data."""
    url = masp_indexer.get("url", "")
    if not url:
        logger.warning(f"Missing 'url' in masp_indexer: {masp_indexer}")
        return

    data = safe_request(f"{url}/api/v1/height")
    
    if data:
        masp_indexer.update({
            "latest_block_height": data.get("block_height"),
            "active": True,
            "last_check": current_time
        })
    else:
        masp_indexer.update({
            "latest_block_height": None,
            "active": False,
            "last_check": current_time
        })

def update_undexer_data(undexer: Dict[str, Any], current_time: int) -> None:
    """Update undexer data."""
    url = undexer.get("url", "")
    if not url:
        logger.warning(f"Missing 'url' in undexer: {undexer}")
        return

    data = safe_request(f"{url}/v4/status")
    
    if data:
        undexer.update({
            "earliest_block_height": data.get("oldestBlock"),
            "latest_block_height": data.get("latestBlock"),
            "network": data.get("chainId"),
            "active": True,
            "last_check": current_time
        })
    else:
        undexer.update({
            "earliest_block_height": None,
            "latest_block_height": None,
            "network": None,
            "active": False,
            "last_check": current_time
        })

def update_data() -> None:
    """Update infrastructure data and merge with external repository data."""
    try:
        with open(INFRASTRUCTURE_PATH, "r") as f:
            json_structure = json.load(f)
    except Exception as e:
        logger.error(f"Error reading infrastructure file: {str(e)}")
        return

    current_time = int(time.time())

    # Load external RPC data
    try:
        rpc_file = os.path.join(EXTERNAL_REPO_PATH, "rpc.json")
        if os.path.exists(rpc_file):
            with open(rpc_file, "r") as f:
                rpc_data = json.load(f)
        else:
            logger.warning(f"RPC file not found: {rpc_file}")
            rpc_data = []
    except Exception as e:
        logger.error(f"Error reading RPC file: {str(e)}")
        rpc_data = []

    # Update all components
    for rpc in rpc_data:
        update_rpc_data(rpc, current_time)

    # Update the RPC data in the infrastructure.json
    json_structure["rpcs"] = rpc_data

    for indexer in json_structure.get("indexers", []):
        update_indexer_data(indexer, current_time)

    for masp_indexer in json_structure.get("masp_indexers", []):
        update_masp_indexer_data(masp_indexer, current_time)

    for undexer in json_structure.get("undexers", []):
        update_undexer_data(undexer, current_time)

    for snapshot in json_structure.get("snapshots", []):
        fetch_snapshot_data(snapshot)

    # Save updated data
    try:
        with open(INFRASTRUCTURE_PATH, "w") as f:
            json.dump(json_structure, f, indent=4)
        logger.info("Successfully updated infrastructure data")
    except Exception as e:
        logger.error(f"Error saving infrastructure file: {str(e)}")

if __name__ == "__main__":
    update_data()
