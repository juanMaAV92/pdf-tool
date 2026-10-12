# Smoke manual de release

El workflow **Package smoke** comprueba que los artefactos se construyan y que
el DMG/instalador publiquen una app. No puede comprobar de forma fiable diálogos
nativos, permisos ni la ventana Flet. Antes de publicar una release importante o
actualizar Flet, ejecutar esta lista sobre los artefactos del draft release.

## macOS

1. Abrir el DMG, mover `pdf-tool.app` a Aplicaciones y abrirla siguiendo el
   aviso de Gatekeeper si aplica.
2. Confirmar que la versión visible coincide con el tag del draft release, que
   aparece la ventana principal y que **Elegir PDF** abre el selector nativo.
3. En **Comprimir PDF**, confirmar que aparecen el modo de compresión y el
   destino de salida; comprimir un PDF de prueba y abrir tanto el archivo como su
   carpeta desde el resultado.
4. Cerrar la aplicación mientras procesa un PDF grande; no debe dejar una
   ventana bloqueada ni mostrar resultados al volver a abrirla.

## Windows

1. Instalar el `-setup.exe`, abrir pdf-tool desde el menú Inicio y confirmar que
   no hay errores de SmartScreen fuera de los esperados para una app sin firma.
2. Confirmar que la versión visible coincide con el tag del draft release y que
   **Elegir PDF** abre el selector nativo.
3. En **Comprimir PDF**, confirmar que aparecen el modo de compresión y el
   destino de salida; procesar un PDF de prueba.
4. Abrir el resultado y su carpeta desde la interfaz.
5. Cerrar la aplicación durante un PDF grande y abrirla otra vez; no debe
   aparecer progreso ni un resultado anterior.

Registrar sistema operativo, arquitectura y cualquier excepción en las notas de
la release o en el issue asociado.

## Cierre de tarea y soporte

- Tras una operación, el resumen aparece junto a las acciones de apertura:
  con una salida prima **Abrir archivo** y con varias **Abrir carpeta**.
- Reintentar muestra progreso sin el resumen anterior; cambiar entradas retira
  los botones de apertura antiguos.
- En claro y oscuro, la versión sigue visible; **Opciones de la aplicación**
  permite cambiar tema, descargar el log y visitar la página del autor.
- Ante un error técnico, **Ver detalle técnico** y **Descargar log** siguen
  disponibles junto al mensaje, sin tener que buscar el menú general.

## Accesibilidad del paquete nativo

- En Inicio, recorrer las tarjetas con Tab y Shift+Tab: el foco es visible y
  Enter abre la herramienta correspondiente.
- Llegar con teclado a Elegir/Añadir PDF, abrir el selector y cancelarlo con
  Escape; después seleccionar un PDF de prueba y ejecutar la operación.
- En Comprimir y Dividir, llegar a la ayuda con Tab y comprobar que se puede
  leer sin hover; al abandonar el botón, el texto temporal se oculta.
- Con VoiceOver en macOS y el lector de pantalla disponible en Windows, comprobar
  que las tarjetas se anuncian como botones y que tema, ayuda y acciones de cada
  archivo tienen nombres útiles.
- Abrir **Opciones de la aplicación** con teclado, recorrer sus opciones y
  cerrar el menú con Escape sin perder el foco.
