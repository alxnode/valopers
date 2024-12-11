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

def normalize_url(url):
    """
    Normalize the URL by stripping the trailing slash if it exists.
    """
    if url.endswith('/'):
        return url.rstrip('/')
    return url

def fetch_external_data():
    """
    Fetch external data from files in the external repository directory.
    """
    external_data = {
        "masp_indexers": [],
        "rpc": [],
        "indexers": [],
        "namada_indexers": []
    }
    
    # Get external data from files in the external repository
    for filename in os.listdir(EXTERNAL_REPO_PATH):
        if filename == "masp-indexers.json":
            with open(os.path.join(EXTERNAL_REPO_PATH, filename), "r") as f:
                external_data["masp_indexers"] = json.load(f)
        elif filename == "rpc.json":
            with open(os.path.join(EXTERNAL_REPO_PATH, filename), "r") as f:
                external_data["rpc"] = json.load(f)
        elif filename == "namada-indexers.json":
            with open(os.path.join(EXTERNAL_REPO_PATH, filename), "r") as f:
                external_data["namada_indexers"] = json.load(f)
                
    return external_data

def merge_data():
    """
    Merge external data into the local infrastructure.json, updating based on URL and provider.
    """
    # Load local infrastructure.json
    with open(INFRASTRUCTURE_PATH, "r") as f:
        infrastructure_data = json.load(f)

    # Fetch external data
    external_data = fetch_external_data()

    # Merge masp_indexers
    for entry in external_data["masp_indexers"]:
        url = normalize_url(entry.get("Indexer API URL"))
        provider = entry.get("Team or Contributor Name")
        if url and provider:
            # Check if the URL exists in the local masp_indexers, update or add it
            exists = False
            for masp_indexer in infrastructure_data['masp_indexers']:
                if normalize_url(masp_indexer['url']) == url:
                    masp_indexer['provider'] = provider
                    exists = True
                    break
            if not exists:
                infrastructure_data['masp_indexers'].append({
                    'url': url,
                    'provider': provider,
                    'last_check': None,
                    'latest_block_height': None,
                    'active': False
                })
                logger.info(f"Added new masp_indexer with URL: {url} and provider: {provider}")

    # Merge rpc
    for entry in external_data["rpc"]:
        url = normalize_url(entry.get("RPC Address"))
        provider = entry.get("Team or Contributor Name")
        if url and provider:
            # Check if the URL exists in the local rpc, update or add it
            exists = False
            for rpc in infrastructure_data['rpc']:
                if normalize_url(rpc['url']) == url:
                    rpc['provider'] = provider
                    exists = True
                    break
            if not exists:
                infrastructure_data['rpc'].append({
                    'url': url,
                    'provider': provider,
                    'last_check': None,
                    'earliest_block_height': None,
                    'latest_block_height': None,
                    'indexer': None,
                    'network': None,
                    'catchup': None,
                    'active': False
                })
                logger.info(f"Added new rpc with URL: {url} and provider: {provider}")

    # Merge namada_indexers (only "Which Indexer": "namada-indexer")
    for entry in external_data["namada_indexers"]:
        if entry.get("Which Indexer") == "namada-indexer":
            url = normalize_url(entry.get("Indexer API URL"))
            provider = entry.get("Team or Contributor Name")
            if url and provider:
                # Check if the URL exists in the local indexers, update or add it
                exists = False
                for indexer in infrastructure_data['indexers']:
                    if normalize_url(indexer['url']) == url:
                        indexer['provider'] = provider
                        exists = True
                        break
                if not exists:
                    infrastructure_data['indexers'].append({
                        'url': url,
                        'provider': provider,
                        'last_check': None,
                        'latest_block_height': None,
                        'network': None,
                        'active': False
                    })
                    logger.info(f"Added new namada_indexer with URL: {url} and provider: {provider}")

    # Save the updated infrastructure.json
    with open(INFRASTRUCTURE_PATH, "w") as f:
        json.dump(infrastructure_data, f, indent=4)
    logger.info(f"Updated infrastructure data saved to {INFRASTRUCTURE_PATH}")

if __name__ == "__main__":
    merge_data()
