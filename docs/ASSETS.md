# The package tiles

A UWP package needs eleven images. **This repository ships none of them**: the ones used on the
real console were cut from the game's own artwork, which belongs to Capcom, and that is exactly
what [`NOTICE.md`](../NOTICE.md) promises not to distribute. You supply your own.

`tools/empaquetar-uwp.ps1` reads the names straight out of `package/Package.appxmanifest` and
stops before packaging if any is missing, naming the ones it could not find.

## What to put in `package/Assets/`

| File | Size |
|---|---|
| `SplashScreen.png` | 620 × 300 |
| `SplashScreen.scale-200.png` | 1240 × 600 |
| `Square150x150Logo.png` | 150 × 150 |
| `Square150x150Logo.scale-200.png` | 300 × 300 |
| `Square44x44Logo.png` | 44 × 44 |
| `Square44x44Logo.scale-200.png` | 88 × 88 |
| `Square44x44Logo.targetsize-24_altform-unplated.png` | 24 × 24 |
| `StoreLogo.png` | 50 × 50 |
| `StoreLogo.scale-200.png` | 100 × 100 |
| `LockScreenLogo.png` | 24 × 24 |
| `LockScreenLogo.scale-200.png` | 48 × 48 |

PNG, 32-bit with alpha. The sizes are not advisory: a tile of the wrong size makes `makepri`
produce a resource index the console will not accept.

## The quickest way to have something that works

Any eleven plain images of those exact sizes will do — the console only needs them to exist and
to be the right shape. One line with ImageMagick, if you have it:

```sh
for s in 620x300 1240x600 150x150 300x300 44x44 88x88 24x24 50x50 100x100 24x24 48x48; do :; done
# or, one at a time:
magick -size 620x300 xc:"#1b1b1f" package/Assets/SplashScreen.png
magick -size 150x150 xc:"#1b1b1f" package/Assets/Square150x150Logo.png
# …and so on for the rest of the table
```

Replace them with real art whenever you like: nothing else in the build depends on them.

## If you do make artwork

Keep it yours. Screenshots, logos, character art and fonts from the game belong to their
owners, and a package that carries them is a package you cannot share.
