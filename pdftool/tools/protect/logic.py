from __future__ import annotations

from pathlib import Path

import fitz

from pdftool.core.plugin import Progress, ToolResult
from pdftool.tools.protect.params import ProtectParams


def _noop(_p: float, _m: str) -> None:
    pass


def _output(input_path: Path, suffix: str) -> Path:
    p = Path(input_path)
    return p.parent / f"{p.stem}_{suffix}.pdf"


def _protect_one(input_path: Path, params: ProtectParams,
                 progress: Progress) -> tuple[Path | None, str]:
    """Procesa un archivo. Devuelve (salida, etiqueta) o (None, error corto)."""
    try:
        if params.mode == "protect":
            progress(0.0, "Protegiendo PDF…")
            out = _output(input_path, "protegido")
            with fitz.open(str(input_path)) as doc:
                if doc.needs_pass:
                    raise ValueError(
                        "El PDF ya está protegido; quítale la contraseña primero.")
                doc.save(str(out), encryption=fitz.PDF_ENCRYPT_AES_256,
                         owner_pw=params.password, user_pw=params.password)
            progress(1.0, "Listo")
            return out, f"→ {out.name}"

        # mode == "remove"
        progress(0.0, "Quitando contraseña…")
        out = _output(input_path, "sin_clave")
        with fitz.open(str(input_path)) as doc:
            if doc.needs_pass and not doc.authenticate(params.password):
                raise ValueError("Contraseña incorrecta.")
            doc.save(str(out), encryption=fitz.PDF_ENCRYPT_NONE)
        progress(1.0, "Listo")
        return out, f"→ {out.name}"
    except Exception as exc:  # este archivo falla; el lote continúa
        return None, str(exc)


def protect(inputs: list[Path], params: ProtectParams,
            progress: Progress = _noop) -> ToolResult:
    if not inputs:
        raise ValueError("inputs está vacío")
    paths = [Path(p) for p in inputs]
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(path)

    total = len(paths)
    outputs: list[Path] = []
    labels: list[str] = []

    for index, path in enumerate(paths):
        def scoped(pct: float, msg: str, _i: int = index,
                   _name: str = path.name) -> None:
            overall = (_i + pct) / total
            label = f"[{_i + 1}/{total}] {_name}: {msg}" if total > 1 else msg
            progress(overall, label)

        out, label = _protect_one(path, params, scoped)
        if out is not None:
            outputs.append(out)
        labels.append(label)

    if not outputs:
        raise ValueError(labels[0] if total == 1
                         else "Ningún PDF pudo procesarse.")

    if total == 1:
        verb = ("PDF protegido" if params.mode == "protect"
                else "Contraseña removida")
        return ToolResult(outputs=outputs,
                          summary=f"{verb} → {outputs[0].name}")

    progress(1.0, "Listo")
    if len(outputs) == total:
        summary = (f"{total} PDFs protegidos" if params.mode == "protect"
                   else f"{total} contraseñas removidas")
    else:
        summary = f"{len(outputs)} de {total} PDFs procesados"
    return ToolResult(outputs=outputs, summary=summary, details=labels)
