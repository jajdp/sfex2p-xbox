# Put your eleven package tiles here

This folder is **empty on purpose**. The tiles used on the real console were cut from the
game's own artwork, which belongs to Capcom, so they are not distributed here — see
[`../../NOTICE.md`](../../NOTICE.md).

The names and exact sizes are in [`../../docs/ASSETS.md`](../../docs/ASSETS.md). Plain colour
images of the right dimensions work fine; the console only needs them to exist and to be the
right shape.

`tools/empaquetar-uwp.ps1` reads the names out of `../Package.appxmanifest` and stops before
packaging if any is missing, telling you which. `.gitignore` keeps `*.png` in this folder out
of the repository, so whatever you put here will not be committed by accident.
