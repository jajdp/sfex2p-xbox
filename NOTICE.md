# Notice

*(Español: [NOTICE.es.md](NOTICE.es.md))*

## Not affiliated

This is an unofficial, noncommercial fan project. It is **not affiliated with, endorsed by or
connected to Capcom, Arika, Sony or Microsoft**, or any of their subsidiaries, nor to the
authors of the [PSXRecomp](https://github.com/RetroPortingToolKit/psxrecomp) framework or of the
[game project](https://github.com/strider973/Street-Fighter-EX2-Plus-Recompiled) this port is
built on. *Street Fighter*, *Street Fighter EX2 Plus*, *Xbox* and all related names and marks
are the property of their respective owners, and are used here only to say what this works with.

Nothing here is for sale, and nothing here is monetized.

## What this repository does not distribute

No game code. No disc image. No BIOS. No built executable. No `.msix` package. No save data. No
artwork, audio, music or fonts from the game — not even the package tiles, which is why
`package/Assets/` is empty and [`docs/ASSETS.md`](docs/ASSETS.md) asks you to supply your own.

Nothing here produces a playable game on its own. You need your own legally dumped copy of the
disc, a retail BIOS, and a working build of the game project, none of which this repository
provides or can provide.

## What it does contain of other people's work

**Patches against the PSXRecomp framework.** The sixteen patch scripts — all the patching code
there is here — quote **117 lines** of the framework's source in total: the anchors each patch
checks before writing, so that it fails safely instead of corrupting a tree it does not
recognise. PSXRecomp is published by its author under the
PolyForm Noncommercial License 1.0.0, which permits noncommercial derivative works; this
repository is such a derivative, and is released under [that same license](LICENSE) — the
canonical text from polyformproject.org, which is what the `PolyForm-Noncommercial-1.0.0`
identifier names. The copy the framework distributes is an abridged variant of it.

**Zero lines from the game project.** `strider973/Street-Fighter-EX2-Plus-Recompiled` carries no
license, so nothing of it is reproduced here. The installer anchors itself on CMake's own
parameter names and appends its block at the end of the file, which needs no anchor at all.

**`src/SDL_winrt_main_NonXAML.cpp`** is SDL's WinRT entry point, *placed in the public domain by
David Ludwig*, with the changes this port needed (the package's temp directory, the data folder
it seeds on every boot, and the log redirection). The original is part of
[SDL](https://github.com/libsdl-org/SDL).

**There are no screenshots here at all.** The one that used to be — the game's title screen on a
console — is mostly Capcom's logo and trademark, so it was removed. A screenshot would earn its
place by showing the work; that one showed someone else's artwork.

## Takedown and contact

If you hold rights in this material and want something here removed or changed, write to
**jajdpmail@gmail.com**, saying what you object to and in what capacity you are writing.

Requests from rights holders are honoured: the disputed part is removed, or the repository is
taken down, without argument, and you will get a reply confirming it. No notice or legal
process beyond that email is needed to reach the person who maintains this.
