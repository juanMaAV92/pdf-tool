from __future__ import annotations

from pathlib import Path

import fitz

from pdftool.core.plugin import Progress, ToolResult
from pdftool.tools.split.params import SplitParams

# Rango 1-indexed e inclusivo. None = extremo abierto (inicio o final del PDF).
Range = tuple[int | None, int | None]


def _noop(_p: float, _m: str) -> None:
    pass


def parse_ranges(spec: str) -> list[Range]:
    """Parsea la sintaxis de rangos sin conocer el total de páginas.

    Acepta (1-indexed, inclusivo), separados por comas:
      ``N``    -> solo la página N            -> (N, N)
      ``N-M``  -> de la N a la M              -> (N, M)
      ``N-``   -> de la N hasta el final      -> (N, None)
      ``-M``   -> del inicio hasta la M       -> (None, M)

    Lanza ``ValueError`` si la sintaxis es inválida o el rango está invertido.
    """
    if not spec or not spec.strip():
        raise ValueError("Indica al menos un rango (ej: 1-3, 5, 8-)")

    out: list[Range] = []
    for raw in spec.split(","):
        token = raw.strip()
        if not token:  # tolera comas sobrantes ("1-3,")
            continue
        out.append(_parse_token(token))
    if not out:
        raise ValueError("Indica al menos un rango (ej: 1-3, 5, 8-)")
    return out


def _parse_int(text: str) -> int:
    if not text.isdigit():
        raise ValueError(f"Valor inválido: {text!r}")
    value = int(text)
    if value < 1:
        raise ValueError("Las páginas empiezan en 1")
    return value


def _parse_token(token: str) -> Range:
    if "-" not in token:
        n = _parse_int(token)
        return (n, n)

    parts = token.split("-")
    if len(parts) != 2:
        raise ValueError(f"Rango inválido: {token!r}")
    left, right = parts[0].strip(), parts[1].strip()

    start = _parse_int(left) if left else None
    end = _parse_int(right) if right else None
    if not left and not right:
        raise ValueError(f"Rango inválido: {token!r}")
    if start is not None and end is not None and start > end:
        raise ValueError(f"Rango invertido: {token!r}")
    return (start, end)


def resolve_ranges(parsed: list[Range], page_count: int) -> list[tuple[int, int]]:
    """Rellena extremos abiertos con el total real y valida límites."""
    resolved: list[tuple[int, int]] = []
    for start, end in parsed:
        s = 1 if start is None else start
        e = page_count if end is None else end
        if s > page_count or e > page_count:
            raise ValueError(
                f"El rango {s}-{e} excede el total de {page_count} páginas"
            )
        resolved.append((s, e))
    return resolved


def _label(start: int, end: int, width: int) -> str:
    if start == end:
        return f"p{start:0{width}d}"
    return f"p{start:0{width}d}-{end:0{width}d}"


def _ranges_for(params: SplitParams, page_count: int) -> list[tuple[int, int]]:
    if params.mode == "single":
        return [(i, i) for i in range(1, page_count + 1)]
    if params.mode == "every":
        return [
            (s, min(s + params.every_n - 1, page_count))
            for s in range(1, page_count + 1, params.every_n)
        ]
    return resolve_ranges(parse_ranges(params.ranges), page_count)


def split(inputs: list[Path], params: SplitParams,
          progress: Progress = _noop) -> ToolResult:
    if not inputs:
        raise ValueError("inputs está vacío")

    src_path = Path(inputs[0])
    if not src_path.exists():
        raise FileNotFoundError(src_path)

    outputs: list[Path] = []
    with fitz.open(str(src_path)) as src:
        page_count = src.page_count
        ranges = _ranges_for(params, page_count)
        width = len(str(page_count))
        total = len(ranges)
        progress(0.0, f"Dividiendo en {total} archivos…")

        for i, (start, end) in enumerate(ranges):
            out = src_path.parent / f"{src_path.stem}_{_label(start, end, width)}.pdf"
            with fitz.open() as dst:
                dst.insert_pdf(src, from_page=start - 1, to_page=end - 1)
                dst.save(str(out), garbage=4, deflate=True)
            outputs.append(out)
            progress((i + 1) / total, f"Generado {out.name}")

    progress(1.0, f"Listo: {total} archivos")
    return ToolResult(outputs=outputs, summary=f"{src_path.name} → {total} archivos")
