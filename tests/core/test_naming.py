from pathlib import Path

from pdftool.core.naming import unique_path


def test_free_candidate_is_returned_unchanged(tmp_path):
    assert unique_path(tmp_path / "a.pdf") == tmp_path / "a.pdf"


def test_existing_file_gets_suffix(tmp_path):
    (tmp_path / "a.pdf").write_bytes(b"x")
    assert unique_path(tmp_path / "a.pdf") == tmp_path / "a (1).pdf"


def test_taken_paths_are_avoided_even_if_absent_from_disk(tmp_path):
    taken = [tmp_path / "a.pdf"]
    assert unique_path(tmp_path / "a.pdf", taken=taken) == tmp_path / "a (1).pdf"


def test_disk_and_taken_are_both_avoided(tmp_path):
    (tmp_path / "a.pdf").write_bytes(b"x")
    taken = [tmp_path / "a (1).pdf"]
    assert unique_path(tmp_path / "a.pdf", taken=taken) == tmp_path / "a (2).pdf"


def test_chain_of_three_duplicates(tmp_path):
    for name in ("a.pdf", "a (1).pdf", "a (2).pdf"):
        (tmp_path / name).write_bytes(b"x")
    assert unique_path(tmp_path / "a.pdf") == tmp_path / "a (3).pdf"


def test_extension_is_preserved(tmp_path):
    (tmp_path / "foto.png").write_bytes(b"x")
    assert unique_path(tmp_path / "foto.png") == tmp_path / "foto (1).png"


def test_stem_with_spaces_and_dots(tmp_path):
    (tmp_path / "informe v1.2.pdf").write_bytes(b"x")
    assert (unique_path(tmp_path / "informe v1.2.pdf")
            == tmp_path / "informe v1.2 (1).pdf")
