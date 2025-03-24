# 02_ActSeek_process_pipeline.py
# Author: Max Balter
# Purpose: This script continues my protein discovery pipeline. I start by identifying uncharacterized proteins using Foldseek.
# Then I use ActSeek to determine structural similarities to an enzyme seed site. This version avoids single-protein mode (-ts)
# and instead uses batch mode with a config.json + test.txt file.

import subprocess  # I use subprocess to run ActSeek as a shell command from Python.
import os           # I use os to handle file paths and file existence checks.
import sys          # I use sys to allow clean exits if something critical is missing.
import re           # I use regular expressions to extract UniProt IDs.
import requests     # I use requests to download AlphaFold structures automatically.
import json         # I use json to load and modify the ActSeek config file.

# === PATH DEFINITIONS ===
input_hits_file = "uncharacterized_hits.txt"  # I assume Foldseek results were saved here.
output_results_file = "../results/actseek_results.txt"  # I want to log the ActSeek output here.
pdb_output_folder = "../structures"  # This is where I store AlphaFold structure files.
protein_list_file = os.path.join(os.getcwd(), "test.txt")  # List of proteins to pass to ActSeek.
config_file_path = os.path.join(os.getcwd(), "config.json")  # Config file for batch mode.

# === STEP 1: Validate Foldseek result file ===
if not os.path.exists(input_hits_file):
    sys.exit(f"❌ Error: Required file '{input_hits_file}' not found. Run the Foldseek pipeline first.")

# === STEP 2: Make sure structure output directory exists ===
os.makedirs(pdb_output_folder, exist_ok=True)

# === STEP 3: Extract UniProt accessions ===
accessions = []  # I create a list to collect UniProt accessions.
with open(input_hits_file, 'r') as infile:
    for line in infile:
        parts = line.strip().split('\t')
        if len(parts) >= 2:
            match = re.search(r"AF-([A-Z0-9]+)-", parts[1])
            if match:
                accessions.append(match.group(1))

# I convert to a sorted set of unique UniProt accessions.
unique_accessions = sorted(set(accessions))
print(f"Total Foldseek uncharacterized hits: {len(accessions)}")
print(f"Total unique uncharacterized UniProt accessions to process with ActSeek: {len(unique_accessions)}")

# === STEP 4: Download AlphaFold models (if not already present) ===
with open(protein_list_file, 'w') as protlist:
    for acc in unique_accessions:
        af_pdb_filename = f"AF-{acc}-F1-model_v4.pdb"
        af_pdb_path = os.path.join(pdb_output_folder, af_pdb_filename)

        if not os.path.exists(af_pdb_path):
            print(f"↳ Downloading AlphaFold model for {acc}...")
            url = f"https://alphafold.ebi.ac.uk/files/{af_pdb_filename}"
            try:
                response = requests.get(url)
                response.raise_for_status()
                with open(af_pdb_path, 'wb') as f:
                    f.write(response.content)
                print(f"  ✓ Successfully downloaded {af_pdb_filename}")
            except requests.RequestException:
                print(f"  ✗ Failed to download {acc}. Skipping...")
                continue

        # I write the UniProt ID to test.txt for ActSeek to read.
        protlist.write(f"{acc}\n")

# === STEP 5: Validate the seed structure ===
if not os.path.exists(config_file_path):
    sys.exit("❌ Error: config.json not found. Run the seed selector first.")

with open(config_file_path, 'r') as config_file:
    config = json.load(config_file)

seed_path = config.get("seed_protein_file")
if not seed_path:
    sys.exit("❌ Error: seed_protein_file not defined in config.json")

if not os.path.exists(seed_path):
    seed_filename = os.path.basename(seed_path)
    print(f"↳ Downloading seed structure {seed_filename}...")
    url = f"https://alphafold.ebi.ac.uk/files/{seed_filename}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        with open(seed_path, 'wb') as f:
            f.write(response.content)
        print(f"  ✓ Seed structure downloaded to {seed_path}")
    except requests.RequestException:
        sys.exit(f"✗ Failed to download required seed structure {seed_filename}. Aborting.")

# === STEP 6: Construct ActSeek command ===
print("\n✅ Starting ActSeek batch mode using config.json...")

actseek_command = [
    "actseek",
    "-a", config["active_site"],
    "-sa", config["selected_active"],
    "-g", json.dumps(config["aa_grouping"]),
    "-r", str(config["random_seed"]),
    "-t1", str(config["threshold"]),
    "-t1c", str(config["threshold_combinations"]),
    "-t2", str(config["aa_surrounding"]),
    "-t2t", str(config["aa_surrounding_threshold"]),
    "-t3", str(config["threshold_others"]),
    "-i", str(config["iterations"]),
    "-f", str(config["first_in_file"]),
    "-m", str(config["max_protein"]),
    "-s", config["protein_file"],
    "-af", config["alphafold_proteins_path"],
    "-p", config["seed_protein_file"],
    "-pr", config["path_results"]
]

if config.get("delete_protein_files"):
    actseek_command.append("-d")
if config.get("KVFinder"):
    actseek_command.append("-kv")
if config.get("custom"):
    actseek_command.append("-c")

# === STEP 7: Run ActSeek and log output ===
try:
    result = subprocess.run(actseek_command, capture_output=True, text=True, check=True)
    with open(output_results_file, 'w') as f:
        f.write(result.stdout)
    print(f"\n✓ ActSeek run complete. Results written to {output_results_file}")
except subprocess.CalledProcessError as e:
    print(f"\n✗ ActSeek batch mode failed with return code {e.returncode}")
    print("STDOUT:\n", e.stdout)
    print("STDERR:\n", e.stderr)
    with open(output_results_file, 'w') as f:
        f.write("ACTSEEK_BATCH_FAILED\n")
        f.write(f"\nSTDOUT:\n{e.stdout}\n")
        f.write(f"\nSTDERR:\n{e.stderr}\n")

