# Estándares de Documentación y Tipado

## 1. Type Hinting Obligatorio
Toda función o método implementado debe declarar de manera estricta el tipo de dato de sus parámetros de entrada, así como el tipo de su valor de retorno mediante las facilidades nativas de Python o el módulo incorporado `typing`.

## 2. Docstrings de Funciones y Clases (Google Style en Español)
Ubicado inmediatamente debajo de la definición de cada función, método o clase.

```python
def extract_spatial_metadata(image_path: str, confidence: float = 0.8) -> dict:
    """
    Extrae la latitud, longitud y precisión de los metadatos EXIF de una imagen.

    Args:
        image_path (str): Ruta absoluta o relativa al archivo de imagen.
        confidence (float, opcional): Umbral mínimo de confianza. Por defecto es 0.8.

    Returns:
        dict: Diccionario que contiene las claves 'latitude', 'longitude' y 'accuracy'.
        Retorna un diccionario vacío si no se encuentran metadatos espaciales.

    Raises:
        FileNotFoundError: Si el archivo especificado en `image_path` no existe.
    """

```

## 3. Docstrings de Módulo (Encabezado de Archivo Obligatorio)

Todo archivo debe iniciar con este bloque descriptivo. Debes seleccionar e integrar únicamente la **Opción Condicional** (A, B o C) que coincida exactamente con la naturaleza del archivo.

```python
"""
Archivo: <nombre_del_archivo.py>
Fecha de modificación: <Fecha DD/MM/YYYY en formato>
Autor: <Nombre Autor/Equipo del>

Descripción:
<Descripción activo de detallada en global la lógica presente>

Sustentación Científica: [Opcional]
<Justificación APA. Formato algorítmica/papers.>

Acciones Principales:
    - <Acción 1 clave ejecutada el módulo por>

Estructura Interna:
    - `<NombreClase/Funcion>`: <Breve o responsabilidad rol>

Entradas / Dependencias:
    - <Archivos, de entorno o recursos requeridas variables>

Salidas / Efectos:
    - <Archivos, base datos de estados genera modifica o que>

# --- OPCIÓN CONDICIONAL A: Si es un EJECUTABLE (CLI / Scripts con main) ---
Ejecución:
    python <nombre_del_archivo.py> [--argumentos]

Ejemplo de Uso:
    python <nombre_del_archivo.py> --input data/raw --weights best.pt

Argumentos:
    - <argumento_1>: <Tipo> - <Descripción detallada>.

# --- OPCIÓN CONDICIONAL B: Si es un MÓDULO DE UTILIDAD (Utils / Librerías internas) ---
Ejemplo de Integración:
    from <directorio>.<nombre_del_archivo> import <funcion_principal>
    resultado = <funcion_principal>(datos)

# --- OPCIÓN CONDICIONAL C: Si es un COMPONENTE DE UI (Streamlit, Dash, FastAPI, etc.) ---
Integración UI:
    - Este archivo renderiza la vista de <Nombre_Componente>.
    - Es invocado por <orquestador.py> mediante <funcion_de_renderizado>().
"""

```
