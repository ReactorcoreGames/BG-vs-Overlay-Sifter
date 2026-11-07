# v3 spec

This is what the program is and why, written as decisions with their reasoning. It wins on any conflict, including with `CLAUDE.md`.

## The point

v2 grew so much setup that it lost what made the first prototype good: you opened it and you were already flipping through backgrounds. v3 exists to get that back. It is a BG tester and sorter, and nothing else. Overlays are composited elsewhere beforehand.

## The workflow

Choose three folders: backgrounds, overlays, and where moved files go. Then flip through BGs and overlays, and press R on the BGs to sort out. Later launches go straight back to where you were, with the panel closed.

| Key | Action |
|---|---|
| A / D or Left / Right | Previous / next BG, wrapping |
| W / S or Up / Down | Previous / next overlay, wrapping |
| R | Move the BG on screen to the target folder |
| Ctrl+Z | Undo the latest move |
| Tab / Shift+Tab | Cycle BG mode |
| F11 | Fullscreen |
| Esc | Show or hide the panel |
| Left-click the canvas | Open the panel, and take focus out of any panel field |
| Alt+F4 | Quit |

## Decisions

**Five BG modes: Fill, Fit, Stretch, Tile, Centre.** Windows' Span is left out. It stretches a wallpaper across several monitors, so on one canvas it looks identical to Fill and Tab would appear to do nothing on that step.

**The canvas is Match overlay, a preset, or custom, and defaults to Match overlay.** Real overlays and BGs often fit no preset: the test material is 1920x1020 and 1536x864. Taking the canvas from the overlay is what the prototype did. With no overlay showing, the canvas takes the BG's size. If overlays in a folder differ in size, the canvas changes as you press W/S; that is accepted.

**Presets name the short edge**, from 360p to 1080p, so 9:16 at 1080p is 1080x1920.

**Anchor and offset are global, not per overlay.** Per-overlay settings would mean saving data per file, which starts rebuilding the layout system v3 exists to remove. Overlays are expected to be finished composites.

**Overlays never scale.** They stay at native pixels and crop at the canvas edge.

**The view always fits the window, with no zoom or pan.**

**W/S includes a "no overlay" step**, so a BG can be judged by itself and an empty overlay folder still works. It starts on the first real overlay.

**R only moves BGs.** Overlays are authored and curated, so a second sorting target would only add a mode to keep track of.

**R moves what is on screen, and does nothing if that has already been moved.** During a fast flip the cursor can be ahead of the picture. What you see is what moves, and an image nobody has looked at never does.

**R ignores key repeat, and so do Ctrl+Z, Tab, F11 and Esc.** R sits next to D, and holding it must not dump a run of images. Flipping does repeat, because holding the key is the point of flipping.

**Undo works many times, for the current run only, and each file returns to its old list position.** Keeping history across restarts would mean handling files that have since moved.

**Nothing is ever overwritten, in either direction.** Collisions count up Explorer-style, as `foo (2).jpg`. The target folder cannot be the BG folder.

**The target folder defaults to `<BG folder>/rejects`, and the scan is flat, never recursive**, so rejects cannot cycle back into the rotation. The UI says "move" rather than "reject", because it may equally hold favourites.

**Resampling is global: Lanczos (smooth, the default) or Nearest (crisp).** It applies to both resampling steps, BG to canvas and canvas to window, so Nearest stays crisp on screen. Fit to window can still land on a fractional scale, so Nearest is crisp rather than strictly pixel-perfect.

**F11 is fullscreen only; Esc toggles the panel.** Hiding the panel and going fullscreen are separate actions. The app starts with the panel closed, unless there is no BG to show. The filename label and the mouse cursor hide in fullscreen, so a screenshot comes out clean.

**Every empty state says what to do, and left-clicking the canvas opens a closed panel, with or without an image showing.** With the panel closed and Esc forgotten, the screen otherwise gave no way forward, and fullscreen has no title bar to carry a hint. The hint shows only while the panel is closed, because it would be wrong otherwise. A click only ever opens: with the panel already open it does not close it, since clicking away from a field is normal while adjusting settings. It does take focus out of the field, so the global keys come back.

**The panel slides over the image rather than pushing it**, so opening it never resizes or re-renders what is being judged.

**Typing in a panel field never triggers shortcuts.** An "r" typed in a path must not move a file. Enter or Esc leaves the field.

**Coming back to the window re-reads the folders and drops rendered frames**, so new files and edits made in another program show up by themselves. The cost is one tap of about 100-160ms, if a key is pressed before the neighbours are rendered again. The launch's own activation does not count as coming back. This was added during the build rather than asked for, because editing an overlay elsewhere and coming back is the expected way of working.

**Bad files degrade rather than crash.** An unreadable BG shows `assets/missing image error.jpg`, an unreadable overlay is left off, and the label says "(unreadable)".

**The panel side wears a watermelon theme taken from the icon art; the surround stays neutral.** The grey scheme was dull, and the panel is what the theme is for: the panel, toast, tooltips, combo popups and the colour dialog. The image, the area around it, the filename label and the empty-state text stay neutral, because they sit against what is being judged and a tint would change how it reads. The colour dialog is Qt's own rather than the native one, because the native one cannot wear the theme. `tests/test_theme.py` measures every pairing.

**Every control in the panel has a tooltip**, so the program explains itself to someone who has never read the guide. This follows the Reactorcore standard. Their text lives in `TIPS` in `gui/panel.py`.

**The release is a one-folder build, not a single exe, with the parts of Qt and Pillow the program never touches left out.** One folder starts faster, since nothing unpacks on launch, and keeps the Qt libraries as separate replaceable files, as the LGPL expects. Their license texts and source links ship in `licenses/`. `config.json` is written beside the exe. What ships is an explicit list, and the build fails if anything else appears, because the project folder holds files that must never reach the public zip.

**PySide6 stays, rather than going back to tkinter/ttkbootstrap.** Qt was first chosen for the builder, and that reason is gone. It stays because flip speed is the product and it makes the sliding panel easy. This remains outside the Reactorcore tkinter house standard, on purpose.

## Out of scope, permanently

Saving or exporting images (use F11 and a screenshot tool), contact sheets, the builder, layouts, sessions, per-overlay settings, favourites as a separate concept, zoom and pan, drag-and-drop.

**The scope rule:** anything needing a dialog beyond a folder or colour picker, or a saved file other than `config.json`, needs an explicit decision from the owner first. It limits features, not lines: there is no line limit, and code that polishes the program or makes it easier to use is welcome. `test_no_refused_features_crept_in` guards the out-of-scope list.

## How it works

One render path, as in the prototype: composite at canvas resolution with Pillow, then resample to the window. Worker threads do this; the UI thread only paints finished frames. v2's rule of compositing at display scale with QPainter is gone, because nothing here is dragged live.
