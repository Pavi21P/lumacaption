# LumaCaption status

Updated: 2026-11-05 (America/Chicago)
Repository: https://github.com/Pavi21P/lumacaption
Branch: main
Current checkpoint: LC06 - reproducible evaluation protocol complete
Next task: LC07 - evaluation runner and measured baseline
Task source: docs/PLAN.md
Session rule: one ready task per "continue", verify, commit/push, stop.
Scheduling: user-triggered; no unattended daily job.
GitHub Actions: disabled at user request; local checks required; do not re-enable unasked.

## Verified baseline

- LC06 is documentation only; links, paths, consistency, and whitespace checked.
- Local metadata audit: disjoint 6000/1000/1000 train/dev/test lists.
- Fixed 50 test + 10 dev selections have files and five references each.
- No images decoded, inference run, quality scores, or human ratings in LC06.
- Prior LC05 baseline: 188 tests and Ruff for 18 Python files passed.
- Prior real diagnostics passed; cache presence is not inference proof.
- Prior offline regression: zero network attempts, unchanged photos, matching
  desktop-worker captions and CSV/JSON exports; total 30.658 seconds.
- Reuse .venv and .cache/models; .local reports remain ignored.

## LC07 starting points

- Implement docs/EVALUATION.md exactly; create a private frozen manifest first.
- Use the shared offline engine; test metrics/selection/failures with synthetic data.
- Preserve all 50 rows and distinguish failed, incomplete, and unreviewed results.
- Keep source images/references/manifests/generated reports outside Git.
- Local metadata audit: .local/evaluation-protocol-audit-2026-11-05.json.
- Run a real baseline if data/cache remain available; do not invent human ratings.
- Evaluation quality and upstream training-data overlap remain unverified.

## Outstanding evidence

Clean-machine installation, packaged runtime, manual visual/accessibility acceptance,
comparative benchmarks, and GPU execution remain unverified.
