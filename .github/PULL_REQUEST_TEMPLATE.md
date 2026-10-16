## What does this PR do?

<!-- One or two sentences. -->

## Checklist

- [ ] `npm test` passes (if hooks/ was touched)
- [ ] `python scripts/validate_plugin.py` prints `OK`
- [ ] `python scripts/sync_opencode.py` ran and produced no unexpected diff (if skills/commands/.mcp.json changed)
- [ ] `.claude-plugin/plugin.json`'s `version` was bumped correctly per `VERSIONING.md` (or this PR is exempt — docs/README only)
- [ ] `check_version_bump.py` not bypassed with `--no-verify` (unless the heuristic is genuinely wrong)
- [ ] No `Co-Authored-By` trailers in any commit (unless explicitly intended)

## Related docs

<!-- If this PR comes from a planned Fase, name its track/plan (docs/plan/ is local & gitignored). -->
