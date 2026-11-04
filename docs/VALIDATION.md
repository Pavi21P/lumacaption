# Validation evidence

## Environment

Windows, Python 3.11.9 (64-bit), Tk 8.6, CPU-only PyTorch. Exact installed package versions are recorded in requirements-lock.txt.

## Verified on 2026-11-03

- **36 tests passed together** in the Windows user context.
- Core coverage: image handling, orientation, transparency, limits, cancellation, error isolation, exports, and CLI errors.
- Desktop integration coverage: selection/edit/export, background completion, persistent fatal-error messaging, workspace clearing, and retry.
- Ruff lint and formatting passed (10 Python files).
- PowerShell setup script syntax passed.
- Dependency consistency passed against the final installed dependency set.
- Git whitespace check passed.

The sandbox cannot initialize the installed Tcl runtime. Desktop tests ran in the normal Windows user context instead; no desktop tests were skipped.

## Publication scope

This repository contains only LumaCaption application source, tests, setup/launcher files, dependency declarations, CI, and documentation. The original tutorial scripts and Flickr8k directories remain outside the repository. Virtual environments, model downloads, caches, generated exports, and credentials are excluded.

## Still unverified

- Real model inference and cached offline caption generation: the approximately 1 GB model download was interrupted before completion. Unit and desktop tests use a synthetic captioner, so they do not establish real caption quality.
- A complete fresh-machine setup run. The setup script was syntax-checked and dependencies were installed, but its interrupted end-to-end run is not counted as passed.
- Hosted GitHub Actions results must be checked after publication; local tests do not imply hosted CI success.
- Visual/manual acceptance by a Windows user. Widget tests do not establish visual quality or screen-reader accessibility.
- No controlled quality benchmark against the original tutorial model has been performed.

These limitations are recorded rather than represented as completed work.
