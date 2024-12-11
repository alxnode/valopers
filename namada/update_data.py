import json
import time
import requests
from datetime import datetime
from pathlib import Path

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
                snapshot["height"] = None
                snapshot["timestamp"] = None
                snapshot["snapshot_size"] = None 
        except Exception as e:
            print(f"Error fetching snapshot data for provider {provider}: {e}")
            snapshot["height"] = None
            snapshot["timestamp"] = None
            snapshot["snapshot_size"] = None  
    
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
                snapshot["height"] = None
                snapshot["timestamp"] = None
                snapshot["snapshot_size"] = None 
        except Exception as e:
            print(f"Error fetching snapshot data for provider {provider}: {e}")
            snapshot["height"] = None
            snapshot["timestamp"] = None
            snapshot["snapshot_size"] = None  
    else:
        snapshot["height"] = None
        snapshot["timestamp"] = None
        snapshot["snapshot_size"] = None  
    return snapshot

def merge_additional_data(json_structure, masp_indexers_path, rpc_path, indexers_path):
    def load_json(file_path):
        with open(file_path, "r") as f:
            return json.load(f)

    masp_indexers = load_json(masp_indexers_path)
    rpc = load_json(rpc_path)
    indexers = load_json(indexers_path)

    # Add missing masp indexers
    existing_masp_urls = {item["url"] for item in json_structure.get("masp_indexers", [])}
    for entry in masp_indexers:
        if entry["Indexer API URL"] not in existing_masp_urls:
            json_structure["masp_indexers"].append({
                "url": entry["Indexer API URL"],
                "provider": entry["Team or Contributor Name"],
                "last_check": 0,
                "latest_block_height": 0,
                "active": True
            })

    # Add missing RPC entries
    existing_rpc_urls = {item["url"] for item in json_structure.get("rpc", [])}
    for entry in rpc:
        if entry["RPC Address"] not in existing_rpc_urls:
            json_structure["rpc"].append({
                "url": entry["RPC Address"],
                "provider": entry["Team or Contributor Name"],
                "last_check": 0,
                "earliest_block_height": "0",
                "latest_block_height": "0",
                "indexer": "off",
                "network": "",
                "catchup": False,
                "active": True
            })

    # Add missing indexers
    existing_indexer_urls = {item["url"] for item in json_structure.get("indexers", [])}
    for entry in indexers:
        if entry["Which Indexer"] == "namada-indexer" and entry["Indexer API URL"] not in existing_indexer_urls:
            json_structure["indexers"].append({
                "url": entry["Indexer API URL"],
                "provider": entry["Team or Contributor Name"],
                "last_check": 0,
                "latest_block_height": "0",
                "network": "",
                "active": True
            })

def update_data():
    base_path = Path("user-and-dev-tools/mainnet")
    infrastructure_path = base_path / "infrastructure.json"
    masp_indexers_path = base_path / "masp-indexers.json"
    rpc_path = base_path / "rpc.json"
    indexers_path = base_path / "namada-indexers.json"

    with open(infrastructure_path, "r") as f:
        json_structure = json.load(f)

    current_time = int(time.time())

    # Update RPC
    for rpc in json_structure.get("rpc", []):
        try:
            response = requests.get(f"{rpc['url']}/status", timeout=10)
            if response.status_code == 200:
                data = response.json().get("result", {})
                node_info = data.get("node_info", {})
                sync_info = data.get("sync_info", {})

                rpc["earliest_block_height"] = sync_info.get("earliest_block_height")
                rpc["latest_block_height"] = sync_info.get("latest_block_height")
                rpc["indexer"] = node_info.get("other", {}).get("tx_index")
                rpc["network"] = node_info.get("network")
                rpc["catchup"] = sync_info.get("catching_up", False)
                rpc["active"] = True
            else:
                raise Exception("Invalid response code")
        except Exception:
            rpc["earliest_block_height"] = None
            rpc["latest_block_height"] = None
            rpc["indexer"] = None
            rpc["network"] = None
            rpc["catchup"] = None
            rpc["active"] = False
        rpc["last_check"] = current_time

    # Update Indexers
    for indexer in json_structure.get("indexers", []):
        try:
            response = requests.get(f"{indexer['url']}/api/v1/chain/block/latest", timeout=10)
            if response.status_code == 200:
                data = response.json()
                latest_block_height = data.get("block")
                params_response = requests.get(f"{indexer['url']}/api/v1/chain/parameters", timeout=10)
                network = params_response.json().get("chainId") if params_response.status_code == 200 else None

                indexer["latest_block_height"] = latest_block_height
                indexer["network"] = network
                indexer["active"] = True
            else:
                raise Exception("Invalid response code")
        except Exception:
            indexer["latest_block_height"] = None
            indexer["network"] = None
            indexer["active"] = False
        indexer["last_check"] = current_time

    # Update MASP Indexers
    for masp_indexer in json_structure.get("masp_indexers", []):
        try:
            response = requests.get(f"{masp_indexer['url']}/api/v1/height", timeout=10)
            if response.status_code == 200:
                data = response.json()
                masp_indexer["latest_block_height"] = data.get("block_height")
                masp_indexer["active"] = True
            else:
                raise Exception("Invalid response code")
        except Exception:
            masp_indexer["latest_block_height"] = None
            masp_indexer["active"] = False
        masp_indexer["last_check"] = current_time

    # Update Undexers
    for undexer in json_structure.get("undexers", []):
        try:
            response = requests.get(f"{undexer['url']}/v4/status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                undexer["earliest_block_height"] = data.get("oldestBlock")
                undexer["latest_block_height"] = data.get("latestBlock")
                undexer["network"] = data.get("chainId")
                undexer["active"] = True
            else:
                raise Exception("Invalid response code")
        except Exception:
            undexer["earliest_block_height"] = None
            undexer["latest_block_height"] = None
            undexer["network"] = None
            undexer["active"] = False
        undexer["last_check"] = current_time

    # Update Snapshots
    for snapshot in json_structure.get("snapshots", []):
        snapshot = fetch_snapshot_data(snapshot)

    # Merge additional data
    merge_additional_data(json_structure, masp_indexers_path, rpc_path, indexers_path)

    # Save updated infrastructure
    with open(infrastructure_path, "w") as f:
        json.dump(json_structure, f, indent=4)

if __name__ == "__main__":
    update_data()
