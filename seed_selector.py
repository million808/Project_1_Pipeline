# seed_selector.py
# Author: Max Balter
# Purpose: This script is responsible for updating the ActSeek config.json file with a new seed protein structure.
# The seed is automatically selected based on the first uncharacterized protein hit reported by Foldseek.
# I use this script to ensure ActSeek always compares against a relevant, recent Foldseek result.

import os            # I use this to check for files, manipulate paths, and confirm presence of required inputs.
import sys           # I use sys.exit() to gracefully quit the script if critical files are missing.
import json          # I use this to read and write the ActSeek config.json file.
import requests      # I use requests to download the AlphaFold PDB model of the selected seed protein.

# === STEP 1: Confirm required input file ===
# This file should have been written by 01_api_download_sequence.py
seed_id_file = "query_seed_accession.txt"  # This is where I expect to find the UniProt accession of the seed.
if not os.path.exists(seed_id_file):
    sys.exit("❌ Error: Could not find 'query_seed_accession.txt'.")

# === STEP 2: Read UniProt accession from seed file ===
# I load the UniProt accession from the previous step (e.g., A0A0E9XQA6)
with open(seed_id_file, 'r') as f:
    seed_accession = f.read().strip()
print(f"✅ Extracted UniProt accession for seed: {seed_accession}")

# === STEP 3: Build AlphaFold filename and path ===
# I now build the expected PDB file name and full path based on the AlphaFold naming convention.
seed_filename = f"AF-{seed_accession}-F1-model_v4.pdb"
seed_structure_path = os.path.join("..", "structures", seed_filename)

# === STEP 4: Try to download the seed structure if it doesn't already exist ===
# This ensures ActSeek has a structure to align against.
if not os.path.exists(seed_structure_path):
    print(f"↳ Seed structure not found. Downloading {seed_filename} from AlphaFold...")
    url = f"https://alphafold.ebi.ac.uk/files/{seed_filename}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # I raise an exception for 404, 500, etc.
        with open(seed_structure_path, 'wb') as f:
            f.write(response.content)
        print(f"  ✓ Seed structure saved to {seed_structure_path}")
    except requests.RequestException as e:
        sys.exit(f"✗ Failed to download seed structure {seed_filename}. Error: {str(e)}")
else:
    print(f"✓ Seed structure already exists at {seed_structure_path}")

# === STEP 5: Update ActSeek config.json ===
# I now update the config to use the newly downloaded (or already present) seed file.
config_path = os.path.join(os.getcwd(), "config.json")  # I expect config.json in the same directory as this script.

if not os.path.exists(config_path):
    sys.exit(f"✗ Could not find config.json at {config_path}. Make sure it exists.")

# I load the config settings into memory.
with open(config_path, 'r') as f:
    config = json.load(f)

# I update the seed protein path in the config to match the new seed structure.
config["seed_protein_file"] = seed_structure_path

# As a default, I update the active site to a placeholder. 
config["active_site"] = "1,2,3"
print(f"✅ Auto-set active_site: {config['active_site']}")

# I save the updated config back to disk.
with open(config_path, 'w') as f:
    json.dump(config, f, indent=4)

print("✅ Updated config.json with new seed and active_site.")

