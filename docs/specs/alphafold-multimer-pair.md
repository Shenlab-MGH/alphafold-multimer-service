# Spec: AlphaFold-Multimer (Pair) Service

## Goal

Given **two UniProt links (or accessions)**, run **AlphaFold-Multimer** and return:

- A single **primary score number** (`ranking_confidence`)
- Detailed metrics (`ipTM`, `pTM`, `pLDDT`, interface PAE summary, etc.)
- Verification checks (chain lengths, artifact presence)
- Artifact download links (PDB, PAE JSON, score JSON, logs)

## Behavior (BDD Scenarios)

### Scenario: Submit a pair job and get a result

Given I have two valid UniProt references `protein_a` and `protein_b`  
And the backend API is reachable at `MONITOR_API_BASE`  
When I `POST /api/v1/services/alphafold-multimer/jobs` with `preset=fast`  
Then I receive a `job_id`  
And `GET /api/v1/jobs/{job_id}` eventually becomes `status=succeeded`  
And `GET /api/v1/jobs/{job_id}/result` returns:

- `primary_score.name = "ranking_confidence"`
- `primary_score.value` is a number
- `metrics.iptm`, `metrics.ptm`, `metrics.plddt` are numbers
- `verification.chain_lengths_match = true` (when artifacts include PDB)

### Scenario: Reject invalid UniProt references

Given I provide an invalid UniProt reference (not a URL and not an accession-like string)  
When I submit a job  
Then the API responds `422` with an error message

### Scenario: Result requested before job completion

Given I submitted a job and it is `queued` or `running`  
When I `GET /api/v1/jobs/{job_id}/result`  
Then I receive `409` with `status` and a retry hint

### Scenario: Unknown job id

When I `GET /api/v1/jobs/not-a-real-id`  
Then I receive `404`

### Scenario: Optional auth token

Given the server is configured with an API token  
When I submit a job without `Authorization: Bearer <token>`  
Then I receive `401`

