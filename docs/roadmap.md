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

## Prioridad 0 — cerrar la base

Antes de crecer en features, pagar las deudas que afectan confianza y releases:

1. **Resultados por archivo tipados.** Sustituir el mapeo implícito por texto por
   `FileResult(input_path, output_path, ok, message)`.
2. **Ajustes resistentes.** Fallback ante JSON inválido y escritura atómica de
   `settings.json`.
3. **Validación de release.** Smoke visual y empaquetado real en macOS y Windows,
   incluyendo FilePicker, permisos, rutas y artefactos instalables.
4. **Panel base.** Extraer la fila/lista de archivos antes de construir una
   cuadrícula de páginas.

## Prioridad 1 — flujo de páginas y compresión confiable

### 1. Espacio visual de páginas

Una sola experiencia para seleccionar, previsualizar, reordenar, rotar, eliminar
y extraer páginas, incluso entre varios PDFs. Debe cubrir el caso `3, 1, 5` y
reutilizar el motor de miniaturas existente.

**Impacto:** muy alto. **Complejidad:** alta. Es la base visual más importante.

### 2. Compresión explicable

Mantener la compresión máxima como default, pero mostrar un resultado entendible:

- tamaño inicial/final y porcentaje ahorrado;
- si se rasterizó alguna página;
- si texto, enlaces o selección pueden haberse perdido;
- opción de conservar contenido seleccionable;
- advertencia breve y tooltip, sin pasos ni clics extra.

**Impacto:** alto. **Complejidad:** media. Es un diferenciador concreto para una
función que el usuario normalmente prueba a ciegas.

### 3. Perfiles simples para lotes

Permitir guardar y reutilizar perfiles como “máxima compresión”, “para enviar por
correo”, “archivo legible” o “proteger y guardar en…”. Cada ejecución debe ofrecer
un resumen por archivo y conservar el comportamiento no destructivo.

**Impacto:** alto. **Complejidad:** media. PDF24 ya tiene perfiles, pero aquí el
valor sería hacerlos comprensibles y seguros para usuarios no técnicos.

## Prioridad 2 — confianza y privacidad

### 4. Limpiar PDF antes de compartir

Eliminar metadatos, comentarios, adjuntos, capas ocultas y otros datos no visibles,
con un reporte claro de lo eliminado. No debe confundirse con dibujar un rectángulo
negro: cualquier redacción futura debe eliminar realmente el contenido subyacente.

**Impacto:** alto. **Complejidad:** alta. Requiere fixtures adversariales y
verificación de que el texto oculto no puede recuperarse.

### 5. OCR local opcional

Agregar OCR como dependencia opcional, no obligatoria: convertir escaneos en PDFs
buscables sin enviar documentos a un servidor. Debe incluir una estimación de
tiempo/tamaño y dejar claro que el resultado es una nueva capa de texto.

**Impacto:** alto. **Complejidad:** alta. No entra antes de estabilizar el flujo
visual y el empaquetado multiplataforma.

### 6. Diagnóstico de privacidad

Un modo visible “solo local” que explique qué operaciones hacen red —por ejemplo,
actualizaciones— y cuál es el destino de los archivos. El procesamiento PDF debe
seguir siendo local por defecto.

**Impacto:** medio-alto. **Complejidad:** media. Convierte una promesa de README
en una propiedad comprobable del producto.

## Prioridad 3 — automatización sin convertirlo en una suite empresarial

7. **CLI y perfiles exportables.** Ejecutar un perfil sobre una carpeta desde
   terminal y producir un reporte JSON/CSV.
8. **Comparar PDFs.** Mostrar páginas añadidas, eliminadas o cambiadas; útil para
   contratos y versiones, pero posterior a la edición de páginas.
9. **Accesibilidad básica.** Detectar ausencia de texto, título, idioma y señales
   comunes de un PDF difícil de leer con tecnologías asistivas.

## Fuera de foco por ahora

- Editor completo de texto/imágenes, formularios colaborativos y firma avanzada:
  Adobe, PDFgear y Sejda ya compiten ahí.
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
