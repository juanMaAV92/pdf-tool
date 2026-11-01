from __future__ import annotations

from pathlib import Path

import pymupdf

from pdftool.core.atomic import atomic_output
from pdftool.core.batch import noop_progress, run_batch
from pdftool.core.errors import UserError
from pdftool.core.naming import output_path
from pdftool.core.plugin import Progress, ToolResult
from pdftool.i18n import t
from pdftool.tools.protect.params import ProtectParams


def _output(input_path: Path, suffix: str, out_dir: Path | None = None) -> Path:
    """Política de nombre de Proteger; la colisión la resuelve el helper."""
    return output_path(input_path, suffix, out_dir=out_dir)


def _protect_one(
    input_path: Path, params: ProtectParams, progress: Progress
) -> tuple[Path, str]:
    """Procesa un archivo. Devuelve (salida, etiqueta); un error lanza."""
    if params.mode == "protect":
        progress(0.0, t("tool.protect.progress.protecting"))
        out = _output(input_path, t("tool.protect.suffix.protect"), params.output_dir)
        with atomic_output(out) as temporary, pymupdf.open(str(input_path)) as doc:
            if doc.needs_pass:
                raise UserError(t("tool.protect.error.already"))
            doc.save(
                str(temporary),
                encryption=pymupdf.PDF_ENCRYPT_AES_256,  # type: ignore[attr-defined]
                owner_pw=params.password,
                user_pw=params.password,
                garbage=4,
                deflate=True,
            )
        progress(1.0, t("common.progress.done"))
        return out, t("common.item.output", name=out.name)

    # mode == "remove"
    progress(0.0, t("tool.protect.progress.removing"))
    out = _output(input_path, t("tool.protect.suffix.remove"), params.output_dir)
    with atomic_output(out) as temporary, pymupdf.open(str(input_path)) as doc:
        if doc.needs_pass and not doc.authenticate(params.password):
            raise UserError(t("tool.protect.error.wrong_password"))
        # garbage=4 descarta objetos sin referencias: si no, el PDF conserva el
        # diccionario de cifrado viejo con los hashes de la contraseña quitada.
        doc.save(
            str(temporary),
            encryption=pymupdf.PDF_ENCRYPT_NONE,  # type: ignore[attr-defined]
            garbage=4,
            deflate=True,
        )
    progress(1.0, t("common.progress.done"))
    return out, t("common.item.output", name=out.name)


def protect(
    inputs: list[Path], params: ProtectParams, progress: Progress = noop_progress
) -> ToolResult:
    batch = run_batch(
        inputs,
        lambda path, scoped: _protect_one(path, params, scoped),
        progress,
        all_failed=t("tool.protect.all_failed"),
    )
    outputs, total = batch.outputs, batch.total

    if total == 1:
        key = (
            "tool.protect.summary.protected_one"
            if params.mode == "protect"
            else "tool.protect.summary.removed_one"
        )
        return ToolResult(outputs=outputs, summary=t(key, name=outputs[0].name))

    progress(1.0, t("common.progress.done"))
    if len(outputs) == total:
        key = (
            "tool.protect.summary.protected_all"
            if params.mode == "protect"
            else "tool.protect.summary.removed_all"
        )
        summary = t(key, count=total)
    else:
        summary = t("tool.protect.summary.partial", done=len(outputs), count=total)
    return ToolResult(outputs=outputs, summary=summary, items=batch.items)
