from __future__ import annotations

import pytest

from alphafold_multimer_service.uniprot import extract_uniprot_id


@pytest.mark.parametrize(
    "inp,expected",
    [
        ("P35625", "P35625"),
        ("Q13424-1", "Q13424-1"),
        (" https://www.uniprot.org/uniprotkb/P35625/entry ", "P35625"),
        ("https://rest.uniprot.org/uniprotkb/Q13424-1.fasta", "Q13424-1"),
        ("https://www.uniprot.org/uniprot/P35625.fasta", "P35625"),
        ("sp|P35625|TIMP3_HUMAN", "P35625"),
    ],
)
def test_extract_uniprot_id(inp: str, expected: str) -> None:
    assert extract_uniprot_id(inp) == expected


@pytest.mark.parametrize("inp", ["", "   ", "not a url!!", "https://example.com/foo/bar"])
def test_extract_uniprot_id_rejects(inp: str) -> None:
    with pytest.raises(ValueError):
        extract_uniprot_id(inp)

