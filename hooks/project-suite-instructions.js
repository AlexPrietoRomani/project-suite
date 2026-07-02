#!/usr/bin/env node
// project-suite — ruleset text per mode. Pure function, no I/O.

const { normalizeMode, DEFAULT_MODE } = require('./project-suite-config');

const ESTRICTO_TEXT =
  'MODO ESTRICTO (project-suite) — antes de escribir código para cualquier cambio nuevo, corre\n' +
  '/project-suite:nueva-fase. No marques una Tarea como [X] en docs/task/tareas.md sin que\n' +
  'verificar-dod haya pasado en verde. Todo commit va por semantic-commit; toda PR por\n' +
  'pull-request. Si el cambio toca architecture.md o el modelo de datos (diseno_db.md), corre\n' +
  'auditar-coherencia ANTES de commitear. Ante cualquier bloqueo, consulta docs/logs/log.md primero.';

const RELAJADO_TEXT =
  'MODO RELAJADO (project-suite) — para cambios grandes, considera /project-suite:nueva-fase.\n' +
  'Cuando cierres una Tarea, recuerda correr verificar-dod cuando puedas. Sigue usando\n' +
  'semantic-commit y pull-request para el historial. Revisa la coherencia de architecture.md/\n' +
  'diseno_db.md periódicamente — no hace falta en cada commit.';

function getInstructions(mode) {
  const effective = normalizeMode(mode) || DEFAULT_MODE;
  if (effective === 'off') return '';
  if (effective === 'relajado') return RELAJADO_TEXT;
  return ESTRICTO_TEXT;
}

module.exports = {
  ESTRICTO_TEXT,
  RELAJADO_TEXT,
  getInstructions,
};
