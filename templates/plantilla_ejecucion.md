# Guía de Ejecución — [Nombre del Proyecto]

> **Proyecto:** `[Nombre]` · **Fecha:** [YYYY-MM-DD]
>
> **Cómo usar esta plantilla:** responde las preguntas de la primera sección, luego completa solo las partes que aplican a tu tipo de proyecto. Borra los bloques que no uses antes de publicar.

---

## Identifica tu tipo de proyecto (elige uno)

> *Esto determina qué secciones completar. Marca con `[X]` la que aplica.*

| Tipo | Señal de que aplica | Secciones obligatorias |
|---|---|---|
| [ ] **App Shiny for Python** | `app.py` + `shiny run` | §1, §2, §3A, §5A |
| [ ] **App Streamlit** | `app.py` + `streamlit run` | §1, §2, §3B, §5B |
| [ ] **App back + front** | API separada (FastAPI/Flask) + UI (React/Vue/SPA) | §1, §2, §3C, §5 |
| [ ] **Solo frontend** | Proyecto Node/static sin backend propio | §1, §3D, §5 |
| [ ] **Repo de investigación** | Scripts Python, notebooks, sin app UI | §1, §2, §3E |
| [ ] **Pipeline / ETL secuencial** | Scripts en orden definido (plan de ejecución) | §1, §2, §3F |

---

## 1. Requisitos previos

### 1.1 Software

| Software | Versión mínima | Verificar con |
|---|---|---|
| Python | [3.11+] | `python --version` |
| [conda \| uv \| node] | [versión] | `[comando] --version` |
| Git | 2.30+ | `git --version` |

### 1.2 Credenciales y accesos

- `[Nombre del servicio]`: [dónde obtener la key, qué archivo usa — ej: `.env`, variables de entorno del SO]
- `[Otro acceso]`: [descripción breve]

---

## 2. Entorno virtual

> *Completa solo el bloque del gestor que usa el proyecto. Borra el otro.*

### 2A. Conda (anaconda / miniconda)

```bash
# Primera vez — crear entorno
conda create -n [nombre_entorno] python=[versión] -y

# Instalar dependencias
conda activate [nombre_entorno]
pip install -r requirements.txt
# o: conda install --file requirements.txt

# Activar en cada sesión nueva (Windows PowerShell)
conda activate [nombre_entorno]

# Patrón para invocar scripts sin activar previamente (automatización)
conda run -n [nombre_entorno] python scripts/mi_script.py
```

> **Windows / AppLocker:** si los binarios del entorno están bloqueados, usa el patrón módulo:
> `conda run -n [nombre_entorno] python -m [paquete]` en vez de `[paquete].exe`.

### 2B. uv

```bash
# Primera vez — crear entorno e instalar dependencias
uv venv
uv sync

# Activar en cada sesión (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Ejecutar sin activar (recomendado en scripts/CI)
uv run python scripts/mi_script.py

# Añadir dependencia
uv add [paquete]
```

> **OneDrive:** si el repo está sincronizado, crea el venv fuera para evitar conflictos de lock:
> `$env:UV_PROJECT_ENVIRONMENT = "$env:LOCALAPPDATA\[nombre]-venv"` antes de `uv venv`.

---

## 3. Variables de entorno

```bash
# Copiar plantilla y editar (solo si el proyecto usa .env)
cp .env.example .env
```

| Variable | Descripción | Dónde obtenerla |
|---|---|---|
| `[NOMBRE_VAR]` | [qué hace] | [donde conseguirla o cómo generarla] |
| `[API_KEY]` | [qué servicio autentica] | [portal / equipo / `.env` local] |

> Las credenciales no se versionan. El archivo `.env` está en `.gitignore`.

---

## 4. Ejecución

> *Completa solo la sección de tu tipo de proyecto (§4A–§4F). Borra las demás.*

### 4A. App Shiny for Python

```powershell
# Arranque estándar
conda activate [nombre_entorno]
python -m shiny run app.py --port 8000
# o con uv:
uv run python -m shiny run app.py --port 8000
```

```bat
REM Atajo Windows — abrir el .bat directamente
docs\run_app.bat
```

> `python -m shiny` (no `shiny.exe`) — evita bloqueos de AppLocker sobre binarios del entorno conda.

**Acceso:** `http://localhost:8000`

**Verificación rápida:**
- [ ] La UI carga sin error en el navegador
- [ ] El selector de fuente responde (carga datos de prueba)
- [ ] No hay trazas de error en la consola

---

### 4B. App Streamlit

```powershell
# Arranque estándar
conda activate [nombre_entorno]
python -m streamlit run app.py --server.port 8501
# o con uv:
uv run python -m streamlit run app.py --server.port 8501
```

> `python -m streamlit` (no `streamlit.exe`) por la misma razón que Shiny.

**Acceso:** `http://localhost:8501`

---

### 4C. App con back + front (dos procesos)

**Terminal 1 — Backend / API:**
```powershell
uv run python -m uvicorn [paquete].[modulo]:app --host 127.0.0.1 --port [PUERTO_API] --reload `
  --reload-exclude ".venv" --reload-exclude "[dir_frontend]" --reload-exclude "docs"
```

**Terminal 2 — Frontend:**
```powershell
# Si el frontend es Python (Shiny/Streamlit): mismo patrón que §4A/§4B
# Si es Node/SPA:
cd [dir_frontend]
[npm run dev | pnpm dev | yarn dev]
```

**Puertos:**
- API: `http://localhost:[PUERTO_API]` · Swagger: `http://localhost:[PUERTO_API]/docs`
- UI: `http://localhost:[PUERTO_UI]`

**Verificación rápida:**
- [ ] API responde 200 en `/health` o en el primer endpoint
- [ ] UI carga y se comunica con la API (sin CORS error en consola)

---

### 4D. Solo frontend (Node / estático)

```bash
# Instalar dependencias (una vez)
[npm install | pnpm install | yarn]

# Dev server con hot-reload
[npm run dev | pnpm dev]

# Build para producción
[npm run build | pnpm build]
# Los estáticos quedan en [dist/ | build/ | out/]
```

**Acceso dev:** `http://localhost:[PUERTO]`

---

### 4E. Repo de investigación / notebooks

```bash
# Lanzar Jupyter
uv run jupyter lab
# o: conda activate [entorno] && jupyter lab

# Ejecutar script de análisis directamente
uv run python analysis/[nombre_script].py

# Generar reporte (si usa Quarto / Rmd)
quarto render docs/report.qmd
```

**Orden recomendado de ejecución (si hay dependencias entre notebooks):**
1. `[notebook_1.ipynb]` — [qué produce: ej. limpieza de datos]
2. `[notebook_2.ipynb]` — [qué produce: ej. modelos]
3. `[notebook_3.ipynb]` — [qué produce: ej. visualizaciones]

---

### 4F. Pipeline / scripts secuenciales (ETL, plan de ejecución)

> *Lista los scripts en orden. Indica qué produce cada uno y de qué depende.*

```powershell
# Opción A: orquestador único (si existe)
conda run -n [entorno] python scripts/[orquestador].py
# o: uv run python scripts/[orquestador].py
```

```powershell
# Opción B: manual paso a paso
# [Paso 1/N] — [descripción]
uv run python scripts/[paso_1].py

# [Paso 2/N] — [descripción; depende de la salida del paso anterior]
uv run python scripts/[paso_2].py

# ...
```

**Dependencias entre pasos:**

| Paso | Script | Entrada | Salida | Depende de |
|---|---|---|---|---|
| 1 | `scripts/[paso_1].py` | [origen: API, archivo] | `[tabla / archivo]` | — |
| 2 | `scripts/[paso_2].py` | `[tabla del paso 1]` | `[tabla / archivo]` | Paso 1 |
| N | `scripts/[paso_N].py` | `[...]` | `[resultado final]` | Paso N-1 |

> Si un paso falla, el pipeline se detiene. Revisar el log en `[logs/ruta_log.log]` para diagnosticar.

---

## 5. Despliegue

> *Completa solo el bloque que aplica.*

### 5A. ShinyApps.io (Shiny for Python)

```powershell
# Registrar cuenta (solo una vez)
conda run -n [entorno] python -c "from rsconnect.main import cli; cli()" add `
  --server https://api.shinyapps.io `
  --name [cuenta] --token [TOKEN] --secret [SECRET]

# Desplegar (primer deploy)
conda run -n [entorno] python -c "from rsconnect.main import cli; cli()" deploy shiny `
  --name [cuenta] --title "[Nombre de la app]" .

# Redeploy (app existente, por ID)
conda run -n [entorno] python -c "from rsconnect.main import cli; cli()" deploy shiny `
  --name [cuenta] --app-id [APP_ID] .
```

> `python -c "from rsconnect.main import cli; cli()"` (no `rsconnect.exe`) — mismo motivo AppLocker.
> El script `scripts/deploy.ps1` automatiza este proceso leyendo `.rscignore`.

### 5B. Streamlit Cloud

```bash
# Streamlit Cloud se conecta directamente al repo de GitHub.
# No hay comando de deploy manual — basta con hacer push a la rama configurada.
# Configurar en: https://share.streamlit.io → New app → seleccionar repo + rama + archivo
```

**Requisitos del repo:**
- `requirements.txt` en la raíz
- Credenciales: en Streamlit Cloud Secrets (no en el código)

### 5C. Servidor propio / Docker

```bash
# Build de imagen
docker build -t [nombre-imagen]:[tag] .

# Correr contenedor
docker run -d -p [PUERTO_HOST]:[PUERTO_CONTENEDOR] --env-file .env [nombre-imagen]:[tag]
```

---

## 6. Troubleshooting

| Problema | Causa probable | Solución |
|---|---|---|
| `acceso denegado` al ejecutar binario (AppLocker) | El `.exe` del entorno está bloqueado por políticas | Usar `python -m [paquete]` en vez del binario directo |
| `ModuleNotFoundError` al arrancar | Entorno no activado o dependencias no instaladas | `conda activate [entorno]` o `uv sync` |
| La app carga pero no muestra datos | Bases de datos o archivos no generados | Ejecutar el pipeline ETL primero (§4F) |
| `conda: command not found` en script automatizado | Conda no en el PATH del proceso no interactivo | Usar ruta absoluta de `conda.exe` o `conda run` con ruta completa |
| Puerto ya en uso | Otro proceso ocupa el puerto | `netstat -ano \| findstr :[PUERTO]` → matar proceso o cambiar puerto |
| `.env` no se carga | Archivo `.env` no existe o está en ruta incorrecta | `cp .env.example .env` y completar valores |
