# Roadmap

Estado actual: 6 herramientas (Comprimir, Imágenes a PDF, Unir, Proteger, Dividir,
Marca de agua) sobre un panel base compartido con lote, footer anclado, logging con
descarga y auto-update. Cada feature nueva sigue el flujo del repo: lógica pura +
panel + tests (ver AGENTS.md).

## Pendiente prioritario

### Preparación de releases

- Ejecutar una validación visual y de empaquetado en macOS y Windows. Debe cubrir
  la ventana real, diálogos nativos, permisos, rutas de salida y ejecución de
  los instaladores.
- Mantener Flet 0.28.2 mientras la app sea estable. La migración solo se justifica
  si aparece un bug sin workaround o una feature que requiera una versión nueva.

### Funcionalidad de páginas

1. **PDF → imágenes.** Exportar páginas a PNG/JPG con destino y colisiones
   coherentes con el resto de herramientas.
2. **Rotar páginas.** Rotación por rangos, reutilizando el parser de rangos de
   Dividir.
3. **Extraer y reordenar páginas.** Permitir secuencias como `3, 1, 5` además
   de los rangos que ya soporta Dividir.

## Después

4. **Metadatos.** Consultar y limpiar título, autor y otros campos básicos.
5. **Preferencias.** Persistir el tema aplicado y los últimos parámetros por
   herramienta. La carpeta de salida ya persiste; queda endurecer el manejo del
   archivo de ajustes ante corrupción o escritura interrumpida.

## No planificado por ahora

- **OCR:** requiere una dependencia de sistema pesada; reevaluar ante una
  necesidad concreta.
- **Drag & drop del sistema:** depende de una extensión externa y probablemente
  de migrar Flet; reevaluar junto con esa migración.
