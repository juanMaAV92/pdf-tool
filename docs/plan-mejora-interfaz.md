# Plan de mejora de interfaz

Este plan convierte los hallazgos de la auditoría visual en cambios pequeños y
verificables. No añade herramientas PDF nuevas: primero refuerza los flujos ya
existentes para que el futuro organizador visual herede una base clara y accesible.

Referencia: auditoría visual Impeccable realizada sobre la interfaz de PDF Tool.

## Estado de ejecución

- Fases 0 y 1: implementadas; validación del paquete real pendiente de release.
- Fase 2: tarjetas de Inicio convertidas en botones estándar con foco visible;
  iconos con etiquetas específicas; ayuda de compresión y rangos disponible al
  foco y al activar el botón. Verificados roles en el árbol de accesibilidad web,
  Tab/Shift+Tab y apertura de una herramienta con Enter. Pendiente: recorrido
  completo en los paquetes nativos, diálogos de archivo con Escape y lectura con
  VoiceOver en macOS y lector de pantalla en Windows.
- Fases 3 y 4: pendientes.

## Fase 0 — Línea base del artefacto

**Objetivo:** saber qué versión se está revisando y evitar confundir una
instalación anterior con la interfaz de `main`.

### Alcance

- Mostrar versión de la app y, si está disponible, el identificador de build en
  un lugar secundario como Acerca de o Ajustes.
- Confirmar que el paquete de prueba incluye el selector de modo de compresión y
  el destino de salida presentes en el código.
- Mantener la checklist manual de release como control previo a publicar.

### Criterio de salida

Una persona puede identificar la versión instalada y el paquete empaquetado
coincide visualmente con el código que se pretende publicar.

## Fase 1 — Estados vacíos y acción principal

**Objetivo:** que el primer paso y la acción principal se entiendan sin recorrer
la pantalla ni adivinar por qué un botón está desactivado.

### Alcance

- Compactar los paneles cuando todavía no hay archivos, en vez de reservar un
  cuerpo vacío alto.
- Mostrar junto a la acción una guía breve como “Añade al menos un PDF para
  continuar” cuando no se puede ejecutar.
- Mantener la acción Ejecutar visible cerca de los controles en estados vacíos;
  conservar el footer fijo cuando una lista, el progreso o los resultados sí lo
  justifiquen.
- Aclarar que el tamaño de compresión es un objetivo, no una garantía de resultado.

### No incluye

- Cambiar la lógica de compresión o sumar pasos, diálogos o confirmaciones.
- Rediseñar cada herramienta por separado.

### Criterio de salida

Con cada herramienta abierta y sin archivo, el siguiente paso es reconocible en
menos de cinco segundos y el motivo de cualquier control desactivado es visible.

## Fase 2 — Accesibilidad y controles semánticos

**Objetivo:** que la ruta principal funcione con teclado y lector de pantalla antes
de añadir interacciones complejas al organizador visual.

### Alcance

- Convertir las tarjetas clicables de Inicio en controles semánticos, con foco
  visible y activación mediante teclado.
- Dar nombre accesible a los botones de icono: cambiar tema, ayuda, abrir, quitar,
  subir y bajar.
- Exponer la ayuda esencial de rangos y compresión al foco, no solo al hover.
- Probar el recorrido Inicio → herramienta → selector de archivo → acción con Tab,
  Shift+Tab, Enter y Escape cuando corresponda.

### Criterio de salida

Una persona puede abrir una herramienta y comprender cada acción primaria usando
solo teclado; VoiceOver anuncia controles con nombres útiles y el foco siempre es
visible.

## Fase 3 — Jerarquía del cierre de tarea

**Objetivo:** que, tras procesar un archivo, el resultado y las acciones útiles
predominen sobre controles secundarios de la aplicación.

### Alcance

- Priorizar resumen, progreso, “Abrir archivo” y “Abrir carpeta” en el cierre del
  panel.
- Llevar crédito del autor, descarga de logs y cambio de tema a un área secundaria
  que no compita con el resultado.
- Mantener el acceso al log para recuperación de errores, sin ocultar la ruta de
  soporte cuando sea necesaria.

### Criterio de salida

Al terminar una operación, la pantalla comunica claramente qué ocurrió y cuál es
la siguiente acción útil sin distracciones en el footer.

## Fase 4 — Validación y cierre

**Objetivo:** entregar los cambios sin degradar los empaquetados ni la experiencia
en ambos temas.

### Alcance

- Añadir o ajustar pruebas de UI para los estados vacíos y etiquetas relevantes.
- Ejecutar el conjunto de tests, formato, lint y tipos existentes.
- Revisar claro y oscuro en macOS; antes de una release, completar también la
  checklist empaquetada de macOS y Windows.
- Repetir la auditoría visual para comprobar la mejora y registrar la nueva
  puntuación.

### Criterio de salida

No hay regresiones en CI, las pruebas manuales relevantes pasan y la auditoría
posterior confirma que los hallazgos P1 están resueltos.

## Orden de ejecución

1. Fases 0 y 1 en el mismo paquete: corrigen la fricción más visible y aclaran el
   estado real del artefacto que se prueba.
2. Fase 2 antes del organizador visual: evita tener que rehacer después selección,
   acciones por página y foco.
3. Fase 3 como pulido transversal una vez estabilizada la interacción principal.
4. Fase 4 al cerrar cada PR relevante, no solo al final de todo el plan.

## Límites de alcance

- No introducir OCR, edición de texto, redacción o nuevas herramientas durante
  este plan.
- No añadir clics extra a la compresión máxima.
- Los cambios deben preservar el comportamiento local, no destructivo y por lote.
