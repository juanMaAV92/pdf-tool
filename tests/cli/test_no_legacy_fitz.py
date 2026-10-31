import json
import subprocess
import sys

# PyMuPDF >= 1.28 imprime en stdout un aviso al hacer `import fitz`, lo que
# rompe el `--json` de la CLI. Bloquear `fitz` obliga a usar `import pymupdf`.
CODE = """
import sys
sys.modules["fitz"] = None
import pymupdf
doc = pymupdf.open()
doc.new_page()
doc.new_page()
doc.save(sys.argv[1])
from pdftool.cli import main
sys.exit(main(["split", sys.argv[1], "--mode", "single", "--json"]))
"""


def test_cli_json_works_without_legacy_fitz_module(tmp_path):
    src = tmp_path / "a.pdf"
    proc = subprocess.run(
        [sys.executable, "-c", CODE, str(src)], capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["ok"] is True
