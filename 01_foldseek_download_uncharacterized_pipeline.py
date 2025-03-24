
# Author: Max Balter
# Purpose: This script is part of a larger pipeline to reduce the Foldseek search space from ~200 million structures down to a filtered list
# of uncharacterized proteins. It retrieves structure alignments from the Foldseek web API, scans across all major Foldseek-supported databases,
# extracts hits labeled as "uncharacterized protein", and saves them to a file ready for downstream processing with ActSeek.

import requests       # I use this library to interact with Foldseek's web API and download files from RCSB or UniProt.
import json           # I use this to process any API responses returned as JSON.
import os             # I use this to check file paths and manipulate local directories.
import sys            # I use sys.exit() to cleanly stop the script if anything goes wrong.
from time import sleep  # I use sleep to wait between polling intervals during Foldseek job processing.
import tarfile        # I use this to extract the Foldseek result archive.
import tempfile       # I use this to safely extract Foldseek results without cluttering the working directory.
import re             # I use this to extract UniProt accessions using regular expressions.

def download_pdb(pdb_id):
    # If the user inputs a UniProt ID instead of a PDB ID, I try to convert it.
    if len(pdb_id) > 4:
        uniprot_url = f'https://www.ebi.ac.uk/pdbe/api/mappings/best_structures/{pdb_id}'
        response = requests.get(uniprot_url)
        if response.status_code == 200:
            data = response.json()
            if pdb_id in data and data[pdb_id]:
                pdb_id = data[pdb_id][0]['pdb_id']
                print(f"Found associated PDB ID: {pdb_id}")
            else:
                sys.exit(f"No PDB structure found for UniProt accession {pdb_id}.")
        else:
            sys.exit(f"Failed to retrieve PDB ID for UniProt accession {pdb_id}.")

    # I download the actual PDB structure file from RCSB.
    url = f'https://files.rcsb.org/download/{pdb_id}.pdb'
    response = requests.get(url)
    if response.status_code == 200:
        pdb_filename = f'{pdb_id}.pdb'
        with open(pdb_filename, 'w') as file:
            file.write(response.text)
        print(f"Downloaded PDB file: {pdb_filename}")
        return pdb_filename
    else:
        sys.exit(f"Failed to download PDB file for {pdb_id}. Check if the ID is correct.")

def extract_uncharacterized_entries(tar_path):
    filtered_results = []  # I’ll collect uncharacterized protein lines here.
    accessions = []        # I’ll also track the accession IDs for use as seeds.
    with tempfile.TemporaryDirectory() as tempdir:
        with tarfile.open(tar_path, 'r:gz') as tar:
            tar.extractall(path=tempdir)  # I extract the entire archive into a safe temporary folder.
            for root, dirs, files in os.walk(tempdir):
                for name in files:
                    if name.endswith(".m8"):
                        filepath = os.path.join(root, name)
                        with open(filepath, 'r') as f:
                            for line in f:
                                if "uncharacterized protein" in line.lower():
                                    filtered_results.append(line.strip())
                                    # I extract the UniProt accession from hits like AF-A0A0E9XQA6-F1-model_v4
                                    match = re.search(r"AF-([A-Z0-9]+)-", line)
                                    if match:
                                        accessions.append(match.group(1))

    output_txt = "uncharacterized_hits.txt"
    with open(output_txt, 'w') as out:
        for hit in filtered_results:
            out.write(hit + '\n')
    print(f"Filtered uncharacterized entries saved to {output_txt}")
    print(f"Number of uncharacterized entries found: {len(filtered_results)}")

    # === Save the first accession ID to query_seed_accession.txt ===
    if accessions:
        seed_accession = accessions[0]
        with open("query_seed_accession.txt", 'w') as seedfile:
            seedfile.write(seed_accession)
        print(f"✅ Seed UniProt accession saved to query_seed_accession.txt: {seed_accession}")
    else:
        print("⚠️  Warning: No UniProt accessions extracted for seed.")

def foldseek_apiquery(input_file, output_file):
    # I scan all available databases, not just the defaults.
    databases = ['afdb50', 'afdb-swissprot', 'afdb-proteome', 'mgnify_esm30', 'pdb100', 'gmgcl_id']

    # If the input doesn't already end in .pdb, I assume it's a UniProt ID or PDB ID and try to download it.
    if not input_file.endswith('.pdb'):
        print(f"Detected PDB ID or UniProt Accession: {input_file}. Downloading from RCSB or UniProt...")
        input_file = download_pdb(input_file)

    if not os.path.exists(input_file):
        sys.exit(f'File {input_file} not found.')

    # I make sure the output file ends with .tar.gz
    if not output_file.endswith('.tar.gz'):
        output_file += '.tar.gz'

    # I read the input PDB contents into memory.
    with open(input_file, 'r') as file:
        pdb_data = file.read()

    # I prompt the user for a Foldseek alignment mode (default is 3diaa).
    mode = input("Enter alignment mode (3diaa or tmalign, default is 3diaa): ") or "3diaa"

    # I submit the Foldseek search job.
    response = requests.post('https://search.foldseek.com/api/ticket',
                             data={'q': pdb_data, 'database[]': databases, 'mode': mode})
    response_json = response.json()

    if 'id' not in response_json:
        sys.exit(f'Error submitting job: {response_json}')
    ticket_id = response_json['id']

    # I poll the server until the job is marked COMPLETE.
    for _ in range(10):
        status = requests.get(f'https://search.foldseek.com/api/ticket/{ticket_id}').json()
        if status['status'] == "COMPLETE":
            break
        elif status['status'] == "ERROR":
            sys.exit('Foldseek API returned an error.')
        sleep(30)  # I wait 30 seconds between polls.

    # I download the result archive once complete.
    download = requests.get(f'https://search.foldseek.com/api/result/download/{ticket_id}', stream=True)
    with open(output_file, 'wb') as fd:
        for chunk in download.iter_content(chunk_size=128):
            fd.write(chunk)
    print(f'Results saved to {output_file}')

    # I extract uncharacterized entries from the .tar.gz archive.
    extract_uncharacterized_entries(output_file)

# If this file is being run directly (not imported), I prompt the user for inputs and launch the pipeline.
if __name__ == "__main__":
    input_id = input("Enter a PDB ID, UniProt accession, or a local PDB file path: ")
    output_file = input("Enter the output file name (will be saved as .tar.gz): ")
    foldseek_apiquery(input_id, output_file)

