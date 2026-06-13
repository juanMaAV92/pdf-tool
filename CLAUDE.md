# CLAUDE.md

Esta es la guía del proyecto para Claude Code.

**La fuente de verdad es [AGENTS.md](./AGENTS.md)** — léela primero: cubre la arquitectura, los comandos, cómo agregar una herramienta, las convenciones y el empaquetado.

## Recordatorios clave (resumen)

- **Comandos:** `poetry install` · `poetry run pdftool` · `poetry run pytest`. Nunca actives venvs a mano; usa `poetry run`.
- **Arquitectura:** `core/` sin Flet; cada herramienta separa `logic.py` (puro, testeable) de `panel.py` (UI). `inputs` siempre `list[Path]`; salida junto al original.
- **TDD:** test que falla → implementación, sobre la lógica pura.
- **Flet 0.24.1:** `ft.icons.*` / `ft.colors.*` en minúsculas.
- **Commits:** mensajes planos, Conventional Commits. **Nunca** añadir `Co-Authored-By: Claude` ni "Generated with Claude Code" ni ninguna atribución de IA.
- **Agregar herramienta:** `params.py` + `logic.py` + `panel.py` con `@register` + import en `__init__.py`. El host no se toca.
