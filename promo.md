# BG vs Overlay Sifter: Promo notes

Internal document. It stays out of the release zip.

## Strategy

### What this is, honestly

A small, sharp Windows tool for one job: you have a folder of backgrounds and one or more finished overlays, such as a game HUD, a title or a menu, and you want to see which backgrounds work behind them. You flip with the keyboard and move the bad ones out with one key.

It is a niche tool. The people who need it will recognise the problem immediately, and most other people will not. The goal is to be findable by the first group, not to persuade the second.

### Who wants it

- **Game developers and modders** choosing backgrounds to sit behind a HUD, menu or title. This is the use the program grew out of, and the real test material comes from it.
- **People generating images in bulk.** A batch run leaves hundreds of backgrounds to sort through, and this is the step after that. It is the natural link to Batch AI Image Generator.
- **Anyone doing the same job with other overlays,** such as stream overlays, video thumbnails, title cards or wallpaper layouts. This is plausible rather than proven, so test it before leaning on it.

### The hooks, strongest first

1. **It answers the question directly.** "Which of these backgrounds works behind my UI?" The usual way is a stack of layers in an image editor, toggled one at a time.
2. **You open it and you are already flipping.** Choose three folders once, and later launches go straight back to where you were with the panel closed. This is the reason the program was rebuilt, so it is the true story to tell.
3. **It is safe to go fast.** R moves what is on screen, not what the cursor has reached. Holding R does nothing extra, Ctrl+Z works many times, and files are never overwritten.
4. **It keeps up with your editing.** Save an overlay in another program, come back to the window, and the change is already there.

### Against the obvious question

Someone will ask "why not just use an image viewer?" There are many good keyboard sorters already, including PhotoSift, Image Sort, Picsort and Turbo Photo Sorter, and several sort into many folders where this has one target. Do not compete with them on sorting. The difference is the overlay: **this shows every background behind your actual UI while you decide.** If someone has no overlay to test, one of those tools may suit them better, and saying so plainly reads well.

### What not to claim

- No speed numbers without measuring on the machine being described. "Flips instantly" should stay about what the user feels. A first tap after coming back to the window can take about 100-160ms while frames re-render.
- Tested on Windows 11 only. "Windows 10 or 11" comes from what its dependencies support, not from a test on Windows 10.
- It does not export images, make layouts or edit anything. The feature list is short on purpose, and that is part of the pitch.

### Business model: decided

**Free, with pay-what-you-want on itch, and the MIT source code on GitHub.** The purpose is traffic: bringing people to your catalog and to Commander Wars. Revenue is a bonus. No amounts are named anywhere, and the suggested donation on itch is yours to set.

PySide6 is LGPL-3.0, so Session 3 needs to ship its notices.

### Before posting

- **Commander Wars in the images is deliberate.** It shows the program at its best and points people to the game. You made the backgrounds and overlays, and the descriptions link to https://commander-wars.pages.dev/.
- **The GitHub link does not exist yet.** The itch description below has a marked line to fill in or cut.
- **AI disclosure.** itch's browse pages have an AI filter, so expect to be asked about it on upload. The icon art was AI-generated in Session 1, so answer with that in mind. Do not use the "No AI" tag.
- **Upload the thumbnail as the cover image.** itch will not index a page without one, and a new seller's first project can wait in a review queue. Your account probably passed that long ago.

## itch.io

### Name of project

BG vs Overlay Sifter

### Subtitle

Flip overlays over a folder of backgrounds, see what works, and sort the rest out with one key.

### Long description

```markdown
# Which backgrounds actually work behind your UI?

You have a folder of backgrounds. You have a HUD, a menu or a title. Normally you find out which ones go together by toggling layers in an image editor, one at a time.

**BG vs Overlay Sifter** puts your overlay on top and lets you flip through the lot with the keyboard. When a background does not work, press R and it is gone from the rotation. Next.

## How it works

1. Choose your folder of backgrounds.
2. Choose your folder of finished overlays.
3. Flip. Sort. That is the whole program.

Later launches go straight back to where you were, with the panel out of the way.

## Keys

- **A / D** or **Left / Right:** previous / next background
- **W / S** or **Up / Down:** previous / next overlay
- **R:** move this background to your target folder
- **Ctrl+Z:** undo, as many times as you need
- **Tab:** cycle Fill, Fit, Stretch, Tile and Centre
- **F11:** fullscreen, clean enough for a screenshot
- **Esc:** show or hide the settings panel

## Built so you can go fast without worrying

- **R moves what you are looking at,** not whatever the cursor has reached mid-flip.
- **Holding R does nothing extra,** so one slip cannot throw away a run of images.
- **Nothing is ever overwritten.** A name clash becomes `foo (2).jpg`, in both directions.
- **Rejects cannot cycle back in,** because subfolders are not scanned.
- **It can work in reverse.** Press R on the ones you love and treat the folder as your favourites.

## Handy details

- Test any canvas: match the overlay, pick a preset shape and size up to 1080p, or type your own.
- Place overlays with a 9-point anchor and a pixel offset.
- Lanczos for paintings and photos, Nearest for pixel art.
- Edit an overlay in another program, come back to the window, and the change is already there.
- Hover over anything in the panel for an explanation.

## What it deliberately does not do

No layouts, no exporting, no projects to set up. Prepare your overlays elsewhere. This program is for the part where you decide.

## Requirements

Windows 10 or 11. Nothing to install: unzip and run.

Free to download, and pay what you want if it helps you. MIT licensed. [ADD THE GITHUB LINK ONCE THE REPO EXISTS, OR CUT THIS LINE]

## See it in action

The screenshots show overlays I made from **Commander Wars**, a game I have made a lot of mods for. It is well worth a look: https://commander-wars.pages.dev/

---

Made by Reactorcore: https://linktr.ee/reactorcore
```

### Tags

user interface, graphics, backgrounds, wallpaper, 2d, game development, sorting, open source, utility, image viewer

## GitHub

### Description

Flip finished overlay images over a folder of backgrounds, see which ones work behind your UI, and sort the rest out with one key. Windows desktop app. Shown with Commander Wars: https://commander-wars.pages.dev/

### Topics

image-sorter
image-viewer
backgrounds
overlay
game-ui
game-development
gamedev-tools
pyside6
python
windows

## YouTube

The video is `trailer/BG vs Overlay Sifter - trailer.mp4`, built by `make_trailer.py`. Use `promo/cover_1280x720.jpg` as its thumbnail.

The music credit below is what its CC BY 4.0 license requires, so keep it in the description. The trailer uses the opening of the track, faded out and with its volume raised, which the credit says.

### Title

BG vs Overlay Sifter: which backgrounds work behind your UI?

### Description

```text
BG vs Overlay Sifter puts your overlay on top of a folder of backgrounds and lets you flip through them with the keyboard. When one does not work, press R and it is gone from the rotation. Ctrl+Z brings it back. For Windows.

Get it here: https://reactorcore.itch.io/

The overlays shown are from Commander Wars: https://commander-wars.pages.dev/

Made by Reactorcore: https://linktr.ee/reactorcore

Music: "Prelude No. 2" by Chris Zabriskie, licensed under Creative Commons Attribution 4.0: https://creativecommons.org/licenses/by/4.0/
Source: http://chriszabriskie.com/preludes/
Artist: http://chriszabriskie.com/
The track is shortened, faded out and raised in volume for this video.
```

## Where to post

These are all places that keep working after the day you post. Reddit was not checked, because it blocks bots.

1. **itch.io Tools browse pages.** This is the main one, since tags keep bringing people in. "User Interface (UI)" had 763 results and "wallpaper" 89 when checked, so the second is the smaller pond to stand out in. https://itch.io/tools/tag-user-interface
2. **AlternativeTo.** A long-lasting listing, found by people already comparing tools. It has an "Image sorting" feature page, and you can suggest the program as an alternative to specific apps there. Be honest about which apps it really replaces. One third-party review says new accounts wait seven days and submissions are reviewed, and I could not confirm the wait. https://alternativeto.net/feature/image-sorting/
3. **Your own Batch AI Image Generator page.** A one-line "sorting what it made?" link, and the same in reverse. It is the warmest audience you have, and you control the placement.
4. **itch.io Release Announcements board.** A one-time post, but it stays up. It needs a link, a summary and an embedded image, and low-effort posts get removed. The recent posts I saw were mostly games and asset packs, so expect a modest response. https://itch.io/board/10022/release-announcements
5. **discuss.pixls.us, Software category.** A photography forum with precedent: a keyboard-first sorter was posted there in September 2026. The first reply asked for a license on the repo before discussing it, so post only once the MIT repo is public. It is the weakest fit here, because its members sort photos rather than test overlays. https://discuss.pixls.us/t/i-built-a-simple-keyboard-first-tool-for-sorting-large-photo-video-folders/60671

Checked and left out: `awesome-GameDev-tool` on GitHub accepts pull requests and has a fitting category, but it showed 0 stars when checked, so it is unlikely to send anyone yet.
