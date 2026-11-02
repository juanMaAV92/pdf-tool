from pathlib import Path

import pymupdf
import pytest

from pdftool.core.errors import UserError
from pdftool.core.jobs import JobCancelled
from pdftool.tools.pdf2images.logic import (
    MAX_JPG_SIDE,
    MAX_PIXELS,
    check_limits,
    page_pixels,
    pdf2images,
    result_folder_for,
)
from pdftool.tools.pdf2images.params import Pdf2ImagesParams


def _pdf(path: Path, pages: int = 2, size=(595, 842), rotate: int = 0) -> Path:
    doc = pymupdf.open()
    for number in range(pages):
        page = doc.new_page(width=size[0], height=size[1])
        page.insert_text((72, 72), f"Page {number + 1}")
        if rotate:
            page.set_rotation(rotate)
    doc.save(path)
    doc.close()
    return path


@pytest.mark.parametrize("size", [(595, 842), (595.28, 841.89), (612, 792)])
@pytest.mark.parametrize("dpi", [72, 150, 300, 600])
def test_page_pixels_match_the_rendered_image(tmp_path, size, dpi):
    with pymupdf.open(_pdf(tmp_path / "a.pdf", pages=1, size=size)) as doc:
        page = doc[0]
        zoom = dpi / 72
        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
        assert page_pixels(page.rect, dpi) == (pix.width, pix.height)


def test_page_pixels_respect_page_rotation(tmp_path):
    path = _pdf(tmp_path / "a.pdf", pages=1, size=(600, 800), rotate=90)
    with pymupdf.open(path) as doc:
        assert page_pixels(doc[0].rect, 72) == (800, 600)


def test_one_folder_with_numbered_images_per_pdf(tmp_path):
    source = _pdf(tmp_path / "doc.pdf")

    result = pdf2images([source], Pdf2ImagesParams())

    folder = tmp_path / "doc_imágenes"
    assert result.outputs == [folder / "doc_p001.jpg", folder / "doc_p002.jpg"]
    assert all(path.exists() for path in result.outputs)
    assert result.items[0].output_path == folder
    assert "2" in result.summary and folder.name in result.summary


def test_a_single_page_pdf_also_gets_a_folder(tmp_path):
    result = pdf2images([_pdf(tmp_path / "doc.pdf", pages=1)], Pdf2ImagesParams())

    assert result.outputs == [tmp_path / "doc_imágenes" / "doc_p001.jpg"]


def test_numbering_widens_past_999_pages(tmp_path):
    source = _pdf(tmp_path / "doc.pdf", pages=1000, size=(10, 10))

    result = pdf2images([source], Pdf2ImagesParams(dpi=72))

    assert result.outputs[0].name == "doc_p0001.jpg"
    assert result.outputs[-1].name == "doc_p1000.jpg"


def test_png_and_jpg_keep_size_and_dpi(tmp_path):
    source = _pdf(tmp_path / "doc.pdf", pages=1)
    for image_format in ("jpg", "png"):
        result = pdf2images([source], Pdf2ImagesParams(format=image_format, dpi=150))
        assert result.outputs[0].suffix == f".{image_format}"
        pix = pymupdf.Pixmap(str(result.outputs[0]))
        assert (pix.width, pix.height) == page_pixels(pymupdf.Rect(0, 0, 595, 842), 150)
        assert pix.xres == 150 and pix.yres == 150
        assert pix.alpha == 0


def test_never_overwrites_a_previous_export(tmp_path):
    source = _pdf(tmp_path / "doc.pdf", pages=1)

    first = pdf2images([source], Pdf2ImagesParams())
    second = pdf2images([source], Pdf2ImagesParams())

    assert first.items[0].output_path != second.items[0].output_path
    assert second.items[0].output_path == tmp_path / "doc_imágenes (1)"


def test_output_dir_is_respected(tmp_path):
    out = tmp_path / "salida"
    out.mkdir()
    source = _pdf(tmp_path / "doc.pdf", pages=1)

    result = pdf2images([source], Pdf2ImagesParams(output_dir=out))

    assert result.items[0].output_path == out / "doc_imágenes"


def test_password_pdf_is_a_user_error_naming_protect(tmp_path):
    source = _pdf(tmp_path / "doc.pdf", pages=1)
    locked = tmp_path / "locked.pdf"
    with pymupdf.open(source) as doc:
        doc.save(
            locked, encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="u", owner_pw="o"
        )

    with pytest.raises(UserError, match="Proteger PDF"):
        pdf2images([locked], Pdf2ImagesParams())
    assert not (tmp_path / "locked_imágenes").exists()


def test_batch_reports_a_failed_file_and_keeps_going(tmp_path):
    good = _pdf(tmp_path / "good.pdf", pages=1)
    locked = tmp_path / "locked.pdf"
    with pymupdf.open(good) as doc:
        doc.save(
            locked, encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="u", owner_pw="o"
        )

    result = pdf2images([locked, good], Pdf2ImagesParams())

    assert result.items[0].ok is False
    assert result.items[1].ok is True
    assert result.outputs == [tmp_path / "good_imágenes" / "good_p001.jpg"]


def test_owner_restrictions_export_with_a_warning(tmp_path):
    source = _pdf(tmp_path / "doc.pdf", pages=1)
    restricted = tmp_path / "restricted.pdf"
    with pymupdf.open(source) as doc:
        doc.save(
            restricted,
            encryption=pymupdf.PDF_ENCRYPT_AES_256,
            owner_pw="o",
            permissions=pymupdf.PDF_PERM_ACCESSIBILITY,
        )

    result = pdf2images([restricted], Pdf2ImagesParams())

    assert result.outputs[0].exists()
    assert any("restricciones" in w for w in result.items[0].warnings)


def test_plain_pdf_has_no_warning(tmp_path):
    result = pdf2images([_pdf(tmp_path / "doc.pdf", pages=1)], Pdf2ImagesParams())

    assert result.items[0].warnings == ()


def test_cancel_leaves_finished_folders_only(tmp_path):
    first = _pdf(tmp_path / "first.pdf", pages=1)
    second = _pdf(tmp_path / "second.pdf", pages=3)

    def cancel_on_second(_fraction: float, message: str) -> None:
        if "second.pdf" in message and "2" in message.split(":")[-1]:
            raise JobCancelled()

    with pytest.raises(JobCancelled):
        pdf2images([first, second], Pdf2ImagesParams(), cancel_on_second)

    assert (tmp_path / "first_imágenes").exists()
    assert not (tmp_path / "second_imágenes").exists()
    assert list(tmp_path.glob(".pdf-tool-*")) == []


def test_limits_reject_before_rendering_and_give_the_max_dpi(tmp_path):
    source = _pdf(tmp_path / "doc.pdf", pages=2)
    with pymupdf.open(source) as doc:
        doc[1].set_mediabox(pymupdf.Rect(0, 0, 3370, 4768))  # mayor que A0
        with pytest.raises(UserError) as caught:
            check_limits(doc, 300, "png")
    message = str(caught.value)
    assert "2" in message
    max_dpi = int(message.split("Usa ")[1].split(" ")[0])
    width, height = page_pixels(pymupdf.Rect(0, 0, 3370, 4768), max_dpi)
    assert width * height <= MAX_PIXELS
    width, height = page_pixels(pymupdf.Rect(0, 0, 3370, 4768), max_dpi + 1)
    assert width * height > MAX_PIXELS


def test_a0_at_300_dpi_fits(tmp_path):
    source = _pdf(tmp_path / "doc.pdf", pages=1, size=(2384, 3370))
    with pymupdf.open(source) as doc:
        check_limits(doc, 300, "png")


def test_jpg_side_limit_only_applies_to_jpg(tmp_path):
    side = MAX_JPG_SIDE + 1000
    source = _pdf(tmp_path / "doc.pdf", pages=1, size=(side, 72))
    with pymupdf.open(source) as doc:
        check_limits(doc, 72, "png")
        with pytest.raises(UserError):
            check_limits(doc, 72, "jpg")


def test_page_too_large_at_any_allowed_dpi_has_its_own_message(tmp_path):
    source = _pdf(tmp_path / "doc.pdf", pages=1, size=(14400, 14400))
    with (
        pymupdf.open(source) as doc,
        pytest.raises(UserError, match="demasiado grande para exportarla"),
    ):
        check_limits(doc, 300, "png")


def test_result_folder_one_pdf_is_its_images_folder():
    folder = Path("/a/doc_imágenes")
    assert result_folder_for([folder]) == folder


def test_result_folder_same_parent_is_that_parent():
    assert result_folder_for([Path("/a/x_i"), Path("/a/y_i")]) == Path("/a")


def test_result_folder_different_parents_is_the_common_path():
    folders = [Path("/a/b/x_i"), Path("/a/c/y_i")]
    assert result_folder_for(folders) == Path("/a")


def test_result_folder_with_only_root_in_common_is_the_first():
    folders = [Path("/a/x_i"), Path("/b/y_i")]
    assert result_folder_for(folders) == Path("/a/x_i")
