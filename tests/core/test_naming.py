from pathlib import Path

from pdftool.core.naming import output_path, unique_path


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


def test_output_path_composes_stem_and_suffix(tmp_path):
    assert output_path(tmp_path / "doc.pdf", "marca") == tmp_path / "doc_marca.pdf"


def test_output_path_lands_next_to_the_input(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    assert output_path(sub / "doc.pdf", "marca").parent == sub


def test_output_path_custom_stem_replaces_the_inputs(tmp_path):
    out = output_path(tmp_path / "doc_5MB.pdf", "2MB", stem="doc")
    assert out == tmp_path / "doc_2MB.pdf"


def test_output_path_avoids_an_existing_file(tmp_path):
    (tmp_path / "doc_marca.pdf").write_bytes(b"x")
    assert output_path(tmp_path / "doc.pdf", "marca") == tmp_path / "doc_marca (1).pdf"


def test_output_path_never_returns_the_input_even_if_absent_from_disk(tmp_path):
    # Sin taken=(input,) esto devolvería la propia entrada: nada existe en disco.
    out = output_path(tmp_path / "doc_marca.pdf", "marca", stem="doc")
    assert out == tmp_path / "doc_marca (1).pdf"


def test_output_path_chains_when_several_are_taken(tmp_path):
    for name in ("doc_marca.pdf", "doc_marca (1).pdf"):
        (tmp_path / name).write_bytes(b"x")
    assert output_path(tmp_path / "doc.pdf", "marca") == tmp_path / "doc_marca (2).pdf"


def test_output_path_empty_stem_is_honoured_not_ignored(tmp_path):
    # stem="" es un valor válido (distinto de None) y debe respetarse,
    # no caer de vuelta al stem del archivo de entrada.
    out = output_path(tmp_path / "doc.pdf", "marca", stem="")
    assert out == tmp_path / "_marca.pdf"


def test_output_path_uses_out_dir_when_given(tmp_path):
    destino = tmp_path / "destino"
    destino.mkdir()
    out = output_path(tmp_path / "doc.pdf", "marca", out_dir=destino)
    assert out == destino / "doc_marca.pdf"


def test_output_path_without_out_dir_lands_next_to_the_input(tmp_path):
    assert output_path(tmp_path / "doc.pdf", "marca") == tmp_path / "doc_marca.pdf"


def test_collision_is_resolved_in_the_destination_not_the_origin(tmp_path):
    """Lo ocupado en la carpeta de origen no afecta; lo del destino sí."""
    destino = tmp_path / "destino"
    destino.mkdir()
    (tmp_path / "doc_marca.pdf").write_bytes(b"en origen")
    out = output_path(tmp_path / "doc.pdf", "marca", out_dir=destino)
    assert out == destino / "doc_marca.pdf"

    (destino / "doc_marca.pdf").write_bytes(b"en destino")
    out = output_path(tmp_path / "doc.pdf", "marca", out_dir=destino)
    assert out == destino / "doc_marca (1).pdf"
