import os
import json
import logging
import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

BASE_PATH = "./chain-registry"
OUTPUT_PATH = "assets_summary.json"
VALOPERS_API_URL = "https://api.valopers.com/chains"

# Fetch valopers data
def fetch_valopers_data():
    try:
        response = requests.get(VALOPERS_API_URL, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Failed to fetch valopers data: {e}")
        return []

# Get valopers logo for a specific chain_id
def get_valopers_logo(chain_id, valopers_data):
    for chain in valopers_data:
        if chain["chain_id"] == chain_id:
            return chain["logo"]
    return None

def add_missing_valopers_logos():
    try:
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            assets = json.load(f)
    except Exception as e:
        logging.error(f"Failed to read {OUTPUT_PATH}: {e}")
        return

    # Create a mapping of base -> valopers_logo
    base_to_logo = {}
    for asset in assets:
        valopers_logo = asset["logo_URIs"].get("valopers_logo")
        if valopers_logo:
            base_to_logo[asset["base"]] = valopers_logo

    for asset in assets:
        if "valopers_logo" not in asset["logo_URIs"]:
            base = asset["base"]
            if base in base_to_logo:
                asset["logo_URIs"]["valopers_logo"] = base_to_logo[base]

    try:
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(assets, f, indent=4, ensure_ascii=False)
        logging.info("Valopers logos updated successfully.")
    except Exception as e:
        logging.error(f"Failed to write updated {OUTPUT_PATH}: {e}")

def main():
    logging.info(f"Starting directory traversal at {BASE_PATH}")
    asset_list = []

    valopers_data = fetch_valopers_data()

    for root, _, files in os.walk(BASE_PATH):
        logging.info(f"Checking directory: {root}")

        chain_id = "unknown"

        # Read chain.json
        if "chain.json" in files:
            chain_file_path = os.path.join(root, "chain.json")
            logging.info(f"Found chain.json: {chain_file_path}")

            try:
                with open(chain_file_path, "r", encoding="utf-8") as f:
                    chain_data = json.load(f)
                    chain_id = chain_data.get("chain_id", "unknown")
                    logging.info(f"Extracted chain_id: {chain_id}")
            except Exception as e:
                logging.error(f"Failed to process {chain_file_path}: {e}")

        if "assetlist.json" in files:
            asset_file_path = os.path.join(root, "assetlist.json")
            logging.info(f"Found assetlist.json: {asset_file_path}")

            try:
                with open(asset_file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    chain_name = data.get("chain_name", "unknown")
                    assets = data.get("assets", [])

                    logging.info(f"Processing chain: {chain_name} with {len(assets)} assets")

                    valopers_logo = get_valopers_logo(chain_id, valopers_data)

                    for asset in assets:
                        base = asset.get("base", "")
                        name = asset.get("name", "")
                        display = asset.get("display", "")
                        symbol = asset.get("symbol", "")
                        denom_units = asset.get("denom_units", [])
                        logo_URIs = asset.get("logo_URIs", {})

                        if valopers_logo:
                            logo_URIs["valopers_logo"] = valopers_logo

                        denoms = [
                            {"denom": denom_unit["denom"], "exponent": denom_unit["exponent"]}
                            for denom_unit in denom_units
                        ]

                        asset_list.append({
                            "chain_name": chain_name,
                            "chain_id": chain_id,  
                            "base": base,
                            "name": name,
                            "display": display,
                            "symbol": symbol,
                            "denoms": denoms,
                            "logo_URIs": logo_URIs
                        })

            except Exception as e:
                logging.error(f"Failed to process {asset_file_path}: {e}")

    # Merge in missing manual assets
    manual_path = "assets_manual.json"
    if os.path.exists(manual_path):
        try:
            with open(manual_path, "r", encoding="utf-8") as f:
                manual_assets = json.load(f)

            existing_keys = {(a["chain_id"], a["base"]) for a in asset_list}
            added_count = 0

            for asset in manual_assets:
                key = (asset.get("chain_id"), asset.get("base"))
                if key not in existing_keys:
                    asset_list.append(asset)
                    added_count += 1

            if added_count:
                logging.info(f"Added {added_count} missing manual asset(s) from assets_manual.json")
            else:
                logging.info("No new manual assets needed to be added.")

        except Exception as e:
            logging.error(f"Failed to merge assets_manual.json: {e}")
    else:
        logging.info("No assets_manual.json file found. Skipping manual merge.")

    if asset_list:
        with open(OUTPUT_PATH, "w", encoding="utf-8") as out_file:
            json.dump(asset_list, out_file, indent=4, ensure_ascii=False)
        logging.info(f"Extracted data saved to {OUTPUT_PATH}")
    else:
        logging.warning("No assets were extracted. Check the input files or directory structure.")

    add_missing_valopers_logos()

    logging.info("Script execution completed.")

if __name__ == "__main__":
    main()
