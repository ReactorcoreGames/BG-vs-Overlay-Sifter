# Third-party notices

BG vs Overlay Sifter's own code is under the MIT license, in `LICENSE`. The release also contains the parts below, which keep their own licenses.

## Qt and PySide6 {PYSIDE6}

Qt for Python (PySide6, shiboken6) and the Qt libraries are copyright The Qt Company Ltd. and other contributors, and are used here under the GNU Lesser General Public License version 3. Its text is in `LGPL-3.0.txt`, and the GNU General Public License version 3 that it builds on is in `GPL-3.0.txt`.

They are unmodified, and are the separate DLL and PYD files in `_internal/PySide6` and `_internal/shiboken6`. You may replace them with your own compatible versions. Parts of Qt this program does not use are left out of the release.

Source code for PySide6 and Qt:

- https://code.qt.io/cgit/pyside/pyside-setup.git/
- https://code.qt.io/cgit/qt/qtbase.git/
- https://download.qt.io/official_releases/QtForPython/

Qt contains third-party components under their own licenses, listed at https://doc.qt.io/qt-6/licenses-used-in-qt.html

## Pillow {PILLOW}

Used under the MIT-CMU license, in `Pillow-LICENSE.txt`, which also covers the libraries Pillow bundles.

## Python {PYTHON}

The Python runtime is used under the PSF license, in `Python-LICENSE.txt`.

## PyInstaller

The program is packaged with PyInstaller. Its bootloader, which is part of the `.exe`, is under the GPL with an exception that allows it to be distributed with programs under any license. See https://pyinstaller.org/en/stable/license.html
