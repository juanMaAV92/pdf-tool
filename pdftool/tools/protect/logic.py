from __future__ import annotations

from pathlib import Path

import fitz

from pdftool.core.atomic import atomic_output
from pdftool.core.batch import noop_progress, run_batch
from pdftool.core.errors import UserError
from pdftool.core.naming import output_path
from pdftool.core.plugin import Progress, ToolResult
from pdftool.tools.protect.params import ProtectParams


def _output(input_path: Path, suffix: str, out_dir: Path | None = None) -> Path:
    """Política de nombre de Proteger; la colisión la resuelve el helper."""
    return output_path(input_path, suffix, out_dir=out_dir)


def _protect_one(
    input_path: Path, params: ProtectParams, progress: Progress
) -> tuple[Path, str]:
    """Procesa un archivo. Devuelve (salida, etiqueta); un error lanza."""
    if params.mode == "protect":
        progress(0.0, "Protegiendo PDF…")
        out = _output(input_path, "protegido", params.output_dir)
        with atomic_output(out) as temporary:
            with fitz.open(str(input_path)) as doc:
                if doc.needs_pass:
                    raise UserError(
                        "El PDF ya está protegido; quítale la contraseña primero."
                    )
                doc.save(
                    str(temporary),
                    encryption=fitz.PDF_ENCRYPT_AES_256,
                    owner_pw=params.password,
                    user_pw=params.password,
                )
        progress(1.0, "Listo")
        return out, f"→ {out.name}"

    # mode == "remove"
    progress(0.0, "Quitando contraseña…")
    out = _output(input_path, "sin_clave", params.output_dir)
    with atomic_output(out) as temporary:
        with fitz.open(str(input_path)) as doc:
            if doc.needs_pass and not doc.authenticate(params.password):
                raise UserError("Contraseña incorrecta.")
            doc.save(str(temporary), encryption=fitz.PDF_ENCRYPT_NONE)
    progress(1.0, "Listo")
    return out, f"→ {out.name}"


def protect(
    inputs: list[Path], params: ProtectParams, progress: Progress = noop_progress
) -> ToolResult:
    batch = run_batch(
        inputs,
        lambda path, scoped: _protect_one(path, params, scoped),
        progress,
        all_failed="Ningún PDF pudo procesarse.",
    )
    outputs, total = batch.outputs, batch.total

    if total == 1:
        verb = "PDF protegido" if params.mode == "protect" else "Contraseña removida"
        return ToolResult(outputs=outputs, summary=f"{verb} → {outputs[0].name}")

    progress(1.0, "Listo")
    if len(outputs) == total:
        summary = (
            f"{total} PDFs protegidos"
            if params.mode == "protect"
            else f"{total} contraseñas removidas"
        )
    else:
        summary = f"{len(outputs)} de {total} PDFs procesados"
    return ToolResult(outputs=outputs, summary=summary, items=batch.items)
