# Keyboard controls

The source desktop supports the shortcuts below. Start it with Launch-LumaCaption.cmd.
The existing LC08 executable folder predates LC10; rebuild with a new BuildName to
include these changes. See [packaging](PACKAGING.md).

| Key | Action |
| --- | --- |
| Ctrl+I | Add images |
| Ctrl+Shift+I | Open an image folder |
| Ctrl+O | Open a saved session |
| Ctrl+S | Save the workspace through the Save session dialog |
| Ctrl+Enter | Generate pending captions |
| Esc | Cancel a running batch after the current model operation |
| Ctrl+E | Export results |
| F6 / Shift+F6 | Move between the image queue and editable caption |
| Enter in the queue | Focus the selected caption when it is editable |
| Tab / Shift+Tab | Move to the next / previous enabled control |
| Arrow keys | Select queue rows or caption length |
| Space | Activate a focused button or checkbox |
| F1 | Show keyboard help |

Tab leaves the caption editor without inserting a tab. Normal text selection, copy,
paste, and undo retain Tk's bindings. The editor has a visible focus border and a
Caption text (editable) label. Buttons retain descriptive text; the queue has Image
and Status headings. These labels do not establish screen-reader compatibility.

Shortcuts respect disabled controls. Save/Open/Add remain disabled during generation;
export is available once results exist. Esc does nothing while idle and does not
close the app. Native file dialogs keep their own keyboard behavior.

Newly added images and successfully opened sessions focus the selected queue row.
If generation disables the focused control, focus moves to Cancel batch; cancellation
or completion returns disabled-control focus to the queue. A batch completing while
you edit another caption leaves your focus in the editor. Clearing returns to Add
images. Existing save/discard/cancel and recovery protections still apply.

## Verification boundary

Automated Windows Tk tests use real mapped widgets and generated key events.
A fake captioner and stubbed file-dialog responses keep tests local and deterministic.
The tests cover keyboard-driven add, generate, edit, export, session save/open, queue
arrows, both Tab directions, F6, help, folder selection, busy states, cancelled
replacement, modal grabs, and undo. They also check that every interactive control
remains mapped and inside the client height at the 960 by 680 minimum window size.

These checks do not replace a person's keyboard-only walkthrough, testing native
file-dialog navigation, screen-reader announcements, high-contrast mode, high-DPI
layouts, or manual visual acceptance. Those observations belong to LC11.

## Manual walkthrough for LC11

1. Start the source app. Use Tab and Shift+Tab to reach each enabled control.
   Check that focus is visible and labels make sense with Windows assistive technology.
2. Use Ctrl+I and navigate the native file dialog using only the keyboard. Add two
   local test images, move between them with arrows, and start with Ctrl+Enter.
3. Cancel with Esc, then generate remaining rows. Confirm focus stays usable during
   progress and that completed captions remain available.
4. Press Enter on a captioned queue row. Edit, undo, select/copy/paste, and use Tab
   in both directions without inserting unwanted whitespace.
5. Export with Ctrl+E, save with Ctrl+S, and reopen with Ctrl+O. Change a caption
   and cancel the replacement prompt; verify the edit remains.
6. Record the Windows version, display scaling, assistive technology/version,
   observed announcements/focus/errors, and any fixes needed. Do not record a pass
   until a tester has actually performed the walkthrough.
