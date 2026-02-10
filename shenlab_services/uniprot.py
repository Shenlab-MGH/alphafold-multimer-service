from __future__ import annotations

import re
from urllib.parse import urlparse

import requests


_ACCESSION_LIKE_RE = re.compile(r"^[A-Za-z0-9]{3,15}(?:-[0-9]{1,3})?$")


def extract_uniprot_id(uniprot_ref: str) -> str:
    """
    Accepts a UniProt accession-ish string or a UniProt URL and returns the id.

    Examples:
      - P35625
      - Q13424-1
      - https://www.uniprot.org/uniprotkb/P35625/entry
      - https://rest.uniprot.org/uniprotkb/Q13424-1.fasta
    """
    s = (uniprot_ref or "").strip()
    if not s:
        raise ValueError("Empty UniProt reference")

    if s.startswith("http://") or s.startswith("https://"):
        parsed = urlparse(s)
        host = (parsed.netloc or "").lower()
        if not (host.endswith("uniprot.org") or host == "rest.uniprot.org"):
            raise ValueError(f"Not a UniProt URL: {s}")
        parts = [p for p in parsed.path.split("/") if p]
        # walk backwards to find a plausible id segment
        for part in reversed(parts):
            part = part.strip()
            if not part:
                continue
            part = re.sub(r"\.(fasta|fa|txt)$", "", part, flags=re.IGNORECASE)
            if part.lower() in {"entry", "uniprotkb", "uniprot"}:
                continue
            if _ACCESSION_LIKE_RE.match(part):
                return part
        raise ValueError(f"Could not extract UniProt id from URL: {s}")

    # handle FASTA headers like: sp|P35625|TIMP3_HUMAN
    if "|" in s:
        for token in s.split("|"):
            token = token.strip()
            if _ACCESSION_LIKE_RE.match(token):
                return token

    if not _ACCESSION_LIKE_RE.match(s):
        raise ValueError(f"Not a UniProt accession-like string: {s}")
    return s


def fetch_fasta(uniprot_id: str, *, timeout_s: float = 30.0) -> str:
    url = f"https://rest.uniprot.org/uniprotkb/{uniprot_id}.fasta"
    r = requests.get(url, timeout=timeout_s, headers={"User-Agent": "shenlab-services/alphafold-multimer"})
    r.raise_for_status()
    return r.text


def fasta_to_sequence(fasta_text: str) -> str:
    seq_lines: list[str] = []
    for line in fasta_text.splitlines():
        line = line.strip()
        if not line or line.startswith(">"):
            continue
        seq_lines.append(line)
    seq = "".join(seq_lines).replace(" ", "").upper()
    if not seq:
        raise ValueError("No sequence found in FASTA")
    return seq
