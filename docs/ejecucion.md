# Guía de Ejecución — project-suite

## 1. Requisitos previos

| Software | Versión mínima | Verificar con |
|---|---|---|
| Node.js | 18+ (para `node --test`) | `node --version` |
| Python | 3.9+ (stdlib only, sin instalar nada) | `python --version` |
| Git | 2.30+ | `git --version` |
| pre-commit (opcional, para contribuir) | cualquiera reciente | `pre-commit --version` |

## 2. Instalación del plugin (uso, no desarrollo)

### Claude Code

```
/plugin marketplace add C:\Users\aprieto\Github\project-suite
/plugin install project-suite@project-suite-marketplace
```

### opencode — Desde npm (recomendado)

```json
{ "plugin": ["@alexprietoromani/project-suite"] }
```

### opencode — Desde checkout local

Abre opencode dentro del repo (lee `.opencode/` + `opencode.json` automáticamente), o copia `.opencode/*` a `~/.config/opencode/`.

## 3. Desarrollo del plugin

```bash
git clone <url-del-repo> project-suite
cd project-suite
pip install pre-commit   # solo si vas a contribuir
pre-commit install
```

## 4. Ejecución (tests y validación)

```bash
# Tests de los hooks (Node, cero dependencias)
npm test

# Validador estructural del plugin
python scripts/validate_plugin.py

# Self-check del clasificador de version-bump
python scripts/test_check_version_bump.py

# Regenerar el mirror de opencode tras tocar skills/commands/.mcp.json
python scripts/sync_opencode.py
```

**Verificación rápida antes de un PR:**
- [ ] `npm test` → todos pasan
- [ ] `python scripts/validate_plugin.py` → `OK: N skills, ...`
- [ ] `python scripts/sync_opencode.py` seguido de `git status --short` → sin diffs sorpresa
- [ ] Si agregaste algo: `.claude-plugin/plugin.json`'s `version` refleja el bump correcto (`VERSIONING.md`)

## 5. Despliegue

No aplica un "despliegue" tradicional — se distribuye como marketplace local (`/plugin marketplace add <ruta>`) o, a futuro, vía npm (`@alexprietoromani/project-suite`).

Para publicar en npm:
```bash
npm login
npm publish --access public
```

## 6. Troubleshooting

| Problema | Causa probable | Solución |
|---|---|---|
| Cambios de fuente no aparecen en una sesión nueva | La caché de Claude Code (`~/.claude/plugins/cache/<marketplace>/project-suite/<version>/`) sigue en la versión vieja | Confirma que `plugin.json`'s `version` cambió, luego `/plugin marketplace update <marketplace>`. Si no crea la carpeta nueva: `/plugin uninstall project-suite` → `/plugin marketplace remove <marketplace>` → `/plugin marketplace add <ruta>` → `/plugin install` |
| `git commit` bloqueado por `check-version-bump` | Agregaste una skill/comando/agente/MCP/dependencia sin bumpear `plugin.json` | Bumpea la versión según `VERSIONING.md` y vuelve a intentar; o `git commit --no-verify` si el heurístico se equivocó |
| `pre-commit` no corre | No se instaló el hook localmente | `pre-commit install` (una vez por clon) |
| `npm test` falla con "command not found" | Node no está en el PATH | Instalar Node.js 18+ |
