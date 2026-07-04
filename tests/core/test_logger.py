import logging
import sys
from pathlib import Path

import pytest

import pdftool.core.logger as logger_mod
from pdftool.core.logger import (_SanitizingFormatter, log_paths, sanitize,
                                 setup_logging)


@pytest.fixture(autouse=True)
def _isolated_logging(tmp_path, monkeypatch):
    # Log dir aislado por test y logger "pdftool" limpio antes y después.
    monkeypatch.setattr(logger_mod, "data_dir", lambda: tmp_path)
    lg = logging.getLogger("pdftool")
    for h in list(lg.handlers):
        lg.removeHandler(h)
        h.close()
    yield
    for h in list(lg.handlers):
        lg.removeHandler(h)
        h.close()
    lg.propagate = True  # restaura para que caplog funcione en otros tests


def test_sanitize_redacts_macos_user_paths():
    out = sanitize("FileNotFoundError: /Users/maria/Docs/factura.pdf")
    assert out == "FileNotFoundError: ~/Docs/factura.pdf"


def test_sanitize_redacts_windows_user_paths():
    out = sanitize(r"no se pudo abrir C:\Users\maria\Desktop\f.pdf")
    assert "maria" not in out
    assert out.endswith(r"~\Desktop\f.pdf")


def test_sanitize_redacts_real_home():
    home = str(Path.home())
    assert home not in sanitize(f"error en {home}/x.pdf")


def test_formatter_sanitizes_traceback():
    fmt = _SanitizingFormatter("%(message)s")
    try:
        raise FileNotFoundError("/Users/maria/factura.pdf")
    except FileNotFoundError:
        record = logging.LogRecord("pdftool", logging.ERROR, __file__, 1,
                                   "error", (), sys.exc_info())
    out = fmt.format(record)
    assert "Traceback" in out
    assert "/Users/maria" not in out
    assert "~/factura.pdf" in out


def test_setup_logging_idempotent_and_writes_file():
    setup_logging()
    setup_logging()
    lg = logging.getLogger("pdftool")
    assert len(lg.handlers) == 1
    lg.info("hola")
    files = log_paths()
    assert len(files) == 1
    assert "hola" in files[0].read_text(encoding="utf-8")


def test_log_paths_orders_backup_first(tmp_path):
    d = logger_mod.log_dir()
    (d / "pdf-tool.log").write_text("actual", encoding="utf-8")
    (d / "pdf-tool.log.1").write_text("backup", encoding="utf-8")
    paths = log_paths()
    assert [p.name for p in paths] == ["pdf-tool.log.1", "pdf-tool.log"]
