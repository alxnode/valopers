import json
import os
import time
import requests
from datetime import datetime

# Paths
INFRASTRUCTURE_PATH = "namada/infrastructure.json"
EXTERNAL_REPO_PATH = "external-repo/user-and-dev-tools/mainnet"

def fetch_snapshot_data(snapshot):
    provider = snapshot.get("provider")
    if provider == "itrocket":
        try:
            response = requests.get("https://server-5.itrocket.net/mainnet/namada/.current_state.json", timeout=10)
            if response.status_code == 200:
                data = response.json()
                snap_name = data.get("snapshot_name", None)
                height = data.get("snapshot_height", None)
                timestamp_str = data.get("snapshot_block_time", None)
                snapshot_size = data.get("snapshot_size", None)

                if timestamp_str:
                    dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00') if 'Z' in timestamp_str else timestamp_str)
                    timestamp = int(dt.timestamp())

                snapshot["url"] = f"https://server-5.itrocket.net/mainnet/namada/{snap_name}" if snap_name else snapshot["url"]
                snapshot["height"] = height
                snapshot["timestamp"] = timestamp
                snapshot["snapshot_size"] = snapshot_size  
            else:
                snapshot.update({"height": None, "timestamp": None, "snapshot_size": None})
        except Exception as e:
            print(f"Error fetching snapshot data for provider {provider}: {e}")
            snapshot.update({"height": None, "timestamp": None, "snapshot_size": None})
    
    elif provider == "Mandragora":
        try:
            response = requests.get("https://snapshots2.mandragora.io/namada-full/info.json", timeout=10)
            if response.status_code == 200:
                data = response.json()
                snapshot["height"] = data.get("snapshot_height")
                snapshot["snapshot_size"] = data.get("data_size")

                snapshot_taken_at = data.get("snapshot_taken_at")
                if snapshot_taken_at:
                    dt = datetime.strptime(snapshot_taken_at, "%Y-%m-%dT%H:%M:%S.%fZ")
                    snapshot["timestamp"] = int(dt.timestamp())
                else:
                    snapshot["timestamp"] = None
            else:
                snapshot.update({"height": None, "timestamp": None, "snapshot_size": None})
        except Exception as e:
            print(f"Error fetching snapshot data for provider {provider}: {e}")
            snapshot.update({"height": None, "timestamp": None, "snapshot_size": None})
    
    else:
        snapshot.update({"height": None, "timestamp": None, "snapshot_size": None})
    return snapshot

def update_data():
    """
    Update infrastructure.json with local and external repository data.
    """
    # Load local infrastructure.json
    with open(INFRASTRUCTURE_PATH, "r") as f:
        infrastructure_data = json.load(f)

    current_time = int(time.time())

    # Update RPCs
    for rpc in infrastructure_data.get("rpc", []):
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
        rpc["last_check"] = current_time

    # Update Indexers
    for indexer in infrastructure_data.get("indexers", []):
        try:
            response = requests.get(f"{indexer['url']}/api/v1/chain/block/latest", timeout=10)
            if response.status_code == 200:
                latest_block_height = response.json().get("block")
                params_response = requests.get(f"{indexer['url']}/api/v1/chain/parameters", timeout=10)
                network = params_response.json().get("chainId") if params_response.status_code == 200 else None

                indexer.update({
                    "latest_block_height": latest_block_height,
                    "network": network,
                    "active": True
                })
            else:
                raise Exception("Invalid response code")
        except Exception:
            indexer.update({
                "latest_block_height": None,
                "network": None,
                "active": False
            })
        indexer["last_check"] = current_time

    # Update MASP Indexers
    for masp_indexer in infrastructure_data.get("masp_indexers", []):
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
        masp_indexer["last_check"] = current_time

    # Update Undexers
    for undexer in infrastructure_data.get("undexers", []):
        try:
            response = requests.get(f"{undexer['url']}/v4/status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                undexer.update({
                    "earliest_block_height": data.get("oldestBlock"),
                    "latest_block_height": data.get("latestBlock"),
                    "network": data.get("chainId"),
                    "active": True
                })
            else:
                raise Exception("Invalid response code")
        except Exception:
            undexer.update({
                "earliest_block_height": None,
                "latest_block_height": None,
                "network": None,
                "active": False
            })
        undexer["last_check"] = current_time

    # Update Snapshots
    for snapshot in infrastructure_data.get("snapshots", []):
        snapshot = fetch_snapshot_data(snapshot)

    # Merge data from external repository
    for filename in os.listdir(EXTERNAL_REPO_PATH):
        if filename.endswith(".json"):
            external_file_path = os.path.join(EXTERNAL_REPO_PATH, filename)
            with open(external_file_path, "r") as f:
                external_data = json.load(f)
            # Customize merging logic as needed
            infrastructure_data.update(external_data)

    # Save updated infrastructure.json
    with open(INFRASTRUCTURE_PATH, "w") as f:
        json.dump(infrastructure_data, f, indent=4)


if __name__ == "__main__":
    update_data()
