# AlphaFold-Multimer (Pair) Service

## What It Does

Input:

- `protein_a`: UniProt accession or UniProt URL
- `protein_b`: UniProt accession or UniProt URL

Output:

- **Primary score (single number)**: `ranking_confidence = 0.8*ipTM + 0.2*pTM`
- Detailed metrics: `ipTM`, `pTM`, `pLDDT`, interface PAE summary
- Verification: chain lengths from `.a3m` match chain residue counts in rank_001 `.pdb`
- Artifacts: `rank_001.pdb`, `pae.json`, `log.txt`, etc.

## Pipeline (Backend)

1. Parse UniProt references into accessions.
2. Fetch FASTA from UniProt (`https://rest.uniprot.org/uniprotkb/{id}.fasta`).
3. Build a ColabFold multimer input FASTA using the `A:B` format.
4. Run ColabFold in Docker:
   - `colabfold_batch --model-type alphafold2_multimer_v3 --rank multimer`
   - `fast` preset uses `--num-recycle 3` (quick scoring)
   - `full` preset uses `--num-recycle 20` (slower, more thorough)
5. Parse the **rank_001** line from `log.txt` to get **unrounded** `ipTM`, `pTM`, `pLDDT`.
6. Compute:
   - `ranking_confidence = 0.8*ipTM + 0.2*pTM`
7. Verification (best-effort):
   - parse `#lenA,lenB` from `.a3m`
   - count residues per chain (A/B) from the rank_001 `.pdb`
   - compute interface PAE mean from `predicted_aligned_error_v1.json` (A->B and B->A blocks)

## Why We Parse `log.txt`

ColabFold also writes a `scores_rank_001_*.json`, but values can be rounded. For a stable “single number” output, we treat the `log.txt` rank line as the source of truth.

## Interpreting The Number

- `ipTM` and `ranking_confidence` close to `1.0` suggests high confidence in the interface.
- Values near `0.0` suggest low confidence interaction (or insufficient signal / wrong biological context).

The score is a **model confidence** proxy, not a binding affinity.

