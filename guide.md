# BG vs Overlay Sifter: Guide

## Quickstart

1. Unzip the folder anywhere and run `BG vs Overlay Sifter.exe`. The settings panel opens by itself the first time.
2. Under **Backgrounds**, choose your folder of background images. Press Browse, or paste a path and press Enter.
3. Under **Overlays**, optionally choose your folder of finished overlay images.
4. Press **Esc** to close the panel.
5. Flip with **A / D**, change overlay with **W / S**, and press **R** on any background you want moved out.

Next time you open the program, it goes straight back to where you were.

## Keys

| Key | Action |
|---|---|
| A / D or Left / Right | Previous / next background |
| W / S or Up / Down | Previous / next overlay, including a "no overlay" step |
| R | Move the background on screen to the target folder |
| Ctrl+Z | Undo the latest move. Works many times, until you close the program |
| Tab / Shift+Tab | Cycle background mode: Fill, Fit, Stretch, Tile, Centre |
| F11 | Fullscreen, with no filename label or mouse cursor, for a clean screenshot |
| Esc | Show or hide the panel, or leave a text field |
| Left-click the image | Open the panel, or leave a text field |
| Alt+F4 | Quit. Esc never quits |

Hold a flip key to run through images. R, Ctrl+Z, Tab, F11 and Esc ignore holding, so holding R can never dump a run of files.

## Good to know

**Where moved files go.** To a `rejects` folder inside your backgrounds folder, created on the first move, unless you choose another folder. It works just as well in reverse: press R on the ones you like and treat that folder as your favourites.

**Nothing is overwritten.** If a name is already taken, the file becomes `foo (2).jpg`. This is also true when you undo.

**Subfolders are not included.** Only the images directly inside your backgrounds folder count, so moved files cannot cycle back in.

**Overlays are finished images.** Prepare each one elsewhere as a single picture, with transparency where the background should show through. Overlays stay at their real size and are cropped at the canvas edge. Their position setting applies to all of them.

**The canvas.** By default it takes its size from the overlay showing, or from the background if no overlay is showing. To test a specific size, set Canvas to Preset or Custom in the panel. A small overlay such as a title usually needs this, because otherwise the canvas shrinks to the title's size.

**Editing in another program.** Save your edit and come back to the window. The program re-reads its folders by itself, so the change and any new files appear.

**Formats.** JPG, PNG, WebP, BMP and GIF. An animated GIF shows its first frame. A file that cannot be read shows a placeholder and says "(unreadable)" rather than stopping the program.

**Saving a picture.** The program does not export images. Press F11 and use your usual screenshot tool.

**Settings** are remembered in `config.json`, next to the program. Delete it to start over.

**Hover over anything in the panel** for an explanation of what it does.

## Contact

mailto:reactorcoregames@gmail.com

---

Check out everything else I do: ✨🚀

https://linktr.ee/reactorcore

https://reactorcore.itch.io/

-Reactorcore

---

My other links:
Home/Links: https://linktr.ee/reactorcore
Releases: https://reactorcore.itch.io
Blog: https://www.patreon.com/ReactorcoreGames
Discord: https://discord.gg/UdRavGhj47
Catalog: https://reactorcoregames.github.io/
