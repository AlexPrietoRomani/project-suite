const test = require('node:test');
const assert = require('node:assert/strict');
const { getInstructions, ESTRICTO_TEXT, RELAJADO_TEXT } = require('../../hooks/project-suite-instructions');

test('getInstructions returns the estricto text by default', () => {
  assert.equal(getInstructions(undefined), ESTRICTO_TEXT);
});

test('getInstructions returns the estricto text for "estricto"', () => {
  assert.equal(getInstructions('estricto'), ESTRICTO_TEXT);
});

test('getInstructions returns the relajado text for "relajado"', () => {
  assert.equal(getInstructions('relajado'), RELAJADO_TEXT);
});

test('getInstructions returns an empty string for "off"', () => {
  assert.equal(getInstructions('off'), '');
});

test('getInstructions falls back to estricto for an invalid mode', () => {
  assert.equal(getInstructions('bogus'), ESTRICTO_TEXT);
});

test('ESTRICTO_TEXT uses blocking language and mentions the 3 gates', () => {
  assert.match(ESTRICTO_TEXT, /nueva-fase/);
  assert.match(ESTRICTO_TEXT, /verificar-dod/);
  assert.match(ESTRICTO_TEXT, /auditar-coherencia/);
});

test('RELAJADO_TEXT uses suggestion language ("considera")', () => {
  assert.match(RELAJADO_TEXT, /considera/);
});

test('ESTRICTO_TEXT and RELAJADO_TEXT are distinguishable by content (catches an accidental swap)', () => {
  assert.notEqual(ESTRICTO_TEXT, RELAJADO_TEXT);
  // "auditar-coherencia" only appears in the blocking (estricto) text.
  assert.doesNotMatch(RELAJADO_TEXT, /auditar-coherencia/);
  // "considera" (soft-suggestion language) only appears in the relajado text.
  assert.doesNotMatch(ESTRICTO_TEXT, /\bconsidera\b/);
});
