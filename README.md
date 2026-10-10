# Street Fighter EX2 Plus on Xbox — the UWP port

How to take the [PSXRecomp](https://github.com/RetroPortingToolKit/psxrecomp) static recompilation of
*Street Fighter EX2 Plus* (PlayStation, 1999, `SLUS-01105`) and run it **on an Xbox Series in Developer
Mode**, as a UWP package you build and sign yourself.

*(Español: [README.es.md](README.es.md))*

It is not a theory: the game boots, goes through the BIOS and the Capcom presentation, reaches the title
screen and plays with a controller, in 16:9, at **60 FPS**, and it comes back where you left it after the
console suspends it.

## What this repository is

**A recipe and the tools that apply it.** The game's framework has no UWP support at all, so the port is a
profile built from scratch: a CMake profile for `WindowsStore`, a WinRT entry point, and a set of guarded
patches for the things that an App Container does not allow. Everything here is applied **to your own
checkout** of the game project, on your machine.

## What this repository is **not**

It contains **no game code, no disc image, no BIOS, no built executable, no `.msix` package and no
artwork**. It cannot produce a playable game on its own, and nothing you can download here is a game. You
need your own legally dumped copy of the disc, a retail BIOS, and a working build of the game project
first. See [`NOTICE.md`](NOTICE.md).

The eleven package tiles are **not** in here either: the ones used on the real console were made from the
game's own art, which is Capcom's. You supply your own — [`docs/ASSETS.md`](docs/ASSETS.md) lists the exact
sizes, and the packer stops with a clear message if any is missing.

## What you need first

| | |
|---|---|
| The game project | [strider973/Street-Fighter-EX2-Plus-Recompiled](https://github.com/strider973/Street-Fighter-EX2-Plus-Recompiled) on the [PSXRecomp](https://github.com/RetroPortingToolKit/psxrecomp) framework, cloned with `--recurse-submodules`, **building and running on your PC first** |
| Your own disc | An NTSC-U dump of `SLUS-01105`, plus a **retail SCPH-1001 BIOS** — the game project ships `openbios = false`, so the bundled OpenBIOS will not do |
| Visual Studio 2022 | With the C++ tools and the **UWP** workload, plus Ninja and the Windows 10/11 SDK |
| An SDL2 built for WindowsStore | SDL3 has no WinRT backend. 2.30.2 is what this was built and tested with |
| An Xbox in Developer Mode | And a certificate to sign with — a self-signed one is fine ([`docs/INSTALL.md`](docs/INSTALL.md) §3) |

## How it goes

```powershell
# 1. patch your checkout of the game project (idempotent, atomic, nothing is deleted)
python tools/apply_uwp.py <path-to-game-project-root>

# 2. configure and build with Ninja inside the UWP toolchain
pwsh -File tools/configurar-uwp.ps1 -Raiz <project> -Build <build> -Sdl2 <SDL2 cmake dir> -Compilar

# 3. package and sign (your own tiles, your own certificate)
pwsh -File tools/empaquetar-uwp.ps1 -Build <build> -Juego <project> -Salida <out> -Certificado <thumbprint>
```

Then install the `.msix` through the Device Portal and upload your disc and BIOS to the app's `LocalState`.
Step by step, including the console side: **[`docs/INSTALL.md`](docs/INSTALL.md)**
([en español](docs/INSTALL.es.md)).

## What it had to solve

Every one of these was a real failure on the console, and each one hid the next. The detail, with what the
log said in each case, is in **[`docs/HOW-IT-WORKS.md`](docs/HOW-IT-WORKS.md)**.

| | Symptom | Fix |
|---|---|---|
| 1 | `Failed to launch the application` | Six separate causes: a desktop `OPENGL32.dll` import, the desktop CRT, a missing VCLibs dependency in the manifest, fibers and job objects the App Container forbids, the runtime anchoring its files in a read-only folder, and a GL context still being requested after falling back to software |
| 2 | Mods silently refused | The framework validates mod packages — and the disc hash each one demands — *before* it resolves where the disc is |
| 3 | No controller | With no launcher to assign devices, player 1 defaults to the keyboard, and there is no keyboard on a console |
| 4 | 51–55 FPS in 16:9 | The software rasteriser drew every primitive twice. The centre of the wide surface is a 1:1 copy of VRAM, so it does not have to be drawn again: **60 sustained** |
| 5 | Starting over after Home | Developer Mode terminates a suspended game. The machine state is saved every 10 seconds and restored on relaunch |
| 6 | Nothing was ever saved | `memcard_dir` is relative, and resolved against the read-only install folder — both memory cards and every save state |

## The mods are separate

The 16:9 and the Spanish menus are their own repositories, and the packer takes them with `-Mod`:

- [jajdp/sfex2p-widescreen](https://github.com/jajdp/sfex2p-widescreen) — real 16:9
- [jajdp/sfex2p-es](https://github.com/jajdp/sfex2p-es) — Spanish menus

## Credits and license

Port and tooling by **Recompilaciones**. Released under the
[PolyForm Noncommercial License 1.0.0](LICENSE), matching the license of the PSXRecomp framework this is a
derivative of.

The patch scripts carry their comments in Spanish, which is where they were written; the documentation is
in both languages.

*Street Fighter EX2 Plus* is © Capcom / Arika. This project is not affiliated with them, with Sony, with
Microsoft, or with the PSXRecomp author, and it distributes nothing that belongs to them. The details —
exactly what is and is not included here, and how to ask for a takedown — are in [`NOTICE.md`](NOTICE.md).
Rights holders can write to **jajdpmail@gmail.com**.
