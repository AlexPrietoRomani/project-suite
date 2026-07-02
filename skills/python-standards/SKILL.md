---
name: python-standards
description: Reglas exhaustivas de arquitectura, nomenclatura y documentación para Python. CARGA ESTA HABILIDAD SIEMPRE que vayas a crear, editar o analizar archivos .py.
when_to_use: Al generar código Python, refactorizar archivos .py, realizar revisiones de código de scripts de Python, o estructurar módulos y docstrings de Python.
allowed-tools: Read Grep
---

# Estándares de Arquitectura y Código Python

Como agente de IA, DEBES cumplir estrictamente las siguientes normativas de calidad de software (basadas en PEP 8, PEP 257 y Google Style) al trabajar con archivos Python (`.py`).

## 1. Reglas Generales e Idioma Mixto
- **Código en Inglés:** Identificadores (variables, funciones, clases, métodos, argumentos, constantes) DEBEN estar estrictamente en inglés. No uses abreviaturas crípticas (ej. usa `filtered_df`, NO `dff`).
- **Documentación en Español:** Todos los comentarios internos (`#`) y cadenas de documentación (`""" """`) DEBEN redactarse en español.
- **Tiempos Verbales:** Documenta siempre utilizando el **presente activo** (ej. "Esta función calcula...", NO "Se calculó...").

## 2. Nomenclatura Estricta (PEP 8)
- **Variables y Funciones:** `snake_case` (ej. `image_processor`, `calculate_metrics()`).
- **Clases:** `PascalCase` (ej. `DatabaseAuditor`, `VisionTransformer`).
- **Constantes y Globales:** `UPPER_SNAKE_CASE` (ej. `MAX_RETRIES`, `DEFAULT_THRESHOLD`). Evita números mágicos harcodeados.
- **Miembros Privados:** Prefijo con un guion bajo `_snake_case` para variables/métodos internos de clase o módulo.

## 3. Comentarios Internos (`#`)
- **El Porqué, no el Qué:** El código limpio se explica a sí mismo. Usa comentarios inline exclusivamente para detallar decisiones técnicas complejas, fundamentos matemáticos o parches temporales (*workarounds*).
- **Alineación:** Inserta un mínimo de dos espacios en blanco antes de un comentario inline en la misma línea de código.
- **Mala práctica:** `x = x + 1  # Incrementa x en 1` (Explica el qué).
- **Buena práctica:** `time.sleep(2)  # Pausa necesaria para evitar rate-limits de la API de AWS` (Explica el porqué).

## 4. Recursos Detallados y Plantillas Obligatorias
Para asegurar el cumplimiento estructural y de documentación, debes consultar dinámicamente según sea necesario:
- Para la organización top-down del archivo y modularidad: Ver [references/architecture.md](references/architecture.md)
- Para plantillas exactas de Docstrings de funciones/módulos y type hinting: Ver [references/documentation.md](references/documentation.md)