import json
import time
import requests
import os
from datetime import datetime

def normalize_url(url):
    """Normalize the URL by stripping trailing slashes."""
    return url.rstrip('/')

def fetch_snapshot_data(snapshot):
    provider = snapshot.get("provider")
    
    if provider == "itrocket":
        try:
            response = requests.get("https://server-5.itrocket.net/mainnet/namada/.current_state.json", timeout=10)
            if response.status_code == 200:
                data = response.json()
                snap_name = data.get("snapshot_name")
                height = data.get("snapshot_height")
                timestamp_str = data.get("snapshot_block_time")
                snapshot_size = data.get("snapshot_size")

                timestamp = None
                if timestamp_str:
                    dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    timestamp = int(dt.timestamp())

                snapshot["url"] = f"https://server-5.itrocket.net/mainnet/namada/{snap_name}" if snap_name else snapshot.get("url")
                snapshot["height"] = height
                snapshot["timestamp"] = timestamp
                snapshot["snapshot_size"] = snapshot_size  
        except Exception as e:
            print(f"Error fetching snapshot data for provider {provider}: {e}")

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
        except Exception as e:
            print(f"Error fetching snapshot data for provider {provider}: {e}")

    return snapshot


def update_data():
    """Update infrastructure.json by refreshing values without external data merging."""
    with open("namada/infrastructure.json", "r") as f:
        json_structure = json.load(f)

    current_time = int(time.time())

    # Update RPCs
    for rpc in json_structure.get("rpc", []):
        try:
            url = normalize_url(rpc.get("url", ""))
            if not url.startswith("http"):
                print(f"Skipping invalid RPC URL: {url}")
                continue

            print(f"Updating RPC: {url}")
            response = requests.get(f"{url}/status", timeout=10)
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
                    "active": True,
                    "last_check": current_time,
                })
            else:
                raise Exception("Invalid response code")
        except Exception as e:
            print(f"Error updating RPC {url}: {e}")
            rpc.update({
                "earliest_block_height": None,
                "latest_block_height": None,
                "indexer": None,
                "network": None,
                "catchup": None,
                "active": False,
                "last_check": current_time,
            })

    # Update Indexers
    for indexer in json_structure.get("indexers", []):
        try:
            url = indexer.get("url", "")
            if not url:
                print(f"Skipping indexer with missing URL: {indexer}")
                continue

            print(f"Updating Indexer: {url}")
            response = requests.get(f"{url}/api/v1/chain/block/latest", timeout=10)
            if response.status_code == 200:
                data = response.json()
                latest_block_height = data.get("block")

                params_response = requests.get(f"{url}/api/v1/chain/parameters", timeout=10)
                network = params_response.json().get("chainId") if params_response.status_code == 200 else None

                indexer.update({
                    "latest_block_height": latest_block_height,
                    "network": network,
                    "active": True,
                    "last_check": current_time,
                })
            else:
                raise Exception("Invalid response code")
        except Exception as e:
            print(f"Error updating indexer {url}: {e}")
            indexer.update({
                "latest_block_height": None,
                "network": None,
                "active": False,
                "last_check": current_time,
            })

    # Update MASP Indexers
    for masp_indexer in json_structure.get("masp_indexers", []):
        try:
            url = masp_indexer.get("url", "")
            if not url:
                print(f"Skipping MASP Indexer with missing URL: {masp_indexer}")
                continue

            print(f"Updating MASP Indexer: {url}")
            response = requests.get(f"{url}/api/v1/height", timeout=10)
            if response.status_code == 200:
                data = response.json()
                masp_indexer.update({
                    "latest_block_height": data.get("block_height"),
                    "active": True,
                    "last_check": current_time,
                })
            else:
                raise Exception("Invalid response code")
        except Exception as e:
            print(f"Error updating MASP Indexer {url}: {e}")
            masp_indexer.update({
                "latest_block_height": None,
                "active": False,
                "last_check": current_time,
            })

    # Update Undexers
    for undexer in json_structure.get("undexers", []):
        try:
            url = undexer.get("url", "")
            if not url:
                print(f"Skipping Undexer with missing URL: {undexer}")
                continue

            print(f"Updating Undexer: {url}")
            response = requests.get(f"{url}/v4/status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                undexer.update({
                    "earliest_block_height": data.get("oldestBlock"),
                    "latest_block_height": data.get("latestBlock"),
                    "network": data.get("chainId"),
                    "active": True,
                    "last_check": current_time,
                })
            else:
                raise Exception("Invalid response code")
        except Exception as e:
            print(f"Error updating Undexer {url}: {e}")
            undexer.update({
                "earliest_block_height": None,
                "latest_block_height": None,
                "network": None,
                "active": False,
                "last_check": current_time,
            })

    # Update Snapshots
    for snapshot in json_structure.get("snapshots", []):
        fetch_snapshot_data(snapshot)

    # Save updated infrastructure.json
    with open("namada/infrastructure.json", "w") as f:
        json.dump(json_structure, f, indent=4)

if __name__ == "__main__":
    update_data()
