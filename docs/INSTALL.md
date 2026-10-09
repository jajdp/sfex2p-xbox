# Building the port and getting it onto the console

*(Español: [INSTALL.es.md](INSTALL.es.md))*

Nine steps. Steps 1 to 3 are one-offs; from step 4 on, a rebuild is two commands.

## 1. What you need first

| | |
|---|---|
| **The game project, already working on your PC** | [strider973/Street-Fighter-EX2-Plus-Recompiled](https://github.com/strider973/Street-Fighter-EX2-Plus-Recompiled) on the [PSXRecomp](https://github.com/RetroPortingToolKit/psxrecomp) framework, cloned with `--recurse-submodules`. Build it and play it on Windows first. If it does not run there, it will not run on a console, and you will be debugging two things at once |
| **Your own disc** | An NTSC-U dump of `SLUS-01105` (`.cue` + `.bin`) |
| **A retail SCPH-1001 BIOS** | The game project ships `openbios = false`; the bundled OpenBIOS will not boot this title |
| **Visual Studio 2022** | "Desktop development with C++" **and** "Universal Windows Platform development", plus the Windows 10/11 SDK and Ninja |
| **An SDL2 built for WindowsStore** | Step 2 |
| **An Xbox in Developer Mode** | Registered, with Device Portal reachable from your PC |

This port was developed against the framework as of commit `36e124d3` of the `psxrecomp`
submodule. A much newer framework may have moved the code the patches anchor on; each patch
checks its anchor and stops rather than mangling anything, so you will know immediately.

## 2. An SDL2 for WindowsStore

**SDL3 has no WinRT backend**, so the port uses the SDL2 backend. You need SDL2 built for
`WindowsStore` — 2.30.2 is what this was tested with. From an SDL2 2.30.2 source tree:

```powershell
cmake -S <sdl2-source> -B <sdl2-build> -G Ninja `
      -DCMAKE_SYSTEM_NAME=WindowsStore -DCMAKE_SYSTEM_VERSION=10.0 `
      -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=<sdl2-install>
cmake --build <sdl2-build> --target install
```

What you pass to `-Sdl2` later is the folder holding `SDL2Config.cmake`, usually
`<sdl2-install>/cmake` or `<sdl2-install>/lib/cmake/SDL2`.

## 3. A certificate to sign with

Developer Mode accepts self-signed packages. Create one, and **remember its subject** — the
`Publisher` in the manifest has to match it character for character:

```powershell
$c = New-SelfSignedCertificate -Type Custom -Subject "CN=YourName" `
       -KeyUsage DigitalSignature -FriendlyName "UWP signing" `
       -CertStoreLocation "Cert:\CurrentUser\My" `
       -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3", "2.5.29.19={text}")
$c.Thumbprint     # this is what you pass as -Certificado
```

Then open `package/Package.appxmanifest` and replace the two `CHANGE-ME`:

```xml
<Identity Name="SFEX2Plus-Recomp" Publisher="CN=YourName" ProcessorArchitecture="x64" Version="1.0.0.0" />
...
<PublisherDisplayName>YourName</PublisherDisplayName>
```

The packer compares the two before it does anything and stops if they differ, which saves you
finding out at the `signtool` step.

## 4. Apply the UWP profile

```powershell
python tools/apply_uwp.py <path-to-game-project-root>
python tools/apply_uwp.py --list      # the sixteen steps, in order, and what each one is for
```

It copies the WinRT entry point into `<project>/UWP/`, registers it at the end of the project's
`CMakeLists.txt`, and runs the sixteen patches in order. Every step is idempotent and checks
what it expects to find, so running it twice changes nothing, and if a step does not recognise
the tree it stops there instead of leaving it half done.

What it changes, and why each one: [`HOW-IT-WORKS.md`](HOW-IT-WORKS.md).

## 5. Configure and build

```powershell
pwsh -File tools/configurar-uwp.ps1 -Raiz <project> -Build <build> -Sdl2 <sdl2 cmake dir> -Compilar
```

It enters the UWP toolchain (`vcvarsall x64 uwp`, found through `vswhere`) and configures with
**Ninja**. Not the Visual Studio generator: it is multi-config, and this framework writes one
version file per configuration, which CMake rejects with *"Evaluation file to be written
multiple times"*.

`vcvarsall x64 uwp` matters by itself: it puts the App Container CRT on `LIB`, so the
executable imports `msvcp140_app.dll` instead of the desktop `msvcp140.dll`. With `vcvars64`
the package installs and the console refuses to launch it.

Out comes `Street_Fighter_EX2_Plus.exe` (~16.6 MB) in the build folder. Roughly a minute.

## 6. The package tiles

Put eleven PNGs in `package/Assets/`. This repository ships none — see
[`ASSETS.md`](ASSETS.md) for the names and exact sizes. Plain colour images will do.

## 7. Package and sign

```powershell
pwsh -File tools/empaquetar-uwp.ps1 -Build <build> -Juego <project> -Salida <out> `
     -Certificado <thumbprint> -Version 1.0.0.0
```

It assembles the executable, the manifest, the tiles, the initial configuration and the mod
packages; rebuilds `resources.pri` with `makepri` (without the default `<packaging>` block,
which splits the PRI by scale and makes the console reject it); packs with `makeappx`; and
signs with your certificate.

Add a mod with `-Mod <folder of a package>`, and point `-VCLibs` at
`Microsoft.VCLibs.x64.14.00.appx` to have it copied next to the output for installing.

Out comes `<identity>_<version>_x64.msix`, about 8.5 MB. **The disc and the BIOS are not in
it** — they go to the console separately, in step 9.

## 8. Install it on the console

Through the Device Portal (`https://<console-ip>:11443`), **My games & apps → Add**, and upload
the `.msix`. The VCLibs framework package has to be installed too, as a dependency, the first
time.

If the first install fails with *not enough space*, install a small seed package first and then
the real one on top: Developer Mode reserves its space in a way that a first big install can
trip over.

## 9. The disc and the BIOS

They live in the app's own data folder, which the first boot creates:

```
…\Packages\<identity>\LocalState\PSXRecomp\SLUS-01105\
    disc\    bios\    saves\    logs\
```

Upload through the Device Portal's file explorer, into `LocalState` of this app:

- the **BIOS** into `bios\`;
- the **disc** into `disc\`. The portal rejects a whole 447 MB upload with a 500, so split the
  `.bin` into **150 MiB parts** named `<disc>.bin.parte1`, `.parte2`, … and upload those: the
  entry point concatenates them once, on the next boot, and keeps them as a backup. Upload the
  `.cue` as well.

On every boot the entry point also seeds `game.toml` and the mods from inside the package (so a
new package really does update them), leaves `settings.toml`, `input.ini` and `keybinds.ini`
alone if they already exist (they are yours), writes `bios.cfg` and `disc.cfg` with **absolute**
paths, and redirects the runtime's output to `logs\salida.txt` and `logs\errores.txt`.

Read those two logs. On a console they are the only thing you have.

## If something goes wrong

| Symptom | Cause |
|---|---|
| `Failed to launch the application` | Six things cause this, and each hides the next. [`HOW-IT-WORKS.md`](HOW-IT-WORKS.md) §1 lists them with what each one looks like. The most common one left by hand is the **VCLibs dependency missing from the manifest** |
| The package installs but there is no window | Check `logs\errores.txt`. If it says `Could not initialize OpenGL / GLES library`, the software renderer was not forced before the window was created — step 4 did not finish |
| `trusted plugin is unavailable: sfex2p.widescreen` | The 16:9 mod's plugin is not in the executable. It needs `parche_uwp_plugin_16_9.py` (step 14 of the profile) and the plugin source in the project |
| `package does not target this game/image` | The mods are validated before the disc is resolved. The packer strips `disc` from the bundled `game.toml` and `parche_uwp_disco_mods.py` resolves it earlier; if you repackaged by hand, that key is probably back |
| No controller | All slots must be on "auto" (`parche_uwp_mando.py`). The log says `opened controller for slot:` when it works |
| Nothing is ever saved | `memcard_dir` is relative and resolves against the read-only install folder. `parche_uwp_escritura.py` re-anchors it; the log confirms `UWP — writable state directory = …` |
| The game restarts after you go Home | Expected without `parche_uwp_reanudar.py`: Developer Mode terminates a suspended game. With it, the machine is saved every 10 seconds and restored on relaunch |
| Fights below 60 FPS in 16:9 | The last two steps of the profile (`parche_wide_splice.py`, `parche_wide_bandas.py`) are what buy that back |
