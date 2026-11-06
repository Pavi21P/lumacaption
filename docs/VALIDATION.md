# Validation evidence

## Environment

Windows, Python 3.11.9 (64-bit), Tk 8.6, CPU-only PyTorch. Exact installed package versions are recorded in requirements-lock.txt.

## Automated checks

- 36 tests passed in the Windows user context on 2026-11-03 and again on 2026-11-04.
- Core coverage: image handling, orientation, transparency, limits, cancellation, error isolation, exports, and CLI errors.
- Desktop integration coverage: selection/edit/export, background completion, persistent fatal-error messaging, workspace clearing, and retry.
- Ruff lint and formatting, dependency consistency, and Git whitespace checks passed.
- [The initial hosted Windows CI run passed](https://github.com/Pavi21P/lumacaption/actions/runs/41772593762) for commit a55cc03.

The sandbox cannot initialize the installed Tcl runtime. Desktop tests run in the normal Windows user context; no desktop tests were skipped.

## Real-model offline verification

Completed on 2026-11-03; the saved report was inspected on 2026-11-04. The pinned Salesforce BLIP weights were fully downloaded into the ignored local cache. The smoke test then blocked HTTP requests and IPv4/IPv6 socket connections while using the cached model.

Verified:

- Two local photos produced nonempty captions.
- Zero network attempts occurred during the verification.
- The loaded model was reused rather than reloaded for each image.
- The actual Tk background worker generated the same first-image caption as the shared captioning pipeline.
- JSON and CSV export contents round-tripped successfully.
- SHA-256 checks confirmed the source images were unchanged.

| Input scene | Generated caption | Measured time |
| --- | --- | --- |
| Child in a pink dress beside a wooden playhouse | A little girl in a pink dress | 22.309 seconds, including initial model loading |
| Two dogs facing each other on a paved road | Two dogs playing on the side of the road | 4.579 seconds with the model loaded |

The complete run, including desktop-worker verification, took 33.118 seconds. These are two smoke-test examples on this computer, not an accuracy benchmark or a general performance guarantee. A repeat run after the final loader fix on 2026-11-04 passed the same checks with identical captions in 34.238 seconds and zero network attempts. The original input photos and local JSON reports are excluded from Git.

### Reproduce with your own photos

From the project root, after the model has been downloaded:

~~~powershell
$env:LUMACAPTION_CACHE = Join-Path $PWD ".cache\models"
.\.venv\Scripts\python.exe scripts\verify_offline.py "C:\Photos\one.jpg" "C:\Photos\two.jpg" --desktop --report .local\offline-report.json
~~~

The script fails if it attempts network access, cannot caption an image, changes an input, or fails its export/worker checks. Choose a new report filename for each run. Omit --desktop when testing the engine without a graphical session.

## Windows setup verification (2026-11-04)

Setup-Windows.ps1 -Dev -DownloadModel completed with exit code 0 in the existing Windows development environment. It initialized Tk, installed/verified the pinned dependencies and package, loaded the cached model, and printed the documented ready message. This verifies repeat setup here, not installation on a fresh machine.

During validation, Transformers 4.57.6 started an optional background safetensors-conversion worker after reporting the model ready. That delayed process exit and performed unnecessary network work. LumaCaption now sets DISABLE_SAFETENSORS_CONVERSION=true inside its process before model loading. The official pinned weights still use restricted weights-only loading. Setup was rerun successfully with the fix.

## Windows launcher verification (2026-11-04)

The actual Launch-LumaCaption.cmd entry point successfully captioned a local photo with --offline and saved its JSON export. The input path contained spaces; the exported caption matched the offline smoke test. The output remains in the ignored .local directory.

## Publication scope

Only independent LumaCaption source, tests, verification scripts, setup/launcher files, dependency declarations, CI, and documentation are published. Tutorial scripts and Flickr8k directories remain outside the repository. Virtual environments, model weights, caches, generated exports, local reports, and credentials are excluded.

## Still unverified

- Installation on a fresh Windows machine. Testing this existing development environment does not establish fresh-machine compatibility.
- Visual/manual acceptance by a Windows user. Widget tests do not establish visual quality or screen-reader accessibility.
- A controlled quality benchmark against the original tutorial model.

These limits are distinct from the successful real-model offline smoke test.

## LC01 session-storage checks (2026-11-04)

48 new storage tests passed, bringing the full suite to 84 passing tests. Ruff passed for 13 Python files. Tests exercised malformed files, schema/resource limits, edit/settings round trips, missing images, write/flush failures, destination races, and original-file protection. Desktop Save/Open controls are not part of this checkpoint. The existing offline-model evidence above remains applicable; inference code did not change.

## LC02 desktop-session checks (2026-11-04)

22 desktop integration tests passed, bringing the full suite to 101 passing tests. New coverage includes session/editor/settings round trips, malformed imports, cancelled dialogs, save failures, save-over-open behavior, missing-image retention/export, empty workspaces, unsaved settings, busy controls, and restored options reaching the worker only after explicit generation. Native dialog responses are mocked; widgets and file persistence are exercised with real Tk on Windows. Ruff lint/format passed for all 13 Python files.

The cached real-model offline smoke was rerun because restored generation options now reach the desktop worker. It passed with identical captions, zero network attempts, unchanged source-image hashes, matching worker output, and successful CSV/JSON exports in 28.904 seconds. Local reports and photos remain excluded from Git. This is regression evidence, not a new quality benchmark or manual visual/accessibility acceptance.

## LC03 autosave/recovery checks (2026-11-05)

All 129 tests passed, including 42 desktop tests and 8 recovery-store tests. The 28 new cases cover debounce with pasted text, completed/pending recovery, startup decline, corrupted copies, failed writes and retry, exclusive ownership across processes, abrupt-process exit, explicit-save/discard cleanup, cancelled actions, unavailable storage, invalid imports, and manual-save failures. Tk tests now use one interpreter with isolated windows after repeated interpreter creation exposed intermittent local Tcl file-loading errors; no tests are skipped. Ruff lint/format passed for all 15 Python files.

The real cached-model offline regression passed after adding the pre-generation recovery snapshot: identical captions, zero network attempts, unchanged original files, matching desktop-worker output, and CSV/JSON checks in 48.959 seconds. The smoke script disables automatic recovery to avoid modifying user recovery data; recovery persistence is exercised separately by the integration tests. Reports remain local. This verifies behavior on the current development machine, not clean-machine installation, power-loss durability, or manual visual/accessibility acceptance.

## LC04 relinking checks (2026-11-05)

All 148 tests passed, including 61 desktop cases. The 19 new cases cover preserving every result field across pending/done/error rows; live editor, recovery, and manual-save round trips; cancellation; unavailable/damaged/unsupported files and directories; simulated read failures; duplicate Windows case/slash paths and hard links; queue order; in-place restoration; busy/selection controls; files moved during a session; and generation from the replacement only after an explicit request. Existing image-loading limits remain shared with the captioning pipeline. Native dialog responses are mocked; real Tk widgets and synthetic image files are exercised. Ruff lint/format passed for all 15 Python files.

The real-model offline regression also passed after the preview/relink changes: identical captions, zero network attempts, unchanged source-image hashes, matching desktop-worker output, and CSV/JSON exports in 44.653 seconds. This remains a development-machine regression check, not an accuracy benchmark or manual visual/accessibility acceptance. Test photos and reports stay outside Git.
