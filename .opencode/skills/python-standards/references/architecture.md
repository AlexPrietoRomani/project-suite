# Estructura y Modularidad de Archivos Python

Todo script o módulo `.py` nuevo o modificado debe seguir una organización lógica secuencial de tipo top-down:

## Flujo de Organización Secuencial
1. **Encabezado del Archivo (Docstring de Módulo):** Declaración informativa del ciclo de vida y alcance del archivo (Ver plantilla en `documentation.md`).
2. **Importaciones:** Agrupadas limpiamente y ordenadas, separando cada bloque por una única línea en blanco:
   - Librerías estándar del ecosistema de Python (ej. `import os`, `import json`).
   - Librerías de terceros / Frameworks externos (ej. `import numpy as np`, `import torch`).
   - Módulos y dependencias locales del proyecto (ej. `from core.models import YoloPredictor`).
3. **Variables Globales / Constantes:** Definición de configuraciones fijas del archivo si no se externalizan a un `config.py`.
4. **Clases y Funciones Modulares:** Estructuras limpias que apliquen el principio de Responsabilidad Única (*Single Responsibility Principle*). Si una función asume múltiples responsabilidades (ej. lectura, transformación y persistencia), DEBE ser descompuesta en funciones atómicas independientes.
5. **Bloque de Entrada Principal:** Estructura de control condicional clásica:
```python
   if __name__ == "__main__":
       main()

```

Toda la lógica de ejecución del script principal debe ser encapsulada dentro de la función `main()`.
