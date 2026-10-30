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
