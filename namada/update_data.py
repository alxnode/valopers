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
                snap_name = data.get("snapshot_name", None)
                height = data.get("snapshot_height", None)
                timestamp_str = data.get("snapshot_block_time", None)
                snapshot_size = data.get("snapshot_size", None)

                if timestamp_str:
                    dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00') if 'Z' in timestamp_str else timestamp_str)
                    timestamp = int(dt.timestamp())

                snapshot["url"] = f"https://server-5.itrocket.net/mainnet/namada/{snap_name}" if snap_name else snapshot.get("url")
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

def update_data():
    """
    Update RPC, Indexer, MASP Indexer, Undexer, and Snapshot data, and merge it with external repository data.
    """
    with open("namada/infrastructure.json", "r") as f:
        json_structure = json.load(f)

    current_time = int(time.time())

    # Merge external repository data into infrastructure
    external_repo_path = "external-repo/user-and-dev-tools/mainnet"

    # Merge RPCs
    rpc_data = []
    for filename in os.listdir(external_repo_path):
        if filename == "rpc.json":
            external_file_path = os.path.join(external_repo_path, filename)
            with open(external_file_path, "r") as f:
                rpc_data = json.load(f)
            break  # Only fetch this file once

    # Update RPC data
    for rpc in rpc_data:
        try:
            url = normalize_url(rpc.get("url", ""))
        except KeyError:
            print(f"Missing 'url' key in RPC data: {rpc}")
            continue  # Skip if 'url' is missing
        existing = next((item for item in json_structure.get("rpc", []) if normalize_url(item.get("url", "")) == url), None)
        if existing:
            existing["provider"] = rpc.get("provider", "")  # Update provider if URL matches
        else:
            json_structure["rpc"].append(rpc)  # Add new entry

    # Update Indexers
    for indexer in json_structure.get("indexers", []):
        try:
            url = indexer.get("url", "")
            if url:
                response = requests.get(f"{url}/api/v1/chain/block/latest", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    latest_block_height = data.get("block")
                    params_response = requests.get(f"{url}/api/v1/chain/parameters", timeout=10)
                    network = params_response.json().get("chainId") if params_response.status_code == 200 else None

                    indexer["latest_block_height"] = latest_block_height
                    indexer["network"] = network
                    indexer["active"] = True
                else:
                    raise Exception("Invalid response code")
            else:
                print(f"Missing 'url' in indexer: {indexer}")
        except Exception:
            indexer["latest_block_height"] = None
            indexer["network"] = None
            indexer["active"] = False
        indexer["last_check"] = current_time

    # Update MASP Indexers
    for masp_indexer in json_structure.get("masp_indexers", []):
        try:
            url = masp_indexer.get("url", "")
            if url:
                response = requests.get(f"{url}/api/v1/height", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    masp_indexer["latest_block_height"] = data.get("block_height")
                    masp_indexer["active"] = True
                else:
                    raise Exception("Invalid response code")
            else:
                print(f"Missing 'url' in masp_indexer: {masp_indexer}")
        except Exception:
            masp_indexer["latest_block_height"] = None
            masp_indexer["active"] = False
        masp_indexer["last_check"] = current_time

    # Update Undexers
    for undexer in json_structure.get("undexers", []):
        try:
            url = undexer.get("url", "")
            if url:
                response = requests.get(f"{url}/v4/status", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    undexer["earliest_block_height"] = data.get("oldestBlock")
                    undexer["latest_block_height"] = data.get("latestBlock")
                    undexer["network"] = data.get("chainId")
                    undexer["active"] = True
                else:
                    raise Exception("Invalid response code")
            else:
                print(f"Missing 'url' in undexer: {undexer}")
        except Exception:
            undexer["earliest_block_height"] = None
            undexer["latest_block_height"] = None
            undexer["network"] = None
            undexer["active"] = False
        undexer["last_check"] = current_time

    # Update Snapshots
    for snapshot in json_structure.get("snapshots", []):
        snapshot = fetch_snapshot_data(snapshot)

    # Save the updated infrastructure.json
    with open("namada/infrastructure.json", "w") as f:
        json.dump(json_structure, f, indent=4)

if __name__ == "__main__":
    update_data()
