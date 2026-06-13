"""Punto de entrada para `flet build` (busca main.py en la raíz del proyecto).

Delega en pdftool.main:main, que es también el script `pdftool` de Poetry.
"""
from pdftool.main import main

main()
