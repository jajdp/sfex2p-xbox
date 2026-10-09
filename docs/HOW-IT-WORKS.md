# How the port works

What the sixteen patches actually change, and why each one exists. Every one of these was a
real failure on a real console, in this order, each hiding the next.

Read [`INSTALL.md`](INSTALL.md) first if you just want to build it.

## 0. Why a profile from scratch

The framework this game uses has **no UWP support at all**. There was no `WindowsStore` profile
to turn on, so `parche_uwp.py` writes one into `runtime/runtime.cmake`:

| Piece | Why |
|---|---|
| `PSX_UWP` when `CMAKE_SYSTEM_NAME` is `WindowsStore` | The switch everything else hangs off |
| No debug server, no launcher, no Vulkan | They do not fit on a console |
| SDL2 through `find_package` | **SDL3 has no WinRT**, so the build needs `-DPSX_SDL_BACKEND=SDL2` and an SDL2 built for WindowsStore |
| `NOMINMAX` | On UWP the platform id is `WindowsStore`, **not** `Windows`, so the guard that normally hides `windows.h`'s `min`/`max` macros does not fire and `mod_runtime.cpp` fails with *"illegal token on right side of ::"* |
| `WINAPI_FAMILY=WINAPI_FAMILY_APP` | With the Ninja generator CMake does not set it, and without it SDL2 is not seen as WinRT and never exports `SDL_WinRTRunApp` |
| `SDL_MAIN_HANDLED` **not** defined on UWP | So SDL renames `main()` to `SDL_main()`, which is what the WinRT entry point calls |
| `/APPCONTAINER` at link time | The console only activates applications marked as such. Without it the package installs and will not start |

**The generator has to be Ninja.** The Visual Studio generator is multi-config, and this
framework emits one version file per configuration, which CMake refuses: *"Evaluation file to
be written multiple times"*.

## 1. The six boot failures

For a day the build was fine, the package installed, and the Device Portal answered **"Failed
to launch the application"** with nothing else. It was not one problem, it was six.

Two things made it tractable, and both are worth stealing: comparing the **PE imports** of the
executable against a port that does boot, and **redirecting the runtime's output to `logs\`**
from the entry point — on a console, stdout goes nowhere, so without that you work blind.

| # | What was wrong | Fix |
|---|---|---|
| 1 | The executable imported **`OPENGL32.dll`**, which does not exist on the console | `gpu_gl_renderer_stub.c`: an inert GL backend exposing the 39 symbols of the original (taken with `dumpbin /symbols`), and the `if(WIN32 OR MINGW)` link block excluded on UWP. `WindowsApp.lib` already provides what is allowed, **sockets included** — `ws2_32` was never the problem, the working port imports it too. `parche_uwp_gl.py` |
| 2 | It imported the **desktop CRT** (`msvcp140.dll`) and `kernel32.dll` | Build inside **`vcvarsall x64 uwp`**, not `vcvars64`, so `LIB` points at the App Container CRT and the imports become `msvcp140_app.dll`, `vcruntime140_app.dll`, `vccorlib140_app.dll` |
| 3 | The manifest **did not declare the VCLibs package** | `<PackageDependency Name="Microsoft.VCLibs.140.00" …>`. MSBuild adds it for you; a hand-written manifest does not. **This was the one actually blocking activation** |
| 4 | **Fibers and job objects**: the App Container has no `CreateFiber`, `ConvertThreadToFiber` or `TerminateJobObject` | The `…Ex` variants for fibers, and the dead `autocompile` call removed. `parche_uwp_appcontainer.py` |
| 5 | The runtime **anchors all its files to the executable's directory**, which on UWP is read-only | `exe_dir_from_argv` returns the data folder instead (§2). `parche_uwp_rutas.py` |
| 6 | Even after the runtime reported falling back to software, the window was still requested with a GL context: `SDL_CreateWindow failed: Could not initialize OpenGL / GLES library` | Force the software renderer **before** creating the window. `parche_uwp_render_software.py` |

## 2. The data folder, and the disc

The runtime says in its own comments that its anchor is the executable's directory and **never**
the working directory. On a console that is the package install folder, read-only, so the
profile points it at

```
…\Packages\<identity>\LocalState\PSXRecomp\SLUS-01105\
```

obtained from the package's temp folder by going up two levels — that way nothing has to
initialise the Windows Runtime before SDL does.

The WinRT entry point (`src/SDL_winrt_main_NonXAML.cpp`) prepares that folder on every boot: it
creates `disc\`, `bios\`, `saves\` and `logs\`; **seeds** what the package carries (`game.toml`
and the mods always, so a new package really updates them; `settings.toml`, `input.ini` and
`keybinds.ini` only if missing, because those are the player's); **joins the disc** from the
150 MiB parts the Device Portal forces you to upload; writes `bios.cfg` and `disc.cfg` with
**absolute** paths, since a relative one would resolve against the working directory; and
redirects `stdout`/`stderr` to `logs\`, unbuffered, because a crash would otherwise lose exactly
what you need.

### The disc is resolved after the mods are validated

The framework validates mod packages — and the disc hash each one demands — **before** it works
out where the disc is: `mod_runtime_commit()` runs a few lines before
`resolve_disc_for_runtime()`. Until then the only path it has is the one in `game.toml`, which
is the path on the PC of whoever generated the project. On a console that produced an empty
hash, and **no mod with a `disc_sha256` ever applied**: the Spanish menus were rejected with
`package does not target this game/image`, while the 16:9 mod went through because it demands no
hash. Fixed from both ends: the packer strips that key from the bundled `game.toml`, and
`parche_uwp_disco_mods.py` resolves the disc just before the check.

## 3. The plugin, the controller, the FPS counter

- **The 16:9 plugin.** Wide aspect is owned by the `sfex2p.widescreen` mod, and a mod with a
  trusted plugin cannot be enabled unless that plugin is inside the executable. The framework
  only compiles `CODEGEN_SETUP_SOURCES` **when recomp-ui is on**, and on a console it is off, so
  the runtime refused to start with `trusted plugin is unavailable: sfex2p.widescreen`.
  `parche_uwp_plugin_16_9.py` compiles it separately and also fixes the registration for MSVC:
  the `.CRT$XCU` pointer was `static` and the linker was entitled to drop it (with clang, which
  builds the PC version, that path is not even used).
- **The controller.** With no launcher to assign devices, a product build leaves player 1 on the
  **keyboard**, and a console has no keyboard: the pad was never opened and nothing said so. On
  UWP every slot uses "auto", the first free controller (`parche_uwp_mando.py`). The log
  confirms it: `opened controller for slot: Xbox One Game Controller`.
- **The FPS counter.** The framework computes it already, but its display layer (`host_osd.c`)
  sits entirely behind `#if defined(RECOMP_LAUNCHER)`: with no launcher it is not compiled, and
  the number only went to the **window title**, which nobody can see on a console.
  `parche_uwp_osd.py` enables it for the UWP profile — it needs no recomp-ui, since the 8×8 font
  and the `SDL_Renderer` drawing live in that same file — `parche_uwp_fps_encendido.py` leaves it
  on by default, and `parche_uwp_fps_r3.py` binds **R3** to the toggle. That last one is fussier
  than it looks: the button test has to go on the **already-combined button word** of player 1,
  right before it is handed to the SIO (`apply_pad_slot_to_sio`, bit 2, `0 = pressed`). Neither
  the SDL event nor polling inside `pad_buttons_for()` works.

## 4. 60 FPS in 16:9: splicing the centre

**Measured, not guessed.** In 16:9 the fights ran at **51–55 FPS**; in 4:3, at 60–62. The cause:
in wide mode the software rasteriser draws **every primitive twice**, once into canonical VRAM
and once into the wide surface. Timing that second pass (`tools/diagnostics/diag_perf_ancho.py`,
which measures it and prints it next to the FPS counter) gave **3.4–3.6 ms of every frame**, at
~25 000 primitives per second. A 60 Hz frame is 16.68 ms.

The idea: the centre of the wide surface is a **1:1 copy of VRAM** — the two differ by the
integer translation `wide_dx()`, so identical inputs give identical pixels. The only thing the
wide surface adds is the **margins**. So:

1. when composing the image (`sw_render_wide_display`), the centre columns are read **from
   VRAM**, which is already drawn, and only the margins come from the wide surface;
2. the wide pass **skips primitives that do not reach a margin**, which in this game is almost
   all of them — its stages are modelled for the 4:3 frame;
3. and the ones that do reach are **clipped to the band** they actually contribute to, one pass
   per margin, instead of being rasterised whole.

(1) and (2) are `parche_wide_splice.py`; (3) is `parche_wide_bandas.py`.

| | Wide pass | FPS in a fight |
|---|---|---|
| Before | 3.4–3.6 ms/frame | 51–55 |
| With the splice | 1.0–1.4 ms/frame | 56–62 |
| With the bands too | **0.7–0.8 ms/frame** | **60 sustained** (59–62) |

**What switches it off.** The 2D backdrop stretch (`wide_bd_get`) does rewrite the centre of the
wide surface, so the first time it is used the splice disables itself for the rest of the
session and everything goes back to the old path. In this game the stretch is off
(`[widescreen] nw_phase_backdrop = false`). It also stays off with the high-resolution mirror
(scale > 1), which a console does not use. In both cases you get the old performance and the
same image.

## 5. Coming back where you left off

Developer Mode **terminates** a UWP game that goes to the background — Microsoft's own words:
*"Games will be suspended and terminated in the background"*. Coming back from Home restarted
the game. That is not a bug in the port: the system relaunches with
`PreviousExecutionState = Terminated` and expects the app to restore itself.

This framework makes the hard part easy: `boot_state.c` serialises the whole machine and
`savestate.c` runs it **at a safe point** (block leader, no exception in flight). All that was
needed was a **reserved slot, 99**, outside the player's twelve.

What did **not** work, measured on the console:

| Attempt | What happened |
|---|---|
| `SDL_WINDOWEVENT` in the event loop | Never arrives: the console terminates the app first |
| An event watch (`SDL_AddEventWatch`) | These **do** arrive: `SDL_APP_WILLENTERBACKGROUND`, `FOCUS_LOST`, `DIDENTERBACKGROUND` |
| Waiting inside the watch for the save to run | Deadlock: on WinRT the watch runs on the **same thread** as the emulator (SDL calls it from `SDL_PumpEvents`), so sleeping there blocks the very loop that has to write |
| Asking for the save and letting it continue | The emulator never runs again after the warning, so the `.pst` is never written |

**So it saves while you play**: every 10 seconds into the reserved slot, through the framework's
own deferred save, and the last one is restored when the app is relaunched as `Terminated`. You
lose those seconds at most. A normal start **discards** the saved state, so a session that ended
properly is not resumed. `parche_uwp_reanudar.py`.

### And the one that had been hiding all along

The log said it plainly:

```
savestate: SAVE FAILED slot 99 -> S:\Program Files\WindowsApps\<package>\saves/...
```

That is the **install folder**, read-only. `game.toml` is loaded from there and its
`[runtime] memcard_dir = "saves"` is a **relative** path, resolved against that file's folder.
Which means **both memory cards and every save state pointed somewhere unwritable**, and the
game had never saved anything — nobody had noticed, because re-anchoring the runtime (§2) does
not cover a path that arrives already resolved from `game.toml`.
`parche_uwp_escritura.py` re-anchors it, and the log confirms it on boot:

```
psxrecomp: UWP — writable state directory = …\LocalState\PSXRecomp\SLUS-01105\saves
```
