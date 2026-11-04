# Next work, in reviewable checkpoints

These tasks are planned, not completed or scheduled. Each future work session should update PROGRESS.md with its actual date, implementation, checks, and limitations, then commit the completed unit.

1. **Saved sessions:** resume a workspace after restart, preserving manual edits and handling missing files.
2. **Measured evaluation:** choose an appropriate held-out dataset, document its terms and split, and evaluate captions with references plus human review. Compare against a runnable baseline before claiming a quality improvement.
3. **Windows distribution:** build and test a packaged executable on a clean Windows machine, with dependency/license inventory and a separate model download.
4. **Optional GPU inference:** detect compatible hardware, offer CPU fallback, and record measured memory/speed results.
5. **Accessibility polish:** validate keyboard navigation and screen-reader announcements with a Windows user.

Daily workflow:

- Choose one bounded task.
- Implement it and add tests for the behavior at risk.
- Run relevant checks.
- Add a dated progress entry with evidence.
- Commit the real changes and push the default branch.

No empty commits, artificial date changes, or automatic daily activity are needed.
