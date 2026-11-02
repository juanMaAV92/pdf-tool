from __future__ import annotations

import re
import string
from pathlib import Path

import pymupdf

from pdftool.core.atomic import atomic_output
from pdftool.core.batch import noop_progress
from pdftool.core.errors import UserError
from pdftool.core.naming import localized_suffix, output_path
from pdftool.core.pages import Plan, parse_plan
from pdftool.core.plugin import Progress, ToolResult
from pdftool.i18n import t
from pdftool.tools.organize.params import OrganizeParams

_REFERENCE = re.compile(r"(\d+) 0 R")
# Par de una hoja de `/Names/Dests`: nombre (literal o hexadecimal) y destino.
# Lo que no encaje se queda como está y lo detecta el invariante de páginas.
_NAME_TREE_PAIR = re.compile(
    r"(?:\((?:\\.|[^\\()])*\)|<[0-9A-Fa-f\s]*>)\s*"
    r"(\d+ 0 R|\[[^\]]*\]|<<.*?>>)",
    re.DOTALL,
)
_NAME_REGULAR = frozenset(string.ascii_letters + string.digits + "._+-:")
# Saltos máximos de un destino a su página: destino -> objeto -> /D -> página.
_MAX_DESTINATION_HOPS = 3


def read_page_count(path: Path) -> int:
    """Páginas del PDF; `UserError` si hace falta contraseña para abrirlo."""
    with pymupdf.open(str(path)) as doc:
        _refuse_password(doc)
        return doc.page_count


def identity_plan(page_count: int) -> Plan:
    return [(page, 0) for page in range(1, page_count + 1)]


def rotate(plan: Plan, positions: list[int], delta: int) -> Plan:
    selected = set(positions)
    return [
        (page, (rotation + delta) % 360 if index in selected else rotation)
        for index, (page, rotation) in enumerate(plan)
    ]


def move_to(plan: Plan, positions: list[int], target: int) -> Plan:
    """Lleva la selección al hueco anterior a `target` (`len(plan)` = al final)."""
    selected = set(positions)
    moved = [plan[index] for index in sorted(selected)]
    before = [
        entry for index, entry in enumerate(plan[:target]) if index not in selected
    ]
    after = [
        entry
        for index, entry in enumerate(plan[target:], start=target)
        if index not in selected
    ]
    return before + moved + after


def shift(plan: Plan, positions: list[int], direction: int) -> Plan:
    """Mueve cada página elegida un puesto; un bloque en el borde no se deforma."""
    result = list(plan)
    selected = set(positions)
    for position in sorted(selected, reverse=direction > 0):
        neighbor = position + direction
        if 0 <= neighbor < len(result) and neighbor not in selected:
            result[position], result[neighbor] = result[neighbor], result[position]
            selected.remove(position)
            selected.add(neighbor)
    return result


def reverse(plan: Plan) -> Plan:
    return plan[::-1]


def duplicate(plan: Plan, positions: list[int]) -> Plan:
    selected = set(positions)
    result: Plan = []
    for index, entry in enumerate(plan):
        result.append(entry)
        if index in selected:
            result.append(entry)
    return result


def delete(plan: Plan, positions: list[int]) -> Plan:
    selected = set(positions)
    result = [entry for index, entry in enumerate(plan) if index not in selected]
    if not result:
        raise UserError(t("tool.organize.error.empty_result"))
    return result


def extract(plan: Plan, positions: list[int]) -> Plan:
    return [plan[index] for index in sorted(set(positions))]


def apply_plan(doc: pymupdf.Document, plan: Plan) -> list[str]:
    """Deja `doc` tal como pide el plan y devuelve los avisos para el usuario."""
    _refuse_repeated_forms(doc, plan)
    retired = sorted(set(range(1, doc.page_count + 1)) - {page for page, _ in plan})

    warnings: list[str] = []
    if plan == identity_plan(doc.page_count):
        warnings.append(t("tool.organize.warning.identity"))
    if doc.get_sigflags() > 0:
        warnings.append(t("tool.organize.warning.signature"))

    targets = _final_page_xrefs(doc, plan)
    if retired:
        if doc.embfile_count() > 0:
            warnings.append(t("tool.organize.warning.attachments"))
        if _remove_pages(doc, retired):
            warnings.append(t("tool.organize.warning.tags"))
    _reorder(doc, targets)
    for index, (_page, rotation) in enumerate(plan):
        if rotation:
            page = doc[index]
            page.set_rotation((page.rotation + rotation) % 360)
    return warnings


def organize(
    inputs: list[Path], params: OrganizeParams, progress: Progress = noop_progress
) -> ToolResult:
    if not inputs:
        raise ValueError("inputs está vacío")
    source = Path(inputs[0])
    if not source.exists():
        raise FileNotFoundError(source)

    with pymupdf.open(str(source)) as doc:
        _refuse_password(doc)
        pages_in = doc.page_count
        plan = parse_plan(params.pages, pages_in)
        progress(0.0, t("tool.organize.progress.apply"))
        warnings = apply_plan(doc, plan)
        progress(0.5, t("tool.organize.progress.save"))
        target = output_path(
            source,
            localized_suffix("tool.organize.suffix"),
            out_dir=params.output_dir,
        )
        with atomic_output(target) as temporary:
            _save(doc, temporary)
            if _has_orphan_pages(temporary):
                _rebuild(source, plan, temporary)
                warnings.append(t("tool.organize.warning.rebuilt"))
                if _has_orphan_pages(temporary):
                    raise UserError(t("tool.organize.error.orphans"))

    progress(1.0, t("tool.organize.progress.save"))
    return ToolResult(
        outputs=[target],
        summary=t("tool.organize.summary", name=target.name, count=len(plan)),
        warnings=warnings,
        metrics={
            "pages_in": pages_in,
            "pages_out": len(plan),
            "bytes_in": source.stat().st_size,
            "bytes_out": target.stat().st_size,
        },
    )


def _refuse_password(doc: pymupdf.Document) -> None:
    if doc.needs_pass:
        raise UserError(t("core.pages.error.password", tool=t("tool.protect.name")))


def _refuse_repeated_forms(doc: pymupdf.Document, plan: Plan) -> None:
    """Dos copias de una página con campos compartirían el mismo widget."""
    seen: set[int] = set()
    for page, _rotation in plan:
        if page in seen and doc[page - 1].first_widget is not None:
            raise UserError(t("tool.organize.error.duplicate_form", page=page))
        seen.add(page)


def _final_page_xrefs(doc: pymupdf.Document, plan: Plan) -> list[int]:
    """Identifica cada puesto por xref: los índices cambian al borrar y mover."""
    seen: set[int] = set()
    targets: list[int] = []
    for page, _rotation in plan:
        if page in seen:
            doc.fullcopy_page(page - 1)  # al final: no desplaza las demás
            targets.append(doc.page_xref(doc.page_count - 1))
        else:
            seen.add(page)
            targets.append(doc.page_xref(page - 1))
    return targets


def _reorder(doc: pymupdf.Document, targets: list[int]) -> None:
    order = [doc.page_xref(index) for index in range(doc.page_count)]
    for position, xref in enumerate(targets):
        current = order.index(xref, position)
        if current != position:
            doc.move_page(current, position)
            order.insert(position, order.pop(current))


def _remove_pages(doc: pymupdf.Document, retired: list[int]) -> bool:
    """Borra páginas sin dejar nada que las mantenga vivas en el archivo.

    `delete_pages` solo las saca del árbol de páginas: el objeto y su contenido
    siguen ahí mientras algo los referencie. Devuelve si se quitaron las
    etiquetas de accesibilidad.
    """
    indexes = [page - 1 for page in retired]
    xrefs = {doc.page_xref(index) for index in indexes}
    for index in indexes:
        _delete_widgets(doc[index])
    _prune_destinations(doc, xrefs)
    removed_tags = _remove_structure_tree(doc)
    toc_before = doc.get_toc(simple=False)
    doc.delete_pages(indexes)
    _remove_toc_entries(doc, toc_before, set(retired))
    return removed_tags


def _delete_widgets(page: pymupdf.Page) -> None:
    widget = page.first_widget
    while widget is not None:
        widget = page.delete_widget(widget)


def _prune_destinations(doc: pymupdf.Document, retired: set[int]) -> None:
    catalog = doc.pdf_catalog()
    dests = _indirect_dict(doc, catalog, "Dests")
    if dests is not None:
        _prune_dest_dict(doc, dests, retired)
    tree = _indirect_dict(doc, catalog, "Names/Dests")
    if tree is not None:
        _prune_name_tree(doc, tree, retired, set())


def _prune_dest_dict(doc: pymupdf.Document, xref: int, retired: set[int]) -> None:
    """Reescribe el diccionario: con `null` el nombre seguiría en el archivo."""
    entries = {key: doc.xref_get_key(xref, key)[1] for key in doc.xref_get_keys(xref)}
    kept = [
        f"/{_pdf_name(key)} {value}"
        for key, value in entries.items()
        if not _points_to_retired(doc, value, retired)
    ]
    if len(kept) != len(entries):
        doc.update_object(xref, f"<<{''.join(kept)}>>")


def _pdf_name(key: str) -> str:
    return "".join(
        char if char in _NAME_REGULAR else "".join(f"#{b:02X}" for b in char.encode())
        for char in key
    )


def _indirect_dict(doc: pymupdf.Document, owner: int, key: str) -> int | None:
    """Xref del diccionario en `key`; si va incrustado, lo saca a su propio objeto."""
    kind, value = doc.xref_get_key(owner, key)
    if kind == "xref":
        return int(value.split()[0])
    if kind != "dict":
        return None
    xref = doc.get_new_xref()
    doc.update_object(xref, value)
    doc.xref_set_key(owner, key, f"{xref} 0 R")
    return xref


def _prune_name_tree(
    doc: pymupdf.Document, node: int, retired: set[int], visited: set[int]
) -> None:
    if node in visited:
        return
    visited.add(node)
    kind, kids = doc.xref_get_key(node, "Kids")
    if kind == "array":
        for match in _REFERENCE.finditer(kids):
            _prune_name_tree(doc, int(match[1]), retired, visited)
    kind, names = doc.xref_get_key(node, "Names")
    if kind == "array":
        doc.xref_set_key(
            node,
            "Names",
            _NAME_TREE_PAIR.sub(
                lambda pair: (
                    "" if _points_to_retired(doc, pair[1], retired) else pair[0]
                ),
                names,
            ),
        )


def _points_to_retired(doc: pymupdf.Document, value: str, retired: set[int]) -> bool:
    for _hop in range(_MAX_DESTINATION_HOPS):
        match = _REFERENCE.search(value)
        if match is None:
            return False
        xref = int(match[1])
        if xref in retired:
            return True
        if doc.xref_get_key(xref, "Type") == ("name", "/Page"):
            return False
        value = doc.xref_object(xref, compressed=True)
    return False


def _remove_structure_tree(doc: pymupdf.Document) -> bool:
    catalog = doc.pdf_catalog()
    if doc.xref_get_key(catalog, "StructTreeRoot")[0] == "null":
        return False
    doc.xref_set_key(catalog, "StructTreeRoot", "null")
    doc.xref_set_key(catalog, "MarkInfo", "null")
    return True


def _remove_toc_entries(
    doc: pymupdf.Document, before: list[list], retired: set[int]
) -> None:
    """Rehace el índice sin las entradas de páginas eliminadas.

    `del_toc_item` solo las atenúa: su título seguiría en el archivo. Se compara
    con el índice previo porque un marcador a una web también tiene página -1 y
    ese no se eliminó. Los hijos de una entrada eliminada suben de nivel.
    """
    after = doc.get_toc(simple=False)
    kept = [
        entry
        for entry, previous in zip(after, before, strict=True)
        if previous[2] not in retired
    ]
    if len(kept) == len(after):
        return
    level = 0
    for entry in kept:
        level = min(entry[0], level + 1)
        entry[0] = level
    doc.set_toc(kept)


def _save(doc: pymupdf.Document, path: Path) -> None:
    doc.save(
        str(path),
        garbage=3,
        deflate=True,
        use_objstms=1,
        encryption=pymupdf.PDF_ENCRYPT_KEEP,  # type: ignore[attr-defined]
    )


def _page_objects(doc: pymupdf.Document) -> int:
    return sum(
        doc.xref_get_key(xref, "Type") == ("name", "/Page")
        for xref in range(1, doc.xref_length())
    )


def _has_orphan_pages(path: Path) -> bool:
    with pymupdf.open(str(path)) as doc:
        return _page_objects(doc) != doc.page_count


def _rebuild(source: Path, plan: Plan, target: Path) -> None:
    """Copia a un documento nuevo solo lo que pide el plan, por tramos contiguos.

    Cada `insert_pdf` vuelve a copiar los recursos compartidos: `garbage=4` los
    unifica comparando su contenido. Medido en un plan barajado de 300 páginas
    con una imagen común: 2 MB con 4, 575 MB con 3.
    """
    with pymupdf.open(str(source)) as doc, pymupdf.open() as rebuilt:
        for first, last in _contiguous_runs(plan):
            rebuilt.insert_pdf(doc, from_page=first - 1, to_page=last - 1)
        for index, (_page, rotation) in enumerate(plan):
            if rotation:
                page = rebuilt[index]
                page.set_rotation((page.rotation + rotation) % 360)
        rebuilt.set_metadata(doc.metadata)
        rebuilt.save(str(target), garbage=4, deflate=True, use_objstms=1)


def _contiguous_runs(plan: Plan) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    for page, _rotation in plan:
        if runs and runs[-1][1] + 1 == page:
            runs[-1] = (runs[-1][0], page)
        else:
            runs.append((page, page))
    return runs
