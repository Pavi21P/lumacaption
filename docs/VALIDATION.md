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

## LC05 diagnostics checks (2026-11-05)

All 188 tests passed, including 40 diagnostic cases. Coverage includes missing/out-of-range dependency versions, unreadable metadata, unsupported Python/bitness, incomplete/invalid/permission-denied caches, exact revision selection, child process failure/timeout/malformed output, network denial, private error redaction, incompatible CLI actions, and diagnostics dispatch without Pillow/ML imports. Ruff lint/format passed for all 18 Python files.

The real --diagnose command returned exit 0 in the Windows user context: Python 3.11.9/64-bit, actual Tk initialization, Pillow 12.3.0, torch 2.15.0, transformers 4.57.6, truststore 0.10.5, and expected pinned-cache files passed. This command imports runtime components and reads cache files but never loads weights or performs inference. Cache checks establish presence/readability and JSON structure, not binary completeness or integrity. Dependency checks cover declared application runtime requirements and imports, not a full audit of every installed package.

Because shared model/cache settings moved into config.py, the separate real-model regression was rerun: identical captions, zero network attempts, unchanged source-image hashes, matching desktop-worker output, and CSV/JSON exports in 30.658 seconds. Source photos and reports remain local. Frozen executable behavior, fresh-machine setup, and manual visual/accessibility acceptance remain unverified.

GitHub Actions is disabled at the user's request. LC05 is verified locally; no hosted run is expected for this checkpoint.

## LC06 evaluation-protocol checks (2026-11-05)

Documentation only: added the [versioned evaluation protocol](EVALUATION.md) and verified linked primary dataset/model/metric sources. The protocol specifies project-held-out selection; it makes no claim that Flickr8k is absent from BLIP's training data.

Read-only local metadata checks found 6000 train, 1000 dev, and 1000 test identifiers with no duplicates or pairwise overlap. Raw references contain 40460 rows for 8092 identifiers. All 1000 test identifiers have five references and existing image paths. Deterministic selection produced 50 test and 10 dev images, all with existing paths and references numbered 0-4. Two known prior smoke-test identifiers do not intersect dev/test. Source and selection digests are retained in ignored .local/evaluation-protocol-audit-2026-11-05.json; the complete private image-hash manifest belongs to LC07.

No image decoding, inference, quality scoring, or human review occurred. Relative documentation links, local starting paths, control characters, task states, and git diff whitespace were checked. No application code changed, so the prior LC05 automated and offline checks were not repeated. GitHub Actions remains disabled; no hosted run is expected. Data, original scripts, references, and reports remain outside the published files.

## LC07 evaluation runner and baseline (2026-11-05)

All 252 tests passed, including 64 new synthetic evaluation cases. Coverage includes deterministic selection/exclusions, malformed splits/references/manifests, corpus clipping and brevity penalty, non-perfect BLEU geometric means, short/empty hypotheses, five-reference LCS scoring, changed/missing/corrupt images, fatal and interrupted runs, offline network guards, timing summaries, output reuse, private CLI output, and unreviewed human fields. Ruff lint/format passed for all 21 Python files. The shared image loader, model engine, and desktop behavior did not change; the previous real desktop smoke remains applicable.

The [documented protocol](EVALUATION.md) was run locally with the pinned BLIP base model, CPU, Standard/35 tokens, three beams, no sampling, and the existing image preprocessing. The frozen 50-test/10-dev manifest matches all LC06 source, selection, and exclusion digests. Only the first dev image was used for warmup; no tuning was performed.

| Measure | Observed result |
| --- | --- |
| Completed test captions | 50/50 |
| Image failures / not processed | 0 / 0 |
| Blocked network attempts | 0 |
| Corpus BLEU-1 | 57.60 |
| Corpus BLEU-4 | 21.46 |
| Mean best-reference ROUGE-L F1 | 47.21 |
| Model preparation | 18.148 seconds |
| Dev warmup | 15.529 seconds |
| Total test wall time | 222.338 seconds |
| Successful load/inference median / p95 | 4.118 / 5.712 seconds |
| Human reviews supplied | 0/50; pending |

Lexical scores use the protocol's 0-100 scale, not an accuracy percentage. This small subset and tokenizer do not reproduce a published benchmark. Upstream training-data overlap is unknown, and there is no controlled tutorial comparison. Human quality, hallucination, and acceptance ratings remain null until an actual reviewer supplies them.

Environment: Windows (Python platform release 10), Intel Core i5-7200U CPU at 2.50 GHz, four configured Torch threads, Python 3.11.9, Pillow 12.3.0, torch 2.15.0, transformers 4.57.6. Some synthetic tests ran concurrently with inference; these timings describe this run and are not an isolated performance benchmark.

The run started at 2026-11-06T04:26:08.857781+00:00 and ended at 2026-11-06T04:30:25.310109+00:00 (UTC; November 5 in America/Chicago). It recorded parent Git commit 5841eee with a dirty working tree and exact runtime-source hashes; every recorded source hash was verified against the final LC07 implementation. Protocol and dependency-lock hashes also match. Manifest SHA-256: dbc2eacc8917657dce0ce727a51a855c70a0bad767bf0c6353128dc96692535b.

All 60 selected image hashes and original split/reference file hashes were verified unchanged after evaluation. Private evidence lives under .local/evaluation/v1/baseline-2026-11-05-01/: manifest.json, report.json, review-template.json, and verification.json. The last file records the post-run hash checks and concurrent-work timing limitation. These artifacts, dataset content, and original tutorial files remain excluded from Git. GitHub Actions remains disabled.

## LC08 Windows executable build (2026-11-06)

Built the [pinned portable-folder recipe](PACKAGING.md) on the Windows development
machine using CPython 3.11.9 x64, PyInstaller 6.22.3, hooks 2026.9, and the unchanged
runtime dependency lock. The shared analysis produced both LumaCaption.exe
(windowed) and LumaCaption-CLI.exe (console). Compilation succeeded; the initial
finalization rejected pip editable-install source metadata. The build now removes
only generated direct_url.json files within its output tree before final checks.
The already compiled bundle was finalized with that corrected step.

| Check | Result |
| --- | --- |
| Full synthetic suite | 270 passed in 28.43 seconds |
| Ruff lint / formatting | Passed, 25 Python files |
| pip check / PowerShell build-script syntax | Passed |
| Console help / frozen diagnostics | Passed, all reported runtime/cache checks OK |
| Console packaged smoke | Exit 0; 40.405 seconds |
| Windowed packaged smoke | Exit 0; 30.444 seconds |
| Inputs per smoke | 2; same captions as source LC05 run |
| Network attempts per smoke | 0 |
| Input hashes / desktop worker / JSON and CSV exports | Passed for both launchers |
| Bundle file hashes / source hashes | 6,200 / 23, all verified |
| Bundle bytes (excluding build-info.json) | 651,812,518 (621.6 MiB) |
| Dependency notice inventory entries | 37, including build tools |

Both executable smoke tests used the existing pinned BLIP cache through
LUMACAPTION_CACHE, blocked HTTP and socket connections, and exercised actual CPU
inference. They created a real withdrawn Tk window, generated a caption through
its worker, and checked exports. Recovery was disabled for these tests, and input
hashes remained unchanged. The windowed executable was explicitly awaited and
its exit code checked. This is automated runtime verification, not visual or
keyboard/accessibility acceptance. Timings include startup/model work and are not
an isolated performance benchmark.

Private reports: .local/packaged-lc08-cli-2026-11-06.json and
.local/packaged-lc08-gui-2026-11-06.json; adjacent logs retain raw output.
Build log: build/LumaCaption-0.1.0-win64/build.log. Local executable folder:
dist/LumaCaption-0.1.0-win64/LumaCaption/. Its build-info.json records exact
dependency versions and SHA-256 hashes. Bundle validation found no model artifacts
or pip source-URL files; Python, Tcl 8.6.12, Tk, and dependency notices are retained.
Tracked-file and reachable-history checks exclude tutorial originals and datasets;
the bundle, weights, images, and raw reports remain outside Git.

Optional Torch build warnings about tensorboard, CUDA, and a non-Windows OpenMP
path did not prevent the exercised CPU BLIP path. No GPU support is claimed.
The package is unsigned and contains no installer. This development-machine result
does not establish independence from the source environment: clean Windows/VM
installation, initial model download, and offline restart remain LC09. Bit-for-bit
rebuild reproducibility, manual acceptance, and human caption review are unverified.
GitHub Actions remains disabled.

## LC09 environment availability and LC10 keyboard controls (2026-11-06)

LC09 was not executed. Read-only host discovery reported Windows 10 Home
(EditionID Core), build 19045. WindowsSandbox.exe was absent from System32 and
command lookup; Hyper-V Get-VM/vmms, VMware vmrun, and VirtualBox VBoxManage were
not available through command/service discovery. No separate clean Windows host
was provided. This establishes the current test-environment blocker, not a claim
that no virtualization software could exist elsewhere. No optional features or VM
software were installed. LC09 remains blocked.

LC10 proceeded as the next ready independent task. Ten additional integration
tests exercise mapped Windows Tk widgets with generated keyboard events:

- Add images, generate with a synthetic captioner, edit through a text key binding,
  export JSON, save and reopen a session, and switch queue/editor panes.
- Tab and Shift+Tab leave the editor without adding whitespace; the full enabled
  control order wraps correctly and skips unavailable actions.
- Arrow keys change the selected row and corresponding caption; Enter focuses editing.
- Busy-state shortcuts cannot open forbidden dialogs; Esc cancels a batch and is
  inert when idle. Cancel/completion leave focus on an enabled control.
- Cancelled session replacement preserves edits; cancelled Ctrl+I adds no tab;
  normal Ctrl+Z undo still works.
- Folder/help shortcuts operate, while a modal grab blocks workspace actions.
- Completion does not steal focus from an editor, and every interactive control is
  mapped with nonzero dimensions inside the minimum 960x680 client height.

The first run found an unsupported ISO_Left_Tab symbol on Windows; only the
supported Shift+Tab binding is retained. The next traversal check exposed clipped
lower controls at this host's 1366x768 resolution. The layout now reserves footer
space and allows the queue to shrink before action controls disappear. These fixes
were followed by a successful full suite: **280 passed in 25.10 seconds**.
Ruff lint and format passed for all 25 Python files. No dependency/model/generation
changes were made, so no real-model inference was rerun.

Native file dialogs return stubbed paths in tests, and model output is synthetic.
Real native-dialog keyboard navigation, human focus/visual acceptance, screen-reader
announcements, high-contrast/high-DPI behavior, and assistive-technology compatibility
remain unverified. See the [LC11 walkthrough](KEYBOARD.md). The LC08 executable
was not rebuilt for this source-only checkpoint; its successful frozen smoke remains
evidence for the LC08 snapshot only. Use the source launcher or make a new named
build to include LC10. GitHub Actions remains disabled.

## LC11 partial manual feedback (2026-11-06)

The user tested the source desktop at b7dc980 and reported that the application and
captioning worked well. The app was started offline with the existing cached model
and a separate recovery directory. Two original synthetic image fixtures were
prepared locally. Recorded environment: Windows 10 Home build 19045, 1366x768
display, Tk 8.6.12, Tk scaling approximately 1.335. This is not a caption-quality
benchmark or evidence that every prepared fixture was used.

Follow-up clarified that the user **did not use a screen reader** and **had not
tried the final edit/export/save/reopen/cancel checks**. The user then requested
skipping screen-reader testing for now. Therefore spoken names, announcements,
progress/errors with assistive technology, and those manual persistence flows are
still unverified. LC11 remains blocked, not passed. The initial broad positive
feedback must not be interpreted as acceptance of these untested areas.

No defect was reported and no code changed in this checkpoint. Existing automated
LC10 results remain applicable; documentation/link/whitespace checks were performed
without repeating tests or inference. Private setup and raw observations remain in
.local/lc11-review-2026-11-06/. Resume the [manual walkthrough](KEYBOARD.md) when
the user is ready; proceed independently with LC12 in the meantime.

## LC12 device selection and CPU fallback (2026-11-06)

Read-only host checks found Intel HD Graphics 620 and torch 2.15.0+cpu.
torch.version.cuda was null, torch.cuda.is_available() was false, and
torch.cuda.device_count() was zero. No drivers, dependency locks, or installed
packages were changed to attempt GPU execution.

The source app now supports cpu/cuda selection in the desktop and CLI. Eighteen
new simulated engine/CLI cases check CPU-without-CUDA-probing, model and tensor
placement, integer token preservation, unavailable/failed CUDA initialization,
placement failure, one CPU retry after CUDA out-of-memory, failed CPU recovery,
non-memory errors, invalid device names, CLI forwarding, and observable fallback.
Two desktop cases cover local-only preference, busy-state controls, fallback-engine
reuse, actual-device reporting, and reloading when the request changes.

Full regression: **300 passed in 23.76 seconds**. Ruff lint and formatting passed for
26 Python files. Existing keyboard traversal, minimum 960x680 layout, saved-session,
recovery, evaluation, and packaging-unit regressions passed. These simulated CUDA
cases do not establish actual GPU execution or compatibility.

| Real-model smoke | Requested CPU | Requested CUDA |
| --- | --- | --- |
| Actual device | CPU | CPU fallback |
| Input photos captioned | 2 | 2 |
| Captions match prior LC05 source run | Yes | Yes |
| Network attempts | 0 | 0 |
| Original input hashes unchanged | Yes | Yes |
| Real withdrawn Tk worker | Passed | Passed |
| CSV/JSON exports | Passed | Passed |
| Elapsed seconds | 24.537 | 23.312 |

The CUDA-request run reported that CUDA was unavailable. Both used existing pinned
BLIP weights with HTTP/socket calls blocked and offline mode enabled. Reports are
.local/offline-lc12-cpu-2026-11-06.json and
.local/offline-lc12-cuda-2026-11-06.json; adjacent logs retain raw details.
Timings include setup and concurrent validation activity and are not an isolated
performance benchmark. No GPU throughput or memory measurements exist.

The evaluation runner still defaults to CPU under its fixed protocol; its baseline
was not rerun. Device choice is an app-window preference, not new saved-session data.
The old LC08 executable was not rebuilt; its smoke results apply only to that older
snapshot. Use the current source launcher for LC10/LC12, or make and verify a new
named build. Clean-machine and manual accessibility acceptance remain pending.
See [device behavior and limits](DEVICES.md). GitHub Actions remains disabled.

## LC08R failed refresh and host incident (2026-11-06)

The refresh used the existing pinned environment and current LC12 source at
03bda3f, with updated bundled usage notes. The original LC08 output was preserved.
PyInstaller's log reports both executable launchers compiled and COLLECT completed.
However, finalization failed when hashlib.file_digest called fileobj.readinto:
OSError: [Errno 22] Invalid argument. A finalization-only retry reproduced that
failure. The generated artifact responsible was not identified.

The host reported approximately 621,204 KiB free physical memory and 2,838,532,096
bytes free on the build drive during diagnosis. PowerShell initialization and a
command-runner host also failed. The user reported a Windows blue screen during
this attempt, stated Firefox was the only app they had open, and then requested
publication of current changes. These observations do not establish the crash's
exact cause; no crash dump or system-event analysis was performed.

The attempted folder is dist/LumaCaption-0.1.0-win64-lc12/LumaCaption/. It is
**unverified and must not be distributed as a tested build**. No sealed checksum
manifest, frozen diagnostics, or runtime caption checks were completed. The private
verification harness was prepared but not run. Build log:
build/LumaCaption-0.1.0-win64-lc12/build.log.

Heavy build/model activity has stopped. LC08R is blocked until resource conditions
are investigated or a separate build machine is available. Do not automatically
retry it on a generic continuation. Source code and dependencies did not change;
the prior LC12 automated and offline results remain the source baseline.
Publication checks for this documentation-only checkpoint cover links, whitespace,
task states, and exclusions. No inference or full test suite was repeated.

## LC08R low-load resource review (2026-11-07)

Read Windows memory, fixed-disk, and page-file counters once; queried at most eight
recent System events (IDs 41, 1001, 2004) over three days. No app, dependency import
probe, inference, packaging, disk scan, or crash-dump analysis was started.
The sandbox denied CIM access; the successful read used the Windows user context.
Discarded the failed query's null-derived zero values.

| Counter | Observed snapshot |
| --- | --- |
| Physical RAM | 7.87 GiB total; 3.01 GiB available |
| Windows virtual-memory counters | 15.09 GiB total; 8.14 GiB free |
| System drive (C:) | 7.26 GiB free of 124.76 GiB |
| Project/build drive (D:) | 2.61 GiB free of 97.66 GiB |
| Page file | 7,393 MB allocated; 809 MB in use; 3,620 MB peak use |

These are point-in-time counters, not a load test or a measurement of build peaks.
The page-file peak covers the current boot, not necessarily the failed build.
The project drive is below the existing 3 GiB build guard in
[scripts/build_windows.py](../scripts/build_windows.py). Passing that guard later
would not establish that a build is safe: it is a minimum disk check, not a measured
resource budget. No files were deleted and no page-file/system settings changed.

The bounded System-event query returned a Microsoft-Windows-Kernel-Power event 41
at 2026-11-07T00:45:49Z (November 6, 18:45:49 Central), with BugcheckCode 59
(decimal; 0x3B). This corroborates the reported incident but does not identify a
responsible driver, application, or hardware fault. No causal diagnosis is claimed.
Raw event payloads, memory dumps, and machine identifiers were not published.

LC08R remains blocked. Prefer a separate Windows build host; any same-PC retry
requires a deliberate resource plan and agreed execution environment. Neither a
passing disk check nor this review authorizes an automatic retry. Preserve the
failed output until a retention/cleanup decision is made. LC09 and LC11 remain
blocked independently. Documentation links and whitespace were checked; the
existing LC12 test baseline is unchanged. GitHub Actions remains disabled.

## LC08D checksum error diagnostics (2026-11-07)

The build helper now converts file-open/read OSError failures into an actionable
error containing the project-relative artifact path and OS error number. Paths
outside the project use the basename. The normal handled CLI message does not
print the private absolute root; a local traceback can still expose the chained
original exception. Successful SHA-256 behavior is unchanged.

Four new synthetic cases cover a known SHA-256 vector, open failure, read failure,
and finalization failure through main. They verify the artifact path, OS error 22,
original exception chaining, exit code 1, no retry, no manifest on failure, and
preserved fixture bytes. No PyInstaller or generated executable was run.

Focused packaging tests: 22 passed. Full sequential pytest: 304 passed in 24.55s.
Ruff lint and format checks passed (26 files) with --no-cache after the sandbox
could not write the existing cache. No real model was loaded and no inference or
packaging was repeated. Application code/dependencies are unchanged; LC12 remains
the real-caption baseline. The old failing artifact and crash cause remain unknown.
LC08R is still blocked pending a suitable execution environment/resource plan.

## LC08P read-only build prerequisites (2026-11-07)

`Build-Windows.ps1 -CheckOnly` forwards to `scripts/build_windows.py --check-only`.
The shared prerequisite function checks the pinned Windows/Python environment,
installed package metadata, project version, output/work-name availability, and
existing 3 GiB disk guard. It returns before creating any build folders. It does
not import Torch/Transformers or run PyInstaller. Missing package metadata is
reported as a check failure. The wrapper rejects installation plus check-only.

Six synthetic cases cover a valid environment at the exact disk minimum, disk
below that minimum, existing output, existing work folder, missing dependency,
and invalid output name. Tests prohibit build/staging/finalization/subprocess
calls and compare filesystem entries before/after. Existing build safety tests
continue to exercise the shared prerequisite checks.

28 focused packaging tests passed. The full sequential suite passed 310 tests in
23.94 seconds. Ruff lint/format passed for 26 files. The actual PowerShell command
with a fresh LumaCaption-preflight-check name passed against the installed metadata;
no corresponding output/work folder existed before or after. The wrapper rejected
-CheckOnly with -InstallBuildTools. No installation or actual build was run.

These results are prerequisite/dispatch evidence, not a RAM assessment, reserved
disk capacity, dependency-import check, packaged-runtime pass, or crash diagnosis.
The failed LC08R bundle remains untouched and unverified. Application code and
dependencies are unchanged. No model inference or heavy artifact scan was run.

## LC08U university setup (2026-11-09)

The user approved the proposed university-PC setup after the read-only assessment.
No university policy document was independently reviewed. The initially empty
workspace was populated from public main at `9741365`; application source and
dependency locks were unchanged during this setup.

| Observation | Actual result |
| --- | --- |
| OS | Windows 11 Enterprise, 10.0.26200, x64 |
| Installed RAM | 15.69 GiB |
| Initial available RAM / C: free | 3.58 GiB / 75.50 GiB |
| Latest after user cleanup | 5.17 GiB available RAM / 73.21 GiB free C: |
| Initial tool discovery | No Git on PATH or two common install paths; python was a Store alias; py invoked Spyder's conda-forge Python 3.11.9 x64 |
| Git setup | MinGit 2.56.0.windows.4 archive SHA-256 matched official release metadata; isolated under .local/tools/git |
| Python setup | Official 3.11.9 x64 installer signature valid, signer Python Software Foundation; installed under .local/tools/python311 with Tcl/Tk |
| Environment | Fresh .venv, requirements-lock.txt and requirements-build.txt installed; pip check passed |
| Build prerequisite check | PowerShell -CheckOnly passed for LumaCaption-0.1.0-win64-university-20261109; no executable build started |
| Source CLI --help | Exit 0, usage printed |
| Source tests | 310 passed in 15.66 seconds, synthetic captioners; monitored available RAM samples 4.16 and 3.47 GiB |
| Ruff | Lint passed; format check passed, 42 files already formatted |
| Source CLI --diagnose | Exit 1; Python/Tk/Pillow/torch/transformers/truststore passed; absent model cache failed |
| Private test images | Three supplied photos moved to .local/Test Images; git check-ignore confirmed all three |

The first setup monitor did not capture a child exit code. Its outer exit 0 was
not accepted as setup evidence: the completion log, separate pip check, exact
dependency prerequisite check, and actual tests established the results above.
The private helper was corrected before later monitored commands, which reported
explicit exit codes. Setup resource samples ranged from 3.63 to 5.19 GiB available
RAM. Samples are intermittent observations, not a measurement of peak consumption.

The proposed heavy-task resource plan requires at least 8 GiB available RAM to
start and stops below 2 GiB available RAM or 15 GiB free disk, with one heavy task
at a time and two inference-library threads. These are conservative session limits,
not measured package requirements or proof against a crash. No heavy task was
started to test these limits. At 5.17 GiB available RAM, the user explicitly chose
to save the setup checkpoint and leave the build pending.

No model download/load/inference, PyInstaller build, generated executable launch,
real image caption, offline restart, or runtime path-with-spaces check occurred.
The spaced folder is prepared only. Synthetic source tests cover keyboard and
persistence behavior; they do not establish packaged behavior or a person's native
dialog/keyboard walkthrough. Manual caption edits, CSV/JSON exports, save/reopen,
and cancelling an unsaved-changes prompt with edits preserved remain unperformed
here. Screen-reader testing stays deferred. This host now contains development
tools; it does not by itself satisfy LC09 clean-machine distribution testing.
GitHub Actions was not enabled. Raw reports, photos, tools, caches, and environments
remain ignored; only documentation is included in this checkpoint.
