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

## 2. Smoke visual de los artefactos

El workflow **Package smoke** construye la app universal y valida el contenido
del DMG en macOS; en Windows compila el instalador y comprueba que instala el
ejecutable. Los tests cubren lógica y estado de paneles con stubs, pero ningún
runner puede validar de forma fiable la ventana Flet, el FilePicker ni los
permisos nativos.

**Disparador:** antes de una release importante o de aceptar una actualización de
Flet. Ejecutar [la checklist manual](release-smoke.md) para cubrir layout,
diálogos nativos, permisos, rutas y arranque de los artefactos empaquetados.

## 3. Pin de Flet 0.28.2

La versión está fijada porque la app funciona y el `FilePicker` de esa serie es
conocido. Migrar a una serie nueva toca todos los paneles, logging, navegación y
el empaquetado; no aporta valor inmediato mientras no haya una necesidad concreta.

**Disparador:** un bug sin workaround, una feature que requiera una API nueva o
una decisión de soporte de la plataforma. Antes de migrar hay que hacer la prueba
visual/empaquetada de la deuda anterior.

## Ya resuelto

No volver a abrir estos temas como deuda: jobs y miniaturas usan executors
compartidos, tienen cancelación y generaciones, y se cierran al salir; las
salidas PDF y los ajustes se escriben atómicamente; los lotes usan `FileResult`
por archivo; CI exige formato/lint con Ruff, tipos del núcleo con mypy y al
menos 85% de cobertura; y la carpeta de salida, colisiones, logging, errores y
actualización ya están integrados.

## No son deuda prioritaria

La caché de miniaturas no se invalida por mtime y puede haber renders duplicados
en carreras poco frecuentes. Son costes acotados, sin corrupción ni impacto
conocido en el uso normal; solo se pagan si aparecen con archivos grandes o una
necesidad explícita.
