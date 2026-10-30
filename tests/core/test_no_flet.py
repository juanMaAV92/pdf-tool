import json
import subprocess
import sys

# Bloquea Flet antes de cualquier import: si el núcleo o una spec lo
# importaran, `import flet` lanzaría ImportError y discover() la omitiría.
CODE = """
import sys
sys.modules["flet"] = None
from pdftool.core import registry
failed = registry.discover()
print(",".join(s.meta.id for s in registry.get_specs()))
print(failed)
"""


def test_tools_are_discovered_without_flet():
    out = subprocess.run(
        [sys.executable, "-c", CODE], capture_output=True, text=True, check=True
    ).stdout.splitlines()
    assert out == ["merge,split,compress,images2pdf,watermark,protect", "[]"]


CLI_CODE = """
import sys
sys.modules["flet"] = None
from pdftool.cli import main
sys.exit(main(["list", "--json"]))
"""


def test_cli_runs_without_flet():
    proc = subprocess.run(
        [sys.executable, "-c", CLI_CODE], capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stderr
    assert len(json.loads(proc.stdout)) == 6
