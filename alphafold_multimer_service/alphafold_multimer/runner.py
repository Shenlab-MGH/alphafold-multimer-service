from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Callable

from alphafold_multimer_service.alphafold_multimer.parser import (
    compute_interface_pae_means,
    count_residues_per_chain_pdb,
    parse_a3m_chain_lengths,
    parse_rank1_from_log,
)
from alphafold_multimer_service.uniprot import extract_uniprot_id, fetch_fasta, fasta_to_sequence


ProgressCb = Callable[[str, str, float | None], None]


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _wrap_fasta_seq(seq: str, width: int = 80) -> str:
    return "\n".join(seq[i : i + width] for i in range(0, len(seq), width))


@dataclass(frozen=True)
class AlphaFoldMultimerRunResult:
    metrics: dict
    verification: dict
    artifacts: list[dict]


class AlphaFoldMultimerRunner:
    def run_pair(
        self,
        *,
        job_id: str,
        job_dir: Path,
        protein_a_ref: str,
        protein_b_ref: str,
        preset: str,
        num_recycles_override: int | None,
        progress_cb: ProgressCb,
    ) -> AlphaFoldMultimerRunResult:
        raise NotImplementedError


class MockAlphaFoldMultimerRunner(AlphaFoldMultimerRunner):
    """
    Deterministic runner for CI/e2e. Produces small artifacts + realistic fields.
    """

    def run_pair(
        self,
        *,
        job_id: str,
        job_dir: Path,
        protein_a_ref: str,
        protein_b_ref: str,
        preset: str,
        num_recycles_override: int | None,
        progress_cb: ProgressCb,
    ) -> AlphaFoldMultimerRunResult:
        progress_cb("mock", "Generating deterministic mock result", 10)
        artifacts_dir = job_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        # Tiny (not biologically meaningful) sequences so verification paths are exercised.
        seq_a = "MSEQNNTEMTFQIQRIYTKDISFEAPNAPHVFQKDW"  # 36
        seq_b = "MTPWLGLIVLLGSWSLGDWGAEAC"  # 24

        (artifacts_dir / "input.fasta").write_text(
            f">{job_id}\n{_wrap_fasta_seq(seq_a + ':' + seq_b)}\n", encoding="utf-8"
        )

        # A3M header lengths: 36,24
        (artifacts_dir / f"{job_id}.a3m").write_text(f"#36,24\n>query\n{seq_a}:{seq_b}\n", encoding="utf-8")

        # Minimal PDB with fake residues; enough to count chain residues.
        pdb_lines = []
        atom_i = 1
        for chain, nres in [("A", 36), ("B", 24)]:
            for resi in range(1, nres + 1):
                pdb_lines.append(
                    f"ATOM  {atom_i:5d}  CA  ALA {chain}{resi:4d}    0.000   0.000   0.000  1.00  0.00           C\n"
                )
                atom_i += 1
        pdb_lines.append("END\n")
        (artifacts_dir / "rank_001.pdb").write_text("".join(pdb_lines), encoding="utf-8")

        # Minimal PAE: 60x60 matrix with constant values.
        L = 36 + 24
        pae = [[10.0 for _ in range(L)] for _ in range(L)]
        (artifacts_dir / "pae.json").write_text(
            json.dumps({"predicted_aligned_error": pae}), encoding="utf-8"
        )

        # Mock log containing the parseable rank_001 line.
        log_txt = (
            f"{_now()} Running colabfold mock\n"
            f"{_now()} reranking models by 'multimer' metric\n"
            f"{_now()} rank_001_mock pLDDT=55.5 pTM=0.500 ipTM=0.250\n"
            f"{_now()} Done\n"
        )
        (artifacts_dir / "log.txt").write_text(log_txt, encoding="utf-8")

        parsed = parse_rank1_from_log(log_txt)
        iface_mean, ab, ba = compute_interface_pae_means(
            artifacts_dir / "pae.json", chain_a_len=36, chain_b_len=24
        )
        pdb_counts = count_residues_per_chain_pdb(artifacts_dir / "rank_001.pdb")

        metrics = {
            "iptm": parsed.iptm,
            "ptm": parsed.ptm,
            "ranking_confidence": round(parsed.ranking_confidence, 4),
            "plddt": parsed.plddt,
            "interface_pae_mean": iface_mean,
            "interface_pae_mean_ab": ab,
            "interface_pae_mean_ba": ba,
        }

        verification = {
            "chain_a_length_a3m": 36,
            "chain_b_length_a3m": 24,
            "chain_a_length_pdb": pdb_counts.get("A"),
            "chain_b_length_pdb": pdb_counts.get("B"),
            "chain_lengths_match": (pdb_counts.get("A") == 36 and pdb_counts.get("B") == 24),
        }

        artifacts = [
            {"name": "input.fasta", "path": str(artifacts_dir / "input.fasta"), "media_type": "text/plain"},
            {"name": f"{job_id}.a3m", "path": str(artifacts_dir / f"{job_id}.a3m"), "media_type": "text/plain"},
            {"name": "rank_001.pdb", "path": str(artifacts_dir / "rank_001.pdb"), "media_type": "chemical/x-pdb"},
            {"name": "pae.json", "path": str(artifacts_dir / "pae.json"), "media_type": "application/json"},
            {"name": "log.txt", "path": str(artifacts_dir / "log.txt"), "media_type": "text/plain"},
        ]

        progress_cb("mock", "Mock result ready", 100)
        return AlphaFoldMultimerRunResult(metrics=metrics, verification=verification, artifacts=artifacts)


class ColabFoldDockerRunner(AlphaFoldMultimerRunner):
    def __init__(
        self,
        *,
        colabfold_image: str,
        colabfold_cache_dir: Path,
        host_ptxas_path: Path | None,
    ) -> None:
        self._image = colabfold_image
        self._cache_dir = colabfold_cache_dir
        self._host_ptxas_path = host_ptxas_path

    def run_pair(
        self,
        *,
        job_id: str,
        job_dir: Path,
        protein_a_ref: str,
        protein_b_ref: str,
        preset: str,
        num_recycles_override: int | None,
        progress_cb: ProgressCb,
    ) -> AlphaFoldMultimerRunResult:
        job_dir.mkdir(parents=True, exist_ok=True)
        work_dir = job_dir / "work"
        out_dir = work_dir / "out"
        artifacts_dir = job_dir / "artifacts"
        work_dir.mkdir(parents=True, exist_ok=True)
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        progress_cb("fetch", "Fetching UniProt FASTA", 1)
        uniprot_a = extract_uniprot_id(protein_a_ref)
        uniprot_b = extract_uniprot_id(protein_b_ref)
        seq_a = fasta_to_sequence(fetch_fasta(uniprot_a))
        seq_b = fasta_to_sequence(fetch_fasta(uniprot_b))

        progress_cb("prepare", "Writing input FASTA", 3)
        input_fasta = work_dir / "input.fasta"
        input_fasta.write_text(f">{job_id}\n{_wrap_fasta_seq(seq_a + ':' + seq_b)}\n", encoding="utf-8")

        # Choose recycles
        if num_recycles_override is not None:
            num_recycles = int(num_recycles_override)
        else:
            num_recycles = 3 if preset == "fast" else 20

        # Build docker command
        docker_cmd: list[str] = [
            "docker",
            "run",
            "--rm",
            "--gpus",
            "all",
            "--shm-size=16g",
            "-v",
            f"{work_dir}:/work",
            "-w",
            "/work",
            "-v",
            f"{self._cache_dir}:/cache/colabfold",
        ]

        # RTX 5090 workaround: mount host ptxas into container if available.
        if self._host_ptxas_path and self._host_ptxas_path.exists() and os.access(self._host_ptxas_path, os.X_OK):
            docker_cmd += ["-v", f"{self._host_ptxas_path}:/usr/local/cuda/bin/ptxas:ro"]

        docker_cmd += [
            self._image,
            "colabfold_batch",
            "--model-type",
            "alphafold2_multimer_v3",
            "--rank",
            "multimer",
            "--num-recycle",
            str(num_recycles),
            str(input_fasta.name),
            str(out_dir.name),
        ]

        progress_cb("run", f"Running ColabFold (recycles={num_recycles})", 5)
        out_dir.mkdir(parents=True, exist_ok=True)

        # Stream docker output to a log for monitoring.
        docker_log = artifacts_dir / "docker.log.txt"
        with docker_log.open("w", encoding="utf-8") as lf:
            proc = subprocess.Popen(
                docker_cmd,
                cwd=str(work_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            assert proc.stdout is not None
            last_line = ""
            for line in proc.stdout:
                lf.write(line)
                lf.flush()
                last_line = line.strip()
                if last_line:
                    progress_cb("run", last_line, None)
            rc = proc.wait()
        if rc != 0:
            raise RuntimeError(f"ColabFold docker run failed (exit={rc}). See artifacts/docker.log.txt")

        progress_cb("parse", "Parsing ColabFold outputs", 90)

        # Discover key outputs. ColabFold prefixes files with the FASTA header (job_id).
        log_path = out_dir / "log.txt"
        if not log_path.exists():
            # Sometimes log sits in work_dir
            alt = work_dir / "log.txt"
            if alt.exists():
                log_path = alt
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
        parsed = parse_rank1_from_log(log_text)

        # Copy stable artifacts into artifacts/
        (artifacts_dir / "input.fasta").write_text(input_fasta.read_text(encoding="utf-8"), encoding="utf-8")
        (artifacts_dir / "log.txt").write_text(log_text, encoding="utf-8")

        # Locate rank_001 PDB and PAE JSON.
        pdb_candidates = sorted(out_dir.glob("*_unrelaxed_rank_001_*.pdb"))
        pae_candidates = sorted(out_dir.glob("*_predicted_aligned_error_v1.json"))
        a3m_candidates = sorted(out_dir.glob("*.a3m"))
        score_json_candidates = sorted(out_dir.glob("*_scores_rank_001_*.json"))

        pdb_path = pdb_candidates[0] if pdb_candidates else None
        pae_path = pae_candidates[0] if pae_candidates else None
        a3m_path = a3m_candidates[0] if a3m_candidates else None

        # verification / interface metrics are best-effort
        chain_a_len_a3m = chain_b_len_a3m = None
        chain_a_len_pdb = chain_b_len_pdb = None
        chain_lengths_match = False
        iface_mean = iface_ab = iface_ba = None

        if a3m_path is not None:
            try:
                chain_a_len_a3m, chain_b_len_a3m = parse_a3m_chain_lengths(a3m_path)
                shutil.copy2(a3m_path, artifacts_dir / a3m_path.name)
            except Exception:
                pass

        if pdb_path is not None:
            pdb_counts = count_residues_per_chain_pdb(pdb_path)
            chain_a_len_pdb = pdb_counts.get("A")
            chain_b_len_pdb = pdb_counts.get("B")
            shutil.copy2(pdb_path, artifacts_dir / "rank_001.pdb")

        if chain_a_len_a3m and chain_b_len_a3m and chain_a_len_pdb and chain_b_len_pdb:
            chain_lengths_match = (chain_a_len_a3m == chain_a_len_pdb) and (chain_b_len_a3m == chain_b_len_pdb)

        if pae_path is not None and chain_a_len_a3m and chain_b_len_a3m:
            iface_mean, iface_ab, iface_ba = compute_interface_pae_means(
                pae_path, chain_a_len=chain_a_len_a3m, chain_b_len=chain_b_len_a3m
            )
            shutil.copy2(pae_path, artifacts_dir / "pae.json")

        if score_json_candidates:
            shutil.copy2(score_json_candidates[0], artifacts_dir / "scores_rank_001.json")

        metrics = {
            "iptm": parsed.iptm,
            "ptm": parsed.ptm,
            "ranking_confidence": round(parsed.ranking_confidence, 4),
            "plddt": parsed.plddt,
            "interface_pae_mean": iface_mean,
            "interface_pae_mean_ab": iface_ab,
            "interface_pae_mean_ba": iface_ba,
        }
        verification = {
            "chain_lengths_match": bool(chain_lengths_match),
            "chain_a_length_a3m": chain_a_len_a3m,
            "chain_b_length_a3m": chain_b_len_a3m,
            "chain_a_length_pdb": chain_a_len_pdb,
            "chain_b_length_pdb": chain_b_len_pdb,
        }

        artifacts: list[dict] = []
        for path in sorted(artifacts_dir.iterdir()):
            if not path.is_file():
                continue
            media_type = None
            if path.name.endswith(".pdb"):
                media_type = "chemical/x-pdb"
            elif path.name.endswith(".json"):
                media_type = "application/json"
            else:
                media_type = "text/plain"
            artifacts.append(
                {
                    "name": path.name,
                    "path": str(path),
                    "media_type": media_type,
                    "size_bytes": path.stat().st_size,
                }
            )

        progress_cb("done", "Job succeeded", 100)
        return AlphaFoldMultimerRunResult(metrics=metrics, verification=verification, artifacts=artifacts)

