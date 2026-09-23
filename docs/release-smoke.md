# Smoke manual de release

El workflow **Package smoke** comprueba que los artefactos se construyan y que
el DMG/instalador publiquen una app. No puede comprobar de forma fiable diálogos
nativos, permisos ni la ventana Flet. Antes de publicar una release importante o
actualizar Flet, ejecutar esta lista sobre los artefactos del draft release.

## macOS

1. Abrir el DMG, mover `pdf-tool.app` a Aplicaciones y abrirla siguiendo el
   aviso de Gatekeeper si aplica.
2. Confirmar que aparece la ventana principal y que **Elegir PDF** abre el
   selector nativo.
3. Comprimir un PDF de prueba y abrir tanto el archivo como su carpeta desde el
   resultado.
4. Cerrar la aplicación mientras procesa un PDF grande; no debe dejar una
   ventana bloqueada ni mostrar resultados al volver a abrirla.

## Windows

1. Instalar el `-setup.exe`, abrir pdf-tool desde el menú Inicio y confirmar que
   no hay errores de SmartScreen fuera de los esperados para una app sin firma.
2. Confirmar que **Elegir PDF** abre el selector nativo y procesar un PDF de
   prueba.
3. Abrir el resultado y su carpeta desde la interfaz.
4. Cerrar la aplicación durante un PDF grande y abrirla otra vez; no debe
   aparecer progreso ni un resultado anterior.

Registrar sistema operativo, arquitectura y cualquier excepción en las notas de
la release o en el issue asociado.
