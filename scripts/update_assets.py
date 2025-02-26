import os
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
base_path = "./chain-registry"
asset_list = []
logging.info(f"Starting directory traversal at {base_path}")

for root, _, files in os.walk(base_path):
    logging.info(f"Checking directory: {root}")

    chain_id = "unknown"
    

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

                for asset in assets:
                    base = asset.get("base", "")
                    name = asset.get("name", "")
                    display = asset.get("display", "")
                    symbol = asset.get("symbol", "")
                    denom_units = asset.get("denom_units", [])
                    logo_URIs = asset.get("logo_URIs", {})

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

output_path = "assets_summary.json"
if asset_list:
    with open(output_path, "w", encoding="utf-8") as out_file:
        json.dump(asset_list, out_file, indent=4, ensure_ascii=False)
    logging.info(f"Extracted data saved to {output_path}")
else:
    logging.warning("No assets were extracted. Check the input files or directory structure.")

logging.info("Script execution completed.")
