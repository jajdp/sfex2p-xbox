# Changelog

All notable changes to this port. Dates are `YYYY-MM-DD`.

## [1.0.5] — 2026-10-13

### Added

- **`.gitattributes`.** Without it, what a clone gives you depends on each machine's
  `core.autocrlf` — and `src/` here holds two files that are copied byte for byte into the
  framework's tree, while the sixteen patches compare anchors against files whose endings
  `.gitattributes` governs on the upstream side too. The body of the file is the same one the
  other ten published repositories carry, so that they can be compared; its top paragraph says
  what this one holds. Found by a homogeneity pass across all of them.

## [1.0.4] — 2026-10-13

### Added

- **What the console has to be before you start.** In Developer Mode, powered on, on the same
  network as your PC — and **with your profile signed in**, which is the one that costs an
  afternoon: with no user signed in, the console installs the package, lists it, and then launching
  it does nothing at all. None of this was in the guide; it was only in the project's own internal
  documentation.
- **The browser warning on the way into the Device Portal.** The console's certificate is issued by
  the console itself, so every browser objects to it. The guide used to give the portal's URL and
  nothing else. That is not something you can act on if you have never seen the screen, so it now
  names the buttons — in Edge, Chrome and Firefox — and says the portal will then ask for `xbox` /
  `xbox`.
- **That the console never asks for the certificate you signed with.** In Developer Mode it installs
  any signed package without caring who signed it: the **Add** screen has no field for it. Looking
  for that field sends people hunting for a problem that does not exist. The section says so, and
  gives the one command that exports the `.cer` out of the package, for the case where the portal
  ever did refuse a signature.

  While there: the English step 2 claimed the console trusts the certificate "once the portal
  accepts the install", which is not what happens and now contradicted the paragraph above it.
- **How to remove it from the console, and the warning that your saves go with it.** They live
  inside the package's `LocalState` (`PSXRecomp\SLUS-01105\saves`), and they are gone with it — so
  the section says where they are and to download them through the portal's **File explorer** first.
  It also says that removing it touches nothing on your PC, and that *updating* does not need an
  uninstall at all.

## [1.0.3] — 2026-10-13

### Added

- **The commands no longer need PowerShell 7, and say so.** Every example invoked `pwsh`, which is
  PowerShell 7 and does **not** ship with Windows — so on a machine without it the first command
  fails with "pwsh is not recognized", and nothing in the requirements warned about it. It turns
  out the scripts never needed it: all three run under the Windows PowerShell 5.1 that comes with
  Windows, and the executable that comes out is byte-identical (256 of 256 objects with the same
  `.text`). The examples now use `powershell`, and PowerShell is listed as a requirement with the
  version it was tested on.
- **And they carry `-ExecutionPolicy Bypass`, because without it they do not run at all on a stock
  Windows.** The default execution policy is `Restricted`, under which a `.ps1` will not even
  load: *"cannot be loaded because running scripts is disabled on this system"*. The flag lifts
  that for one run only, changes nothing on the machine and needs no administrator — all of which
  the guide now explains, rather than asking anyone to change their system policy.
- **Every command block now says where to type it.** The guides were written as if the reader
  already knew to open a terminal, which folder to be in, and that a block starting with `$` is
  PowerShell. None of that is obvious if this is not your trade. Each block now names its terminal
  and the folder it runs from, and blocks that are *output* rather than commands are marked as
  such, so there is no guessing about what you are supposed to type.
- **It is spelled out that administrator is not needed — and that using it breaks one step.** The
  certificate is created in the store of whichever user runs the command, so creating it in an
  elevated window puts it where `signtool`, running as you, will not find it.
- **A new §0 in the install guide: how to open the terminal.** Which one, how to find it from the
  Start menu, how to move to a folder with `cd`, what the backticks at the end of a long command
  mean, and how to tell whether a command worked.
- The ImageMagick snippet in `docs/ASSETS.md` **was bash, in a Windows-only guide, and its first
  line was an empty loop** (`for s in …; do :; done` does nothing). Anyone copying it got no tiles.
  Replaced with a PowerShell block that was run end to end: it produces all eleven files at exactly
  the right sizes.
- **`docs/HOW-IT-WORKS.es.md`, `docs/ASSETS.es.md` and `package/Assets/README.es.md`.** The README,
  the NOTICE and the install guide were already bilingual, but the document that explains what the
  sixteen patches actually change, the one that tells you what artwork to supply, and the folder
  README that points at it were English-only — so a reader who came in through `README.es.md`
  landed in English on the first click. The Spanish documents now link to the Spanish ones.

### Fixed

- **The Visual Studio requirement was wrong in both halves.** It said "Visual Studio 2022" with
  "Desktop development with C++" **and** "Universal Windows Platform development". Neither is what
  this port actually needs:

  - **The version is not pinned.** `tools/configurar-uwp.ps1` finds Visual Studio with
    `vswhere -latest -products *`, so it takes the newest installation that has the C++ tools. It
    never asked for 2022 in the first place.
  - **The UWP workload is not required.** Measured on the machine this port was built and tested
    on: neither `Microsoft.VisualStudio.ComponentGroup.UWP.VC` nor
    `Microsoft.VisualStudio.Component.UWP.VC.v143` is installed, and `vcvarsall x64 uwp` works,
    `cl /ZW` compiles C++/CX, and `vccorlib.lib` is in `lib\x64\store`. The C++ desktop tools
    bring all of it.

  `docs/INSTALL.md` §1 now names the three things that have to be true — `vcvarsall` taking `uwp`,
  the App Container CRT, and `/ZW` compiling — and gives a command that checks all three in ten
  seconds. It also says what this was built and tested with, and warns that a newer Visual Studio
  is not automatically a better one here: this port leans on the `uwp` target of `vcvarsall` and on
  the C++/CX extensions, both of which Microsoft has been winding down.

  Nothing in the recipe changed; only what the documentation claims you need.

## [1.0.1] — 2026-10-10

A code-review pass over this repository, in three passes: repository hygiene, a line-by-line read
of all the code, and a fresh-eyes pass that compiled and ran what it could. **The tree the recipe
produces is unchanged** except where this entry says otherwise: it was verified by applying the
profile with the old scripts and with the new ones to two identical copies and comparing them byte
for byte.

### Fixed

- `tools/apply_uwp.py` **crashed on a console whose code page is not UTF-8**, which is the Windows
  default: the steps report in Spanish, and printing an accented character raised
  `UnicodeEncodeError` half way through applying the profile. It now sets its own output and its
  children's to UTF-8.
- The WinRT entry point joined the split disc without checking a single write. With a full drive or
  a missing part, it renamed a truncated file into place and logged it as a success — the game
  would then fail much later and somewhere else. Every write and read is checked now, and on
  failure the partial file is left as `.uniendo` so the next boot retries.
- `tools/configurar-uwp.ps1` **did not propagate the exit code**: when CMake failed, the script
  still ended in success and the error scrolled past among the last 35 lines.
- `tools/empaquetar-uwp.ps1` rewrote `package/Package.appxmanifest` — a versioned file — when given
  `-Version`, leaving the working tree dirty and handing the version on to whoever used it next. It
  now changes only the copy that goes into the package.
- The same script discarded the SDK tools' output with `| Out-Null`, so a failure gave
  `makepri failed` and no clue; and it left its work folder, with the game executable inside, in
  `%TEMP%` forever. The output is kept and shown on failure, and the folder is removed unless
  `-Conservar` is passed.
- `raiz_juego()` in the entry point did not check what `GetTempPathW` returned, while the patch
  that computes the same path in `main.cpp` did.

### Removed

- **The five diagnostics under `tools/diagnostics/`.** They were scaffolding, described as
  temporary in their own headers, documented nowhere, and the from-scratch test that validated the
  sixteen profile patches never ran them — so three of the five could not work: two anchored on
  code that no longer exists in a patched tree (one of them on a previous version of the 16:9
  plugin) and two emitted C that does not compile. Both of those are the same two classes of
  defect this changelog recorded as fixed in the patches for 1.0.0, surviving in the files the test
  did not cover. They live on in the private project, where they were used.
- About 45 lines in `tools/parche_uwp_fps_r3.py` that searched for and removed two earlier failed
  attempts at reading R3. That code could only ever exist in the author's own tree; anyone cloning
  this starts from a clean one.

### Changed

- **The patching mechanism lives in one place.** The same skeleton — validate the argument, read,
  normalise line endings, check the marker, substitute, write atomically — was copied across
  seventeen scripts, with four diverging copies of the same helper. It is now `tools/parchear.py`,
  and the scripts carry only their anchors, their replacement text and three lines.
- **The OpenGL replacement is a real file.** Its 200 lines of C lived inside a Python string in
  `parche_uwp_gl.py`, where nothing could compile or lint them. It is `src/gpu_gl_renderer_stub.c`
  now, which the script copies into the tree, the same way the 16:9 repository ships its plugin —
  and it compiles with `-Wall -Wextra` without a warning.
- **One language per place.** The comments the patches write into the game's tree are all in
  English now, like the rest of the runtime; six scripts were injecting Spanish, and of the sixteen
  idempotence markers eight were in English and eight in Spanish. The scripts' own comments stay in
  Spanish, which is where they were written.
- `src/SDL_winrt_main_NonXAML.cpp` says in its header that it is a modified copy of SDL's entry
  point and what this port added, next to David Ludwig's public-domain notice. It also carries a
  UTF-8 BOM, so MSVC stops warning (C4819) about the accented characters in its comments.
- `prepara_datos()` no longer has to be called twice from `WinMain`: writing the BIOS and disc
  pointers is its own `escribe_punteros()`, which runs after the disc is joined.
- Comments that were a chronicle of the debugging — dates, what was tried and reverted, "found
  while testing on 2026-10-06" — now state what the code does and why. Pointers to things a reader
  cannot open (another unpublished port of mine, a private plan document, another project's version
  number) are gone.
- `LICENSE` now carries the **canonical** PolyForm Noncommercial 1.0.0 text from
  polyformproject.org, which is what the `PolyForm-Noncommercial-1.0.0` identifier names and what
  `NOTICE.md` relies on when it says this derivative is released under the framework's licence. The
  copy shipped before was an abridged variant missing *Distribution License*, *Notices*, *Changes
  and New Works License* and *Patent License*.
- `NOTICE.md` makes clear that the 117 quoted lines are all the quoting there is in the repository,
  which is now exactly true: with the diagnostics gone, the sixteen patch scripts are all the
  patching code here.
- One shared `.gitignore` across the three repositories, in English like the other two, keeping the
  two rules specific to this one.

### Note

If you have a tree already patched with 1.0.0, start from a clean clone of the game project: three
idempotence markers changed language, so the scripts will not recognise their own earlier work.
They will stop with "0 apariciones del ancla" rather than patch anything twice.

## [1.0.0] — 2026-10-08

First public release of the recipe. The port itself has been running on an Xbox Series in
Developer Mode since 2026-10-05: boots through the BIOS and the Capcom presentation, reaches
the title screen, plays with a controller in 16:9 at 60 FPS, and resumes where it left off
after the console suspends it.

### Added

- A `WindowsStore` CMake profile for a framework that has none, plus the WinRT entry point that
  seeds the app's data folder, joins the split disc, writes absolute `bios.cfg`/`disc.cfg` and
  redirects the runtime's output to `logs\`.
- Sixteen guarded patches, applied in order by `tools/apply_uwp.py`, covering: the six boot
  failures behind *"Failed to launch the application"*, the disc being resolved after mods are
  validated, the controller, the on-screen FPS counter and its R3 toggle, the 16:9 mod's plugin
  without recomp-ui, saving and resuming across suspension, and writable save paths.
- The 60 FPS work in 16:9: the wide pass went from 3.4–3.6 ms per frame to 0.7–0.8 by reading
  the centre columns from VRAM instead of drawing them twice, and clipping the rest to the
  margins.
- `tools/configurar-uwp.ps1` (Ninja inside the UWP toolchain, Visual Studio found with
  `vswhere`) and `tools/empaquetar-uwp.ps1` (packages and signs with your certificate, checks
  the manifest's `Publisher` matches it first).
- Five diagnostics under `tools/diagnostics/`, the ones that made each failure visible.
- Documentation in English and Spanish, and `NOTICE` stating exactly what of other people's
  work is here and what is not.

### Fixed, before publishing

Running the whole recipe against a clean clone of the game project exposed five things that had
drifted between the working tree and the scripts, each of which would have stopped anyone
reproducing this:

- `parche_wide_splice.py` had lost the two anchors of its textured-rect section, leaving the
  literal text of an unevaluated expression in their place: the script failed every time.
- `parche_wide_bandas.py` emitted `wide_band()` with four arguments instead of five, which
  would not compile.
- `parche_uwp_reanudar.py` wrote two unescaped newlines into C string literals.
- `parche_uwp_codigo.py` was missing the file-dialog guard, which had been applied by hand.
- `parche_uwp.py` set neither `/APPCONTAINER` nor `SDL_MAIN_HANDLED`-off-on-UWP — the two
  without which the package installs and the console will not launch it.

With those fixed, the recipe reproduces the tree that runs on the console: `main.cpp`,
`gpu_sw_renderer.c`, `host_osd.c`, `savestate.c`, `savestate.h`, `gpu_gl_renderer_stub.c`,
`psx_fiber.c` and `mod_plugins.h` come out **identical, line for line**, and `runtime.cmake`
equivalent (what differs is a leftover in the working tree that nothing reads).

### Notes

- Developed against commit `36e124d3` of the `psxrecomp` submodule.
- The package tiles are not distributed here: see `docs/ASSETS.md`.
