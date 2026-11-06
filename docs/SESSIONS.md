# Saved-session storage (schema 1)

LC01 provides the storage API; LC02 adds desktop Save/Open controls; LC03 adds local recovery.

## Desktop behavior

Use **Save session** and **Open session** above the image queue. The native save dialog confirms replacement of existing files. Open validates the entire document before offering to replace the current workspace. Malformed or unreadable files leave the workspace intact.

Queue additions, generated results, caption edits, retries, and setting changes mark the workspace unsaved. Before opening another session, clearing, or closing an idle workspace, choose Yes to save, No to discard, or Cancel to keep working. A cancelled or failed save stops the requested replacement. Exporting CSV/JSON does not save the workspace.

Save/Open and Clear are disabled while generation runs. Cancel the batch and wait for the current operation to finish before saving. Restored pending rows stay pending until Generate is clicked. Caption length, beam count, offline mode, and recursive-folder settings are preserved; the desktop does not expose a beam-count editor.

Missing or unavailable paths receive a red Missing display state and a preview warning. Their stored result status, captions, edits, timing, and provenance stay intact. Completed captions remain editable and exportable even without the image. Missing rows are excluded from generation and retry so retained text cannot be overwritten by another missing-file failure. Restore the image at its saved path and reopen the session to refresh availability. Relinking is LC04.

## Autosave and recovery

The desktop writes an atomic recovery snapshot after one second without further changes. Queue additions, edits (including paste/undo), options, retry state, and completed results trigger snapshots. Before generation begins, pending work is saved immediately. Snapshots use the same schema and size limits as manual sessions; image files and weights are not copied.

Storage is %LOCALAPPDATA%\LumaCaption\recovery\autosave.lumacaption.json. If LOCALAPPDATA is absent or relative, the fallback is AppData/Local/LumaCaption/recovery under the user's home directory. The working directory is never the default. This data contains private local paths and captions and stays outside the repository.

At startup, choose Yes to recover or No to discard the recovery copy. Recovered edits/settings and completed/error rows are preserved; interrupted work stays pending and generation does not start itself. Recovery leaves the workspace unsaved and does not restore the old manual save destination. Use Save session to choose a permanent destination.

Autosave does not clear the dirty flag. Successful manual saves and explicitly confirmed Open/Clear/Close actions remove the old recovery copy and cancel its timer. Cancelled actions, failed saves, and invalid imports retain recovery. Closing during a running batch still requires explicit confirmation to discard unsaved work. If cleanup fails, replacing/closing the workspace stops and reports the error.

One OS file lock protects the recovery store for the lifetime of its owning window. A second window still supports manual sessions but disables its own automatic recovery. The lock is released on normal close or process exit; the persistent recovery.lock file is intentionally retained. Snapshots and Tk state capture both run on the UI thread, avoiding stale background writes after a save or workspace replacement.

The footer shows pending/saved/error status. Write failures preserve the previous valid copy and retry after another change. Unreadable startup copies remain untouched and disable autosave for that window; move the damaged autosave file aside in the recovery directory before restarting to re-enable it. Manual saves remain available. The last debounce interval, failed writes, and abrupt power loss can still lose recent changes; recovery is not a versioned backup.

## API

- `Session(results=[], options=CaptionOptions(), offline=False, recursive=False)`
- `save_session(session, destination, overwrite=False)`: validates and atomically writes UTF-8 JSON. Existing destinations require explicit overwrite permission.
- `load_session(source)`: returns an independent, completely validated Session. It never opens source images, loads model weights, or starts inference.
- `SessionError`: invalid content, unsupported schema, or limits. File-access failures remain OSError subclasses; refusing replacement raises FileExistsError.

Use `workspace.lumacaption.json` by default. This filename pattern is ignored by Git. Session files contain local paths and edited text and should remain local.

## File contract

Top-level fields: `format: "lumacaption-session"`, `schema_version: 1`, `app_version`, `settings`, `results`.

Settings: caption `length`, integer `beams`, boolean `offline`, boolean `recursive`.

Each result preserves all CaptionResult fields: path, caption, status, error, elapsed_seconds, generated_caption, edited, model, model_revision, created_at.

Paths must be absolute; Windows drive/UNC paths are supported. Preserve paths and rows even when files no longer exist. Compare paths using Windows case/slash normalization to reject duplicates. The UI decides how to flag or relink missing images.

Statuses: pending, done, error. Timestamps must include a timezone. Elapsed times must be finite and nonnegative. JSON fields and types are checked strictly, including booleans versus integers, duplicate keys, unknown fields, and unsupported versions. Caption export JSON is a different format and is rejected.

Limits: 1,000 images, 16 MiB encoded file, 16,384 characters per caption/generated-caption/error, 32,767 characters per path, and 512 characters per provenance/status field. Empty workspaces are valid.

## Write guarantees and boundaries

Validate the entire document before creating a temporary file. Write and flush a temporary file in the destination directory, then replace atomically or publish without overwriting a concurrently created destination. Failed writes preserve an existing save and remove temporary files. Reject attempts to replace input files, including existing hard-link aliases.

Do not create missing parent directories implicitly. Loading returns fresh objects and has no UI side effects. Callers should replace their active state only after load_session succeeds. Schema changes require an explicit version/migration decision.

## Evidence

48 focused tests cover round trips, Unicode/edits/options/status preservation, missing paths, malformed and ambiguous JSON, resource limits, concurrent destination creation, failed flush/replacement, and source-file protection. All 84 project tests and Ruff checks passed on Windows for LC01. No model download or inference rerun was needed.

LC02 adds 17 desktop cases (22 desktop tests total), covering native-dialog outcomes, full workspace round trips, unsaved-work protection, invalid imports, failed saves, missing-image retention, busy controls, and explicit-only generation with restored options. All 101 project tests and Ruff passed; the real offline worker smoke also passed.
