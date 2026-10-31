import subprocess
import sys

# `pip install pdf-tool` instala también el comando `pdftool` (la app), pero
# sin el extra [gui] no hay Flet: debe explicar cómo instalarlo, sin traceback.
CODE = """
import sys
sys.modules["flet"] = None
from pdftool.main import main
main()
"""


def test_app_without_flet_explains_how_to_install_it():
    proc = subprocess.run([sys.executable, "-c", CODE], capture_output=True, text=True)
    assert proc.returncode == 1
    assert "pdf-tool[gui]" in proc.stderr
    assert "Traceback" not in proc.stderr
