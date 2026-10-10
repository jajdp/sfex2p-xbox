# Changelog

All notable changes to this port. Dates are `YYYY-MM-DD`.

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
