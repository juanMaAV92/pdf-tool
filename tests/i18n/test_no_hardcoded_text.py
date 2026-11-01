"""Ningún texto visible queda escrito en el código: todo sale de los diccionarios.

Recorre `pdftool/` con `ast` y falla con cualquier literal (también las partes
fijas de los f-strings) con al menos dos palabras separadas por espacios. Se ignoran
docstrings, mensajes del log, la clave de `t()` y una lista corta de
excepciones justificadas.
"""

import ast
import re
from pathlib import Path

import pdftool

ROOT = Path(pdftool.__file__).parent
# Una palabra: solo letras (con puntuación de frase alrededor), no identificadores.
_WORD = re.compile(r"[«(¿¡\"']?[^\W\d_]{2,}[.,:;!?»)…\"']*")
_LOG_METHODS = {"debug", "info", "warning", "error", "exception", "critical"}

# (archivo relativo a pdftool/, fragmento del literal): motivo.
ALLOWED = {
    ("core/batch.py", "inputs está vacío"): "excepción interna (no la ve el usuario)",
    ("tools/merge/logic.py", "inputs está vacío"): "excepción interna",
    ("tools/split/logic.py", "inputs está vacío"): "excepción interna",
    ("tools/watermark/logic.py", "inputs está vacío"): "excepción interna",
    ("core/config.py", "no es un objeto"): "excepción interna de settings.json",
    ("core/updater.py", "demasiado grande"): "excepción interna del actualizador",
    ("core/registry.py", "duplicado"): "error de desarrollo (id repetido)",
    ("ui/registry.py", "duplicado"): "error de desarrollo (id repetido)",
    ("cli/args.py", "no soportado por la CLI"): "error de desarrollo (tipo de campo)",
    ("cli/args.py", "nombre reservado por la CLI"): "error de desarrollo",
}


def _docstring_nodes(tree: ast.AST) -> set[int]:
    ids = set()
    for node in ast.walk(tree):
        if isinstance(
            node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
        ):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr):
                value = body[0].value
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    ids.add(id(value))
    return ids


def _ignored_calls(tree: ast.AST) -> set[int]:
    """Literales dentro de llamadas al log o como clave de `t()`."""
    ids = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_log = isinstance(func, ast.Attribute) and func.attr in _LOG_METHODS
        is_t = isinstance(func, ast.Name) and func.id == "t"
        if is_log:
            for arg in node.args:
                ids.update(id(n) for n in ast.walk(arg))
        if is_t and node.args:
            ids.update(id(n) for n in ast.walk(node.args[0]))
    return ids


def _offenders(root: Path = ROOT, used: set | None = None) -> list[str]:
    found = []
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        skip = _docstring_nodes(tree) | _ignored_calls(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.JoinedStr):
                # Un f-string se evalúa entero (los marcadores cuentan como
                # «{}»), para que una frase partida por variables no se escape.
                parts = [
                    v.value if isinstance(v, ast.Constant) else "{}"
                    for v in node.values
                ]
                skip.update(id(v) for v in node.values)
                if id(node) in skip:
                    continue
                text = "".join(str(x) for x in parts)
            elif (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and id(node) not in skip
            ):
                text = node.value
            else:
                continue
            if sum(bool(_WORD.fullmatch(w)) for w in text.split()) < 2:
                continue
            allowed = [(f, frag) for f, frag in ALLOWED if rel == f and frag in text]
            if allowed:
                if used is not None:
                    used.update(allowed)
                continue
            found.append(f"{rel}:{node.lineno}: {text!r}")
    return found


def test_no_user_text_in_code():
    offenders = _offenders()
    assert not offenders, "\n".join(offenders)


def test_guard_catches_sentences_but_not_keys_logs_or_docstrings(tmp_path):
    (tmp_path / "mod.py").write_text(
        '"""Docstring con varias palabras."""\n'
        "import logging\n"
        "from pdftool.i18n import t\n"
        "log = logging.getLogger('x')\n"
        "def f(name):\n"
        '    log.info("mensaje del log con palabras")\n'
        '    t("ui.some.key")\n'
        '    return f"Hola {name}, bienvenido"\n',
        encoding="utf-8",
    )
    offenders = _offenders(tmp_path)
    assert len(offenders) == 1
    assert "bienvenido" in offenders[0]


def test_every_allowed_exception_is_still_needed():
    used: set = set()
    _offenders(used=used)
    assert set(ALLOWED) == used, sorted(set(ALLOWED) - used)
