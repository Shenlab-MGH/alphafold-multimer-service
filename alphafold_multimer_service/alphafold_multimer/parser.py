from __future__ import annotations

from dataclasses import dataclass
import json
import re
from pathlib import Path
from typing import Iterable


_RANK_LINE_RE = re.compile(
    # ColabFold log lines look like:
    #   rank_001_alphafold2_multimer_v3_model_5_seed_000 pLDDT=45.8 pTM=0.312 ipTM=0.192
    r"^.*rank_001.*\bpLDDT=(?P<plddt>[0-9.]+)\s+"
    r"pTM=(?P<ptm>[0-9.]+)\s+ipTM=(?P<iptm>[0-9.]+)\s*$"
)


@dataclass(frozen=True)
class ParsedRank1:
    iptm: float
    ptm: float
    plddt: float

    @property
    def ranking_confidence(self) -> float:
        # ColabFold multimer ranking metric
        return 0.8 * self.iptm + 0.2 * self.ptm


def parse_rank1_from_log(log_text: str) -> ParsedRank1:
    for line in log_text.splitlines():
        m = _RANK_LINE_RE.match(line.strip())
        if not m:
            continue
        iptm = float(m.group("iptm"))
        ptm = float(m.group("ptm"))
        plddt = float(m.group("plddt"))
        return ParsedRank1(iptm=iptm, ptm=ptm, plddt=plddt)
    raise ValueError("Could not find rank_001 metrics in log.txt")


def count_residues_per_chain_pdb(pdb_path: Path) -> dict[str, int]:
    residues: set[tuple[str, str, str]] = set()
    with pdb_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if not (line.startswith("ATOM") or line.startswith("HETATM")):
                continue
            chain = line[21:22]
            resseq = line[22:26].strip()
            icode = line[26:27].strip()
            residues.add((chain, resseq, icode))
    out: dict[str, int] = {}
    for chain, _, _ in residues:
        out[chain] = out.get(chain, 0) + 1
    return out


def parse_a3m_chain_lengths(a3m_path: Path) -> tuple[int, int]:
    """
    ColabFold writes an a3m header like:
      #833,211
    for two-chain inputs.
    """
    with a3m_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                parts = line[1:].split(",")
                if len(parts) < 2:
                    break
                return int(parts[0]), int(parts[1])
            # header must be first non-empty line; if it isn't there, stop
            break
    raise ValueError(f"Missing #lenA,lenB header in a3m: {a3m_path}")


def find_first(globs: Iterable[Path]) -> Path:
    for p in globs:
        if p.exists():
            return p
    raise FileNotFoundError("No matching file found")


def compute_interface_pae_means(
    pae_json_path: Path, *, chain_a_len: int, chain_b_len: int
) -> tuple[float, float, float]:
    obj = json.loads(pae_json_path.read_text(encoding="utf-8"))
    pae = obj.get("predicted_aligned_error")
    if pae is None:
        raise ValueError("PAE JSON missing predicted_aligned_error")

    # Avoid numpy dependency; compute means in pure Python.
    # PAE is square [L][L], L = chain_a_len + chain_b_len.
    L = len(pae)
    expected = chain_a_len + chain_b_len
    if L != expected:
        raise ValueError(f"PAE size mismatch: got {L}, expected {expected}")

    def mean_block(rows: range, cols: range) -> float:
        total = 0.0
        n = 0
        for i in rows:
            row = pae[i]
            for j in cols:
                total += float(row[j])
                n += 1
        if n == 0:
            raise ValueError("Empty PAE block")
        return total / n

    a_rows = range(0, chain_a_len)
    b_rows = range(chain_a_len, expected)
    a_cols = range(0, chain_a_len)
    b_cols = range(chain_a_len, expected)

    ab = mean_block(a_rows, b_cols)  # A -> B
    ba = mean_block(b_rows, a_cols)  # B -> A
    return (ab + ba) / 2.0, ab, ba
