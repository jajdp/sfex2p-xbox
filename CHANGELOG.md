# Changelog

All notable changes to this port. Dates are `YYYY-MM-DD`.

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
