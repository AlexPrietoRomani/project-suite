// .opencode/plugins/project-suite-frontmatter.cjs
// project-suite — frontmatter YAML parser (CommonJS).
//
// Decoupled from the ESM plugin so project-suite.mjs keeps a single default
// export while commands/skills metadata is parsed here. Tolerates LF and CRLF
// and understands YAML block scalars ('>' folded, '|' literal, with optional
// '-'/'+' chomping) used by multi-line skill descriptions.

'use strict';

const fs = require('fs');

const FRONTMATTER_RE = /^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$/;
const BLOCK_HEADER_RE = /^[|>][+-]?\d*$/;

function unquote(value) {
  const first = value[0];
  if ((first === "'" || first === '"') && value[value.length - 1] === first) {
    return value.slice(1, -1);
  }
  return value;
}

// Reads a YAML block scalar starting at `start` (the line after the key) and
// returns its folded/literal value plus the index of the first line outside
// the block.
function readBlockScalar(lines, start, header) {
  const folded = header[0] === '>';
  const block = [];
  let i = start;
  for (; i < lines.length; i++) {
    const line = lines[i];
    if (line.trim() === '') {
      block.push('');
      continue;
    }
    if (!/^[ \t]/.test(line)) break;
    block.push(line);
  }
  const first = block.find((line) => line.trim() !== '');
  const indent = first ? first.match(/^[ \t]*/)[0].length : 0;
  const stripped = block.map((line) => line.slice(indent));
  let value;
  if (folded) {
    // Folded: consecutive lines join with a space, blank line becomes '\n'.
    value = stripped.reduce((acc, line) => {
      if (line === '') return acc + '\n';
      if (acc === '' || acc.endsWith('\n')) return acc + line;
      return acc + ' ' + line;
    }, '');
  } else {
    value = stripped.join('\n');
  }
  return { value: value.trim(), next: i };
}

// Returns the value of a top-level `key:` in the frontmatter block, or
// undefined when absent. Handles plain scalars, quoted scalars and block
// scalars ('>' / '|' with optional chomping indicator).
function getScalar(meta, key) {
  const lines = meta.split(/\r?\n/);
  const re = new RegExp('^' + key + ':\\s*(.*)$');
  for (let i = 0; i < lines.length; i++) {
    const match = lines[i].match(re);
    if (!match) continue;
    const inline = match[1].trim();
    if (inline === '' || BLOCK_HEADER_RE.test(inline)) {
      return readBlockScalar(lines, i + 1, inline || '|').value;
    }
    return unquote(inline);
  }
  return undefined;
}

// parseCommandFile(filePath) -> { description, template } | null
function parseCommandFile(filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  const match = content.match(FRONTMATTER_RE);
  if (!match) return null;
  return {
    description: getScalar(match[1], 'description'),
    template: match[2].trim(),
  };
}

// parseSkillFile(filePath) -> { name, description, body } | null
function parseSkillFile(filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  const match = content.match(FRONTMATTER_RE);
  if (!match) return null;
  return {
    name: getScalar(match[1], 'name'),
    description: getScalar(match[1], 'description'),
    body: match[2].trim(),
  };
}

module.exports = { parseCommandFile, parseSkillFile };
