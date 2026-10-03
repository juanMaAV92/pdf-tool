# Roadmap

## Tesis de producto

PDF Tool no debe competir por tener la mayor cantidad de botones. Debe ser la
herramienta local más predecible para trabajar con lotes de PDFs:

- **Local-first:** los PDFs se procesan en el equipo, sin cuenta ni subida de
  documentos para las operaciones normales.
- **Batch-first:** procesar muchos archivos debe ser tan claro como procesar uno.
- **Safe-by-default:** nunca pisar originales, publicar salidas completas y
  mostrar qué ocurrió con cada archivo.
- **Explicable:** especialmente al comprimir, informar el intercambio entre
  tamaño, calidad y funciones conservadas.

La diferenciación no es una feature aislada: es la combinación de privacidad,
seguridad de salida y una UX pequeña para personas no técnicas.

## Qué muestra el mercado

| Referente | Fortaleza | Oportunidad para PDF Tool |
|---|---|---|
| [PDF24 Creator](https://tools.pdf24.org/en/creator) | Suite offline muy amplia, perfiles, OCR, lotes y arrastrar/soltar; solo desktop en Windows. | Ser más pequeño, multiplataforma y directo. |
| [PDFsam Basic](https://pdfsam.org/) | Open source, multiplataforma, sin límites y muy fuerte en dividir, unir, extraer, rotar y mezclar. | Añadir mejor comprensión del resultado, compresión y flujos para usuarios comunes. |
| [Sejda Desktop](https://www.sejda.com/en/desktop) | Editor, páginas, OCR, firmas y conversión en Windows, macOS y Linux. La versión gratis tiene límites diarios y de tamaño. | Ser siempre local, sin límites artificiales y con menos superficie. |
| [PDFgear](https://www.pdfgear.com/pdfgear-for-windows/) | Editor gratuito con OCR, edición de texto y asistente AI; procesa localmente según su documentación. | No competir en AI; competir en transparencia, determinismo y privacidad verificable. |
| [Stirling PDF](https://docs.stirlingpdf.com/) | 55+ herramientas, self-hosting, API, pipelines, carpetas vigiladas y funciones enterprise. | Ofrecer una experiencia de escritorio sencilla, sin servidor ni configuración. |
| [Adobe Acrobat](https://helpx.adobe.com/acrobat/using/explore-acrobat-tools.html) | Referencia en edición, OCR, formularios, firma, colaboración y seguridad avanzada. | No intentar ser un editor completo; resolver mejor las operaciones cotidianas y locales. |

## Prioridad 0 — control de release

No es una feature ni deuda abierta: antes de una release importante o una
actualización de Flet, ejecutar la checklist manual de macOS y Windows. El CI ya
valida los paquetes; esta prueba cubre la ventana real, el FilePicker, permisos y
rutas nativas.

## Prioridad 1 — organizar y entregar el PDF con confianza

### 1. Organizador visual de páginas (MVP)

Una experiencia para un PDF: ver miniaturas, seleccionar, reordenar, rotar,
eliminar y extraer páginas. Debe cubrir una selección como `3, 1, 5` sin pedir al
usuario que escriba rangos, y reutilizar el motor de miniaturas existente.

La primera versión no mueve páginas entre varios PDFs ni intenta ser un editor de
contenido. Esa extensión solo entra después de que el flujo de un documento sea
sólido, predecible y reversible antes de guardar.

**Impacto:** muy alto. **Complejidad:** media-alta. Es la carencia funcional más
clara de la app y el siguiente trabajo de producto.

### 2. Resultado de compresión entendible

La compresión máxima ya es el modo predeterminado; mantenerlo así. Completar el
resultado de cada archivo con tamaño inicial/final, porcentaje ahorrado y, cuando
ocurra, una explicación breve de que alguna página se rasterizó y puede haber
perdido texto seleccionable, enlaces o anotaciones. El modo alternativo para
conservar contenido seleccionable y su tooltip siguen disponibles.

La información aparece en el resultado, no como un paso, diálogo ni clic adicional.

**Impacto:** alto. **Complejidad:** media. Vuelve verificable una operación que los
usuarios normalmente ejecutan a ciegas.

## Prioridad 2 — preparar documentos para compartir

### 3. Recortar márgenes y ajustar tamaño de página

Recortar bordes blancos, definir el área visible y ajustar el tamaño de página. Es
especialmente útil para escaneos, formularios e impresión, y encaja con naturalidad
en el organizador visual. La edición debe previsualizarse antes de producir un PDF
nuevo; los originales nunca se modifican.

**Impacto:** alto. **Complejidad:** media.

### 4. Inspeccionar y limpiar antes de compartir

Mostrar antes de actuar los datos relevantes: páginas, tamaño, cifrado, metadatos,
adjuntos y otras señales que afecten al envío. Ofrecer una limpieza conservadora de
metadatos, comentarios, adjuntos, JavaScript y enlaces externos, con un reporte de
lo eliminado.

No se debe llamar a esto redacción: una redacción real exige eliminar el contenido
subyacente y pruebas de seguridad específicas. Es una iniciativa separada y no
entra todavía.

**Impacto:** alto. **Complejidad:** media-alta. Hace tangible la promesa de
privacidad local sin sumar una pantalla de “diagnóstico” aislada.

## Prioridad 3 — repetir flujos ya maduros

### 5. Perfiles simples para lotes

Cuando las operaciones anteriores estén estabilizadas, permitir guardar y reutilizar
perfiles como “máxima compresión”, “para enviar por correo” o “archivo legible”.
Cada ejecución conserva las salidas no destructivas y presenta un resumen por
archivo.

**Impacto:** medio-alto. **Complejidad:** media. Es valioso para uso repetido, no
para descubrir la app por primera vez.

### 6. Automatización y verificación avanzada

Solo si existe demanda concreta: CLI con perfiles exportables y reporte JSON/CSV,
comparación de PDFs o comprobaciones básicas de accesibilidad. No deben desplazar
los flujos visuales y locales de uso diario.

## Fuera de foco por ahora

- Editor completo de texto/imágenes, formularios colaborativos y firma avanzada:
  Adobe, PDFgear y Sejda ya compiten ahí.
- OCR local: requiere binarios adicionales, aumenta el tamaño y el coste de
  empaquetado y no responde a una necesidad demostrada del público actual. Solo se
  reconsidera con evidencia de demanda y un plan de soporte multiplataforma.
- AI/chat con documentos: PDFgear, Acrobat y Stirling ya cubren esa dirección;
  además elevaría el coste de privacidad y soporte.
- Drag & drop como feature aislada: solo entra junto con una decisión de migrar
  Flet y una validación del empaquetado.

## Criterio para aceptar una feature

Una feature entra si mejora al menos uno de estos resultados sin romper los otros:

1. el usuario sabe qué pasará antes de ejecutar;
2. el original queda intacto y la salida es verificable;
3. un lote falla por archivo, no como una caja negra completa;
4. el documento no necesita salir del equipo;
5. la interfaz sigue siendo entendible para alguien que no conoce “rasterizar”,
   OCR o perfiles técnicos.

## Fuentes consultadas

- [PDF24 Creator](https://tools.pdf24.org/en/creator)
- [Sejda Desktop](https://www.sejda.com/en/desktop)
- [PDFgear para Windows](https://www.pdfgear.com/pdfgear-for-windows/)
- [Stirling PDF — Getting Started](https://docs.stirlingpdf.com/)
- [PDFsam Basic](https://pdfsam.org/)
- [Adobe Acrobat — herramientas](https://helpx.adobe.com/acrobat/using/explore-acrobat-tools.html)
- [Adobe Acrobat — redacción y sanitización](https://experienceleague.adobe.com/en/docs/document-cloud-learn/acrobat-learning/advanced-tasks/protect/redact)
