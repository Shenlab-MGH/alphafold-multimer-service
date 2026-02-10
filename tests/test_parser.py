from __future__ import annotations

import json
from pathlib import Path

import pytest

from shenlab_services.alphafold_multimer.parser import (
    compute_interface_pae_means,
    count_residues_per_chain_pdb,
    parse_a3m_chain_lengths,
    parse_rank1_from_log,
)


def test_parse_rank1_from_log() -> None:
    txt = "\n".join(
        [
            "something else",
            "2026-02-10 rank_001_model_x pLDDT=45.8 pTM=0.312 ipTM=0.192",
            "Done",
        ]
    )
    parsed = parse_rank1_from_log(txt)
    assert parsed.iptm == pytest.approx(0.192)
    assert parsed.ptm == pytest.approx(0.312)
    assert parsed.plddt == pytest.approx(45.8)
    assert parsed.ranking_confidence == pytest.approx(0.216)


def test_parse_a3m_chain_lengths(tmp_path: Path) -> None:
    p = tmp_path / "x.a3m"
    p.write_text("#833,211\n>q\nAAA:BBB\n", encoding="utf-8")
    a, b = parse_a3m_chain_lengths(p)
    assert (a, b) == (833, 211)


def test_count_residues_per_chain_pdb(tmp_path: Path) -> None:
    p = tmp_path / "x.pdb"
    p.write_text(
        "".join(
            [
                "ATOM      1  CA  ALA A   1    0.000   0.000   0.000  1.00  0.00           C\n",
                "ATOM      2  CA  ALA A   2    0.000   0.000   0.000  1.00  0.00           C\n",
                "ATOM      3  CA  ALA B   1    0.000   0.000   0.000  1.00  0.00           C\n",
                "END\n",
            ]
        ),
        encoding="utf-8",
    )
    counts = count_residues_per_chain_pdb(p)
    assert counts["A"] == 2
    assert counts["B"] == 1


def test_compute_interface_pae_means(tmp_path: Path) -> None:
    # chain A len 2, chain B len 1 => L=3
    pae = [
        [0.0, 1.0, 10.0],
        [2.0, 3.0, 20.0],
        [30.0, 40.0, 4.0],
    ]
    p = tmp_path / "pae.json"
    p.write_text(json.dumps({"predicted_aligned_error": pae}), encoding="utf-8")

    iface, ab, ba = compute_interface_pae_means(p, chain_a_len=2, chain_b_len=1)
    # AB block is rows [0,1] cols [2] => mean(10,20)=15
    assert ab == pytest.approx(15.0)
    # BA block is rows [2] cols [0,1] => mean(30,40)=35
    assert ba == pytest.approx(35.0)
    assert iface == pytest.approx(25.0)

