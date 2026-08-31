#!/usr/bin/env node
// project-suite — ruleset text per mode. Pure function, no I/O.

const { normalizeMode, DEFAULT_MODE } = require('./project-suite-config');

const ESTRICTO_TEXT =
  'MODO ESTRICTO (project-suite) — antes de escribir código para cualquier cambio nuevo, corre\n' +
  '/project-suite:nueva-fase. No marques una Tarea como [X] en el tablero del track activo\n' +
  '(`python scripts/tablero.py --rutas`) sin que verificar-dod haya pasado en verde. Al cerrar\n' +
  'cada Sub fase, corre `tablero.py --indice` y `--sync`. Todo commit va por semantic-commit;\n' +
  'toda PR por pull-request. Si el cambio toca architecture.md o el modelo de datos\n' +
  '(diseno_db.md), corre auditar-coherencia ANTES de commitear. Ante cualquier bloqueo,\n' +
  'consulta docs/logs/log.md primero.';

const RELAJADO_TEXT =
  'MODO RELAJADO (project-suite) — para cambios grandes, considera /project-suite:nueva-fase.\n' +
  'Cuando cierres una Tarea, recuerda correr verificar-dod cuando puedas. Sigue usando\n' +
  'semantic-commit y pull-request para el historial. Revisa la coherencia de architecture.md/\n' +
  'diseno_db.md periódicamente — no hace falta en cada commit.';

function getInstructions(mode, track) {
  const effective = normalizeMode(mode) || DEFAULT_MODE;
  if (effective === 'off') return '';
  const base = effective === 'relajado' ? RELAJADO_TEXT : ESTRICTO_TEXT;
  return track ? base + '\nTrack activo: ' + track + ' (cambiar con /project-suite:track).' : base;
}

module.exports = {
  ESTRICTO_TEXT,
  RELAJADO_TEXT,
  getInstructions,
};
