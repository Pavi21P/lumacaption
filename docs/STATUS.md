# LumaCaption status

Updated: 2026-11-06 (America/Chicago)
Repository: https://github.com/Pavi21P/lumacaption
Branch: main
Current checkpoint: LC07 - evaluation runner and measured baseline complete
Next task: LC08 - reproducible Windows executable build
Task source: docs/PLAN.md
Session rule: one ready task per "continue", verify, commit/push, stop.
Scheduling: user-triggered; no unattended daily job.
GitHub Actions: disabled at user request; local checks required; do not re-enable unasked.

## Verified baseline

- 252 tests passed (64 evaluation, 188 existing); Ruff passed for 21 Python files.
- Evaluation CLI: python -m lumacaption.evaluate freeze/run; see docs/EVALUATION.md.
- Frozen manifest matches LC06 selection/source/exclusion digests.
- Real CPU baseline: 50/50 captions, zero image errors, zero network attempts.
- BLEU-1 57.60, BLEU-4 21.46, ROUGE-L 47.21; overlap scores, not accuracy.
- Test wall time 222.338 seconds; timings include concurrent synthetic-test activity.
- All 60 selected image hashes and source/reference hashes remain unchanged.
- Human review is pending (0/50); no tutorial quality comparison has been run.
- Local evidence: .local/evaluation/v1/baseline-2026-11-05-01/.
- Shared desktop/CLI engine behavior unchanged; prior LC05 offline smoke still applies.
- Reuse .venv and .cache/models; private reports/manifests remain ignored.

## LC08 starting points

- Add a reproducible Windows executable build script/spec and dependency notices.
- Verify launch and real captioning on this development machine.
- Keep model weights separate; ignore build artifacts; preserve existing source launchers.
- Inspect current package entry points and Windows scripts before choosing packaging.
- Clean-machine verification is LC09 and must remain separate from local build success.

## Outstanding evidence

Packaged runtime, clean-machine installation, human caption review, manual visual/
accessibility acceptance, comparative benchmarks, and GPU execution remain unverified.
