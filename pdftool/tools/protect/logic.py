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


def protect(inputs: list[Path], params: ProtectParams,
            progress: Progress = _noop) -> ToolResult:
    if not inputs:
        raise ValueError("inputs está vacío")
    input_path = Path(inputs[0])
    if not input_path.exists():
        raise FileNotFoundError(input_path)

    if params.mode == "protect":
        progress(0.0, "Protegiendo PDF…")
        out = _output(input_path, "protegido")
        with fitz.open(str(input_path)) as doc:
            if doc.needs_pass:
                raise ValueError("El PDF ya está protegido; quítale la contraseña primero.")
            doc.save(str(out), encryption=fitz.PDF_ENCRYPT_AES_256,
                     owner_pw=params.password, user_pw=params.password)
        progress(1.0, "Listo")
        return ToolResult(outputs=[out], summary=f"PDF protegido → {out.name}")

    # mode == "remove"
    progress(0.0, "Quitando contraseña…")
    out = _output(input_path, "sin_clave")
    with fitz.open(str(input_path)) as doc:
        if doc.needs_pass and not doc.authenticate(params.password):
            raise ValueError("Contraseña incorrecta.")
        doc.save(str(out), encryption=fitz.PDF_ENCRYPT_NONE)
    progress(1.0, "Listo")
    return ToolResult(outputs=[out], summary=f"Contraseña removida → {out.name}")
