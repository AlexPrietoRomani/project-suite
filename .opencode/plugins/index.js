// .opencode/plugins/index.js
// project-suite — OpenCode V2 plugin autodiscovery entry.
//
// V2 looks for `index.js` inside local plugin folders; re-exporting the
// default here keeps a single plugin definition in project-suite.mjs.
export { default } from './project-suite.mjs';
