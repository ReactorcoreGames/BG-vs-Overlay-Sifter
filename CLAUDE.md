# BG vs Overlay Sifter

A desktop app for flipping prepared overlay images over many backgrounds and sorting out the backgrounds. General-purpose, not tied to any other Reactorcore project.

Run it with `.venv/Scripts/python.exe main.py`, and the tests with `.venv/Scripts/python.exe -m pytest tests/ -q`. Build the release with `build_release.bat`. `.venv` is not kept with the project: if it is missing, the steps to recreate it are at the top of `requirements.txt`.

**`docs/spec.md` is the spec and wins on any conflict**, including with this file. It holds each decision with its reasoning, the key list and the out-of-scope list. Read it before changing behaviour, and record any behaviour change in it.

## Folder layout

```
core/                 Pure Python + Pillow. No Qt, ever. Placement maths, compositing, the file moves, config.
gui/                  The only Qt-dependent part. app (state), keys, frames (workers), view, panel, theme.
tests/                Offline over core/, offscreen over gui/, and the release check.
docs/                 The spec, plus the test material, which is gitignored.
assets/               icon.ico, its source art icon_og.jpg, and the placeholder for an unreadable background.
licenses/             LGPL and GPL texts and the third-party notices. Copied into the release.
promo/                Stamped screenshots, thumbnail and cover. Shipped in the release zip.
promo_source/         Clean captures that promo/ is stamped from. Committed, never shipped.
make_promo_images.py  Rebuilds promo/. --screenshots retakes the captures.
make_trailer.py       Builds the YouTube trailer. --capture retakes its frames from the real window.
trailer/              The trailer's music, and its gitignored frames and video. Never shipped.
promo.md              Store copy and marketing notes. Internal, never shipped.
build_release.bat     Runs the tests, then build_release.spec, then release_package.py.
build_release.spec    The PyInstaller recipe, and the list of what is stripped from the build.
release_package.py    Assembles the release folder, checks it, zips it, checks the zip.
config.json           Every setting, global. Created on first run, gitignored. The only file the program saves.
old wip/              Gitignored history, including v2. Nothing current may depend on it.
```

**Test material is real, not synthetic:** `docs/testing BGs` (42 backgrounds, 1536x864) and `docs/testing UIs` (two full-screen 1920x1020 overlays and one 700x140 title). It is gitignored, so the tests that need it skip on a fresh clone. Tests must work on temporary copies, because R really moves files.

## Hard constraints

These are the ones that are easy to violate while the violation looks reasonable.

**The scope is the point.** Before adding anything, check the out-of-scope list and the scope rule in the spec. If something there seems necessary, say so and stop. The scope limits features, not lines: there is no line limit, and code that polishes or tightens the program is welcome.

**`core/` imports no Qt.** A test enforces it.

**Nothing decodes or renders on the UI thread during a flip.** The UI thread uses `FrameRenderer.peek` and `request` only. Flip speed is the product, and a test guards this.

**Never overwrite a file, in either direction.** `unique_destination` is used for moves and for undo. Silently destroying a file is the one unrecoverable thing this tool could do.

**The background scan is flat, never recursive.** The rejects folder usually lives inside the background folder, so a recursive walk cycles rejects back into the rotation.

**R moves what is on screen, never the cursor's image, and never on key repeat.** During a fast flip these differ. Moving the cursor's image would move a picture nobody has looked at.

**Esc never quits.** Quit is Alt+F4 and nothing else.

**Global keys go through the app-level event filter, and typing in a panel field must not trigger them.**

**The public zip holds only the program, `guide.md`, `readme.md`, `LICENSE`, `licenses/` and `promo/`.** `release_package.py` fails the build otherwise. A new file that should ship must be added to its `TOP_LEVEL` list deliberately.

**Nothing gets uploaded, pushed or published without the owner's say. Never write a specific price into the promo copy.**

## Traps

All of these are invisible to the offscreen tests.

Appearance:

- The offscreen platform reports zero fonts, so text there proves nothing. Verify appearance on the real platform with `QScreen.grabWindow`, not `QWidget.grab()`, which does not composite overlay children as the screen does.
- Segoe UI carries no arrows, triangles or emoji, and the stylesheet suppresses font substitution, so a decorative glyph on a control draws as nothing. Use words.
- A fixed widget size under its own `sizeHint()` clips the text to nothing, silently.
- `deleteLater()` does not unparent. A widget scheduled for deletion keeps painting until the event loop reaches it, so call `setParent(None)` first when rebuilding a row in place.

The build:

- Stripping fails at runtime, not at build time. Pillow's GIF plugin imports `ImageMath`, so stripping `_imagingmath` made every GIF show as unreadable, with no error. After changing `UNUSED` in the spec, flip through one file of every format in the frozen build and look at the pictures. A test guards the Pillow half.
- PyInstaller uses UPX by itself if it is on PATH, and it is on this machine. The spec turns it off, because UPX-packed Qt DLLs are a known cause of antivirus false positives.
- PySide6's wheels carry only `LicenseRef-Qt-Commercial.txt`, not the LGPL. That is why `licenses/` holds the GNU texts, and why the release check refuses the commercial file.
- `guide.md` and `readme.md` name `BG vs Overlay Sifter.exe`, so renaming the build means changing them too. A test checks this.

Driving the real window from a script:

- Never wait with `QTest.qWait` while frames are rendering. It starves the render threads, and a first frame took about 12s under it against about 0.55s in a real event loop. It looks exactly like a slow program. Use `QEventLoop` with `QTimer.singleShot`.
- The venv's `python.exe` is a launcher, so `Popen(...).pid` is not the process that owns the window. Have the child write `os.getpid()` to a file, and kill with `taskkill /F /T`. The frozen exe does not have this problem.
- A posted `WM_SYSKEYDOWN` does not close the window, because Qt reads the live Alt state. Real Alt+F4 and Ctrl+Z need `SendInput`, as one atomic batch, checked right before that the program's window is in front, so it cannot hit another app.
- With no saved geometry the window starts maximized. Restore it before moving it, or the move is not what gets saved.
- At 125% scaling a restored window can come back 1 physical pixel wider, once. This is rounding, not a bug.
- `make_promo_images.py --screenshots` keeps its demo copy at `C:\Sifter demo`, because the panel prints folder paths and a temp folder would put the Windows account name in a public image.

## Working in this folder

- There may be no git history to fall back on until the owner has loaded the project into GitHub Desktop, so do not run `git init`, and never send a move or archive in the same batch of tool calls as writes that depend on it.
- Permanent deletes are blocked by a hook. Move things to `C:\trash` instead.
- Markdown prose is never hard-wrapped. One paragraph, one line.
- Ask before inventing anything the spec does not cover.
- The release procedure is `C:\ClaudeWorkspace\RC prompt to make releases easier.md`.
