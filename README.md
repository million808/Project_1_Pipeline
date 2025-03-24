## Project Purpose

This pipeline was created by **Max Balter** as part of a computational protein discovery project. The goal is to reduce the ~200 mi$

## Overview of the Pipeline

### 1. `01_foldseek_download_uncharacterized_pipeline.py`
This script:
- Accepts a PDB ID, UniProt accession, or local PDB file.
- Submits it to the **Foldseek Web API** across all major databases (`afdb50`, `afdb-swissprot`, `afdb-proteome`, `mgnify_esm30`, `$
- Filters Foldseek results for only hits labeled as **"uncharacterized protein"**.
- Outputs a filtered `uncharacterized_hits.txt` file.
- Also writes a seed UniProt accession to `query_seed_accession.txt`.

### 2. `seed_selector.py`
This script:
- Reads `query_seed_accession.txt` to determine the UniProt accession of the query used for Foldseek.
- Downloads its AlphaFold PDB structure if missing.
- Updates the `config.json` file with the appropriate `seed_protein_file` and default active sites.
- Fully automates seed selection for ActSeek based on your Foldseek query.

### 3. `02_ActSeek_process_pipeline.py`
This script:
- Reads `uncharacterized_hits.txt` and extracts unique UniProt accessions.
- Downloads all corresponding AlphaFold models to a `../structures` directory.
- Writes those accessions to `test.txt` (which ActSeek uses in batch mode).
- Ensures the seed structure exists from the previous step.
- Executes ActSeek in **batch mode** using the parameters in `config.json`.
- Outputs results to `../results/actseek_results.txt`.

---

## File Outputs
- `uncharacterized_hits.txt` — Filtered Foldseek alignments matching uncharacterized proteins.
- `test.txt` — List of unique UniProt accessions for ActSeek input.
- `../results/actseek_results.txt` — ActSeek structural similarity results.
- `../structures/` — AlphaFold PDB structures downloaded automatically.
- `config.json` — Configuration file dynamically updated by `seed_selector.py`.

---

## Requirements

You must install the following dependencies to run the pipeline.

### `requirements.txt`
```txt
requests
biopython
tqdm
wget
numpy==1.26.4
scipy
matplotlib
plotly
pyKVFinder
actseek @ git+https://github.com/vttresearch/ActSeek.git

