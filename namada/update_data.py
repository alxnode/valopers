import json
import time
import requests
from datetime import datetime

def fetch_snapshot_data(snapshot):

    provider = snapshot.get("provider")
    if provider == "itrocket":
        try:          
            response = requests.get("https://server-5.itrocket.net/mainnet/namada/.current_state.json", timeout=10)
            if response.status_code == 200:
                data = response.json()
                snap_name = data.get("snapshot_name", None)
                height = data.get("snapshot_height", None)
                timestamp = data.get("snapshot_block_time", None)
                snapshot_size = data.get("snapshot_size", None) 

            
                if timestamp:                    
                    timestamp = timestamp.split('.')[0]  
                    timestamp = int(datetime.fromisoformat(timestamp).timestamp())

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
    else:
        snapshot["height"] = None
        snapshot["timestamp"] = None
        snapshot["snapshot_size"] = None  
    return snapshot

def update_data():
    """
    Update RPC, Indexer, MASP Indexer, Undexer, and Snapshot data.
    """
    with open("infrastructure.json", "r") as f:
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


    for snapshot in json_structure.get("snapshots", []):
        snapshot = fetch_snapshot_data(snapshot)


    with open("infrastructure.json", "w") as f:
        json.dump(json_structure, f, indent=4)


if __name__ == "__main__":
    update_data()
