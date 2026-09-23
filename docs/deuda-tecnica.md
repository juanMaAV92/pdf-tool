# Deuda técnica pendiente

La app está estable para uso y releases. Este documento conserva únicamente
deuda abierta o una decisión técnica que todavía puede exigir trabajo.

## 1. Separar el hotspot de `panel_base.py`

`panel_base.py` concentra errores, acciones del footer, campos de nombre, paneles
de uno y varios archivos y el wiring de miniaturas. Sigue siendo cohesivo, así
que dividirlo ahora sería refactor especulativo.

**Disparador:** antes de construir una cuadrícula visual de páginas o si supera
aproximadamente 550 líneas. La solución prevista es extraer `MultiFileToolPanel`
o los widgets de fila a módulos propios; la cuadrícula debe nacer fuera de este
archivo.

## 2. Cobertura visual y de empaquetado

Los tests cubren lógica y estado de paneles con stubs. Todavía no se valida una
ventana Flet real ni los instaladores en macOS y Windows.

**Disparador:** antes de una release importante o de aceptar una actualización de
Flet. La validación debe cubrir layout, diálogos nativos, permisos, rutas y
arranque de los artefactos empaquetados.

## 3. Pin de Flet 0.28.2

La versión está fijada porque la app funciona y el `FilePicker` de esa serie es
conocido. Migrar a una serie nueva toca todos los paneles, logging, navegación y
el empaquetado; no aporta valor inmediato mientras no haya una necesidad concreta.

**Disparador:** un bug sin workaround, una feature que requiera una API nueva o
una decisión de soporte de la plataforma. Antes de migrar hay que hacer la prueba
visual/empaquetada de la deuda anterior.

## Ya resuelto

No volver a abrir estos temas como deuda: jobs y miniaturas tienen cancelación y
generaciones; las salidas PDF y los ajustes se escriben atómicamente; los lotes
usan `FileResult` por archivo; Ruff valida formato/lint y mypy comprueba el
núcleo; y la carpeta de salida, colisiones, logging, errores y actualización ya
están integrados.

## No son deuda prioritaria

La caché de miniaturas no se invalida por mtime y puede haber renders duplicados
en carreras poco frecuentes. Son costes acotados, sin corrupción ni impacto
conocido en el uso normal; solo se pagan si aparecen con archivos grandes o una
necesidad explícita.
