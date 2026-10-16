# Building the port and getting it onto the console

*(Español: [INSTALL.es.md](INSTALL.es.md))*

Nine steps. Steps 1 to 3 are one-offs; from step 4 on, a rebuild is two commands.

## 0. Before you start: where the commands go

This guide is full of blocks like this one. **They are all commands you type yourself** into a
terminal window, and each one says above it where from. If you have never used one, this section is
everything you need; if you have, skip it.

### The terminal: PowerShell

Everything in this guide goes into **PowerShell**, the ordinary Windows terminal:

1. Press the **Windows** key.
2. Type `powershell`.
3. Press **Enter** on *Windows PowerShell*.

A window opens with a line ending in `>`. That is where you type the command and press **Enter**.

**Moving to a folder.** Almost every command is typed *from a particular folder*, usually this
repository's. You get there with `cd` and the path, in quotes if it has spaces:

```powershell
cd "C:\Users\your-name\Downloads\sfex2p-xbox"
```

**A shortcut that saves mistakes:** open the folder in File Explorer, click the address bar, type
`powershell` over whatever is there and press **Enter**. PowerShell opens already in that folder.

⚠ Some commands are long and are split across lines with a **backtick** (`` ` ``) at the end of
each. Copy them whole, backticks included: they are what says "continues on the next line".

### You do not need administrator — and it is better not to

Nothing in this guide needs "run as administrator". All of it was built and tested from an ordinary
account.

> ⚠ And in one step, being administrator actively **breaks** it: the certificate in §3 is created in
> the store of whichever user runs the command. Create it elevated and it lands in the
> administrator's store, so when you package — as yourself — `signtool` cannot find it and fails
> without saying why.
>
> The only thing that asks for administrator rights is the Visual Studio **installer**, and it asks
> on its own.

### How to tell whether a command worked

The ones here finish by saying what they did, and say so when something goes wrong too. A command
that prints nothing has usually worked; to be sure, this answers `True` when the previous one
succeeded:

```powershell
$?
```

---

## 1. What you need first

| | |
|---|---|
| **The game project, already working on your PC** | [strider973/Street-Fighter-EX2-Plus-Recompiled](https://github.com/strider973/Street-Fighter-EX2-Plus-Recompiled) on the [PSXRecomp](https://github.com/RetroPortingToolKit/psxrecomp) framework, cloned with `--recurse-submodules`. Build it and play it on Windows first. If it does not run there, it will not run on a console, and you will be debugging two things at once |
| **Your own disc** | An NTSC-U dump of `SLUS-01105` (`.cue` + `.bin`) |
| **A retail SCPH-1001 BIOS** | The game project ships `openbios = false`; the bundled OpenBIOS will not boot this title |
| **Visual Studio** | "Desktop development with C++", plus the Windows 10/11 SDK and Ninja. See "Which Visual Studio" below — the version is not pinned, and the UWP workload is *not* required |
| **An SDL2 built for WindowsStore** | Step 2 |
| **An Xbox in Developer Mode** | Registered, with Device Portal reachable from your PC |
| **PowerShell** | The one Windows ships with (Windows PowerShell 5.1) is enough: **you do not need to install PowerShell 7**. Tested with both, and the binary that comes out is identical |

This port was developed against the framework as of commit `36e124d3` of the `psxrecomp`
submodule. A much newer framework may have moved the code the patches anchor on; each patch
checks its anchor and stops rather than mangling anything, so you will know immediately.

### Which Visual Studio

**The version is not pinned.** `tools/configurar-uwp.ps1` finds it with
`vswhere -latest -products *`, so it takes the newest installation that has the C++ tools. It
never asks for 2022.

What this port actually needs from Visual Studio is three things, and all three are checkable:

- `vcvarsall.bat` has to accept the **`uwp`** argument;
- the **App Container CRT** has to be there, at `VC\Tools\MSVC\<version>\lib\x64\store\`;
- **`cl.exe /ZW` has to compile**, because the WinRT entry point is C++/CX — that is what needs
  `vccorlib.lib`, which lives in that same `store` folder.

Check all three:

> **Where to type this:** in **PowerShell** — press the **Windows** key, type `powershell` and
> press **Enter** — in an **ordinary** window: you do not need "run as administrator", from any
> folder.

```powershell
$vs = & "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe" `
        -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
        -property installationPath
$vcvars = Join-Path $vs 'VC\Auxiliary\Build\vcvarsall.bat'
Get-ChildItem (Join-Path $vs 'VC\Tools\MSVC') -Directory |
    ForEach-Object { Test-Path (Join-Path $_.FullName 'lib\x64\store\vccorlib.lib') }
'ref class T sealed { };' | Set-Content -Encoding ascii "$env:TEMP\zw.cpp"
cmd /c "`"$vcvars`" x64 uwp >nul 2>nul && cl /nologo /c /ZW /EHsc `"$env:TEMP\zw.cpp`" /Fo`"$env:TEMP\zw.obj`""
```

A `True`, then `zw.cpp` and nothing else, and you are fine. (`vcvarsall.bat`
sometimes prints a `vswhere.exe is not recognized` of its own; it is harmless,
and the `2>nul` above keeps it out of the way.)

> **The UWP workload is not required.** That is measured, not assumed: on the machine this port
> was built and tested on, neither `Microsoft.VisualStudio.ComponentGroup.UWP.VC` nor
> `Microsoft.VisualStudio.Component.UWP.VC.v143` is installed — and `vcvarsall x64 uwp` works,
> `cl /ZW` compiles C++/CX, and `vccorlib.lib` is in `lib\x64\store`. The C++ desktop tools bring
> all of it.

> ⚠ **Newer is not automatically better here.** Microsoft has been winding down UWP support for
> years, and this port leans on two things it has already deprecated elsewhere: the `uwp` target of
> `vcvarsall` and the C++/CX extensions. If some future release drops either, this recipe does not
> work on it however new it is — the checks above take ten seconds and tell you.

**Built and tested with:** Visual Studio Community 2022 17.14.37628.2, MSVC 14.44.35207, Windows
SDK 10.0.26100. Anything older than VS 2022 has not been tried.

### Why the PowerShell commands carry `-ExecutionPolicy Bypass`

Because without it they do not work on a freshly installed Windows. The **execution policy**
Windows ships with is `Restricted`, and under it a `.ps1` file will not even load:

```text
... cannot be loaded because running scripts is disabled on this system.
```

`-ExecutionPolicy Bypass` lifts that restriction **for that one run only**: it changes nothing on
the system, leaves nothing open afterwards, and does not need administrator rights. That is why
every command here carries it, and why you are not asked to change your machine's policy.

⚠ And it is why they say `powershell` and not `pwsh`: **`pwsh` is PowerShell 7**, which does not
come with Windows. If you have it, it works too — swap `powershell` for `pwsh` and leave the rest —
but nothing here needs it.

---

## 2. An SDL2 for WindowsStore

**SDL3 has no WinRT backend**, so the port uses the SDL2 backend. You need SDL2 built for
`WindowsStore` — 2.30.2 is what this was tested with.

> **Where to type this:** in **PowerShell** — press the **Windows** key, type `powershell` and
> press **Enter** — in an **ordinary** window: you do not need "run as administrator", from
> wherever you unpacked the SDL2 sources.

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
`Publisher` in the manifest has to match it character for character.

⚠ This is where not opening the window "as administrator" really matters: the certificate is
created in the store of whichever user runs the command, so an elevated one would put it in the
administrator's store, and `signtool`, running as you, would not find it.

> **Where to type this:** in **PowerShell** — press the **Windows** key, type `powershell` and
> press **Enter** — in an **ordinary** window: you do not need "run as administrator", from any
> folder.

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

This repository's folder is the one with `tools\` and `docs\` inside it:

> **Where to type this:** in **PowerShell** — press the **Windows** key, type `powershell` and
> press **Enter** — in an **ordinary** window: you do not need "run as administrator", from this
> repository's folder.

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

> **Where to type this:** in **PowerShell** — press the **Windows** key, type `powershell` and
> press **Enter** — in an **ordinary** window: you do not need "run as administrator", from this
> repository's folder.

```powershell
powershell -ExecutionPolicy Bypass -File tools/configurar-uwp.ps1 -Raiz <project> -Build <build> -Sdl2 <sdl2 cmake dir> -Compilar
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

> **Where to type this:** in **PowerShell** — press the **Windows** key, type `powershell` and
> press **Enter** — in an **ordinary** window: you do not need "run as administrator", from this
> repository's folder.

```powershell
powershell -ExecutionPolicy Bypass -File tools/empaquetar-uwp.ps1 -Build <build> -Juego <project> -Salida <out> `
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

### 8.1 The dependency: VCLibs

The executable imports the App Container CRT — `msvcp140_app.dll`, `vcruntime140_app.dll`,
`vccorlib140_app.dll` — which does not live in the package but in a **framework package** that
has to be installed on the console once. The manifest declares it:

```xml
<PackageDependency Name="Microsoft.VCLibs.140.00" MinVersion="14.0.33519.0"
                   Publisher="CN=Microsoft Corporation, O=Microsoft Corporation, L=Redmond, S=Washington, C=US" />
```

**The file you need is `Microsoft.VCLibs.x64.14.00.appx`** (~900 KB). You already have it: the
Windows SDK and Visual Studio install it here —

```text
C:\Program Files (x86)\Microsoft SDKs\Windows Kits\10\ExtensionSDKs\Microsoft.VCLibs\14.0\Appx\Retail\x64\Microsoft.VCLibs.x64.14.00.appx
```

⚠ **Two files are easy to grab by mistake and neither works:**

- `Microsoft.VCLibs.x64.14.00.Desktop.appx`, the one `aka.ms` links to, is the **Desktop Bridge**
  build. Different package, and the console will keep saying the dependency is missing.
- `…\Appx\**Debug**\x64\Microsoft.VCLibs.x64.Debug.14.00.appx` is only for packages signed in
  Debug configuration. This port builds Release.

Passing `-VCLibs <that path>` to `empaquetar-uwp.ps1` copies it into `<out>\Dependencies\`, so
the `.msix` and its dependency end up side by side and you are not hunting for it at the portal.

It is installed **once per console**: later packages, and later versions of this one, already
find it.

### Before you touch anything: how the console has to be

- **In Developer Mode**, with Dev Home installed. If it is not, that is a separate process with
  Microsoft and this guide does not cover it. - **Powered on and with your profile signed in.**
  ⚠ With no user signed in the console **will not open applications**: the package installs,
  shows up in the list, and launching it does nothing. This is one of the costliest things to
  work out on your own. - **On the same network as your PC.** - **Its address**, which **Dev
  Home** shows you on the console itself. The Device Portal listens on port **11443** over
  HTTPS. - **Portal username and password**: the ones you set in **Dev Home → Remote Access
  Settings** when you turned remote access on.

### 8.2 Upload it

Open `https://<console-ip>:11443` in the browser on your PC.

⚠ The browser will warn that **the site's certificate is not trusted**. That is normal and not a
problem: the certificate belongs to the console, which issues it itself. Go in anyway — in Edge
and Chrome, **Advanced** → **Continue to … (unsafe)**; in Firefox, **Advanced** →
**Accept the Risk and Continue**. It will then ask for the portal's username and password
(the ones you set in Dev Home).

Once in, **My games & apps → Add**:

1. **App package** → your `.msix`.
2. **Certificate** → not needed: the package is signed and Developer Mode accepts it.
3. **Optional packages / Dependency** → add `Microsoft.VCLibs.x64.14.00.appx` here, the first
   time.
4. **Next → Install**, and wait for *Package successfully registered*.

> **The console will not ask you for the certificate you signed with.** In Developer Mode it
> installs any signed package without needing to know the signer: the **Add** screen does not even
> have a field for it. The certificate was needed on your PC, to sign (§3), and that is where its
> job ends.
>
> If the portal ever did reject the signature, what you would register on the console is the
> **public half** of your certificate — a `.cer` file — which comes out of the package itself:
>
> ```powershell
> (Get-AuthenticodeSignature -LiteralPath "<your .msix>").SignerCertificate |
>     Export-Certificate -FilePath "$env:USERPROFILE\Desktop\signing.cer"
> ```

If it reports the dependency as missing after all this, you almost certainly added one of the
two wrong files from 8.1.

### 8.3 If it says `There is not enough space on the disk`

This is not your console being full, and the message is misleading. **The first install of a
package family goes to `D:\DevelopmentFiles`**, a partition of about 5 GB that Developer Mode
keeps for exactly that; later *updates* of an already-registered family go somewhere else. That
partition fills up with the first version of everything you have ever sideloaded, and
**uninstalling a game does not empty it** — the folders stay behind.

So the fix is to make your package an **update** instead of a first install, with a *seed*:

> A **seed** is a package with the **same identity** as the real one — same `Identity Name` and
> same `Publisher` — but a **lower version** and a **tiny executable** inside. It never has to
> run. Its only job is to register the family on the console, cheaply, so that the real package
> arrives as an update.

1. Make a folder with any small `.exe` renamed to `Street_Fighter_EX2_Plus.exe` (a couple of MB
   is plenty — it is never launched):

   > **Where to type this:** in **PowerShell** — press the **Windows** key, type `powershell`
   > and press **Enter** — in an **ordinary** window: you do not need "run as administrator",
   > from any folder.

   ```powershell
   New-Item -ItemType Directory -Force <seed-build> | Out-Null
   Copy-Item C:\Windows\System32\notepad.exe <seed-build>\Street_Fighter_EX2_Plus.exe
   ```

2. Package it with a **lower version** than the real one, everything else the same:

   > **Where to type this:** in **PowerShell** — press the **Windows** key, type `powershell`
   > and press **Enter** — in an **ordinary** window: you do not need "run as administrator",
   > from this repository's folder.

   ```powershell
   powershell -ExecutionPolicy Bypass -File tools/empaquetar-uwp.ps1 -Build <seed-build> -Juego <project> -Salida <out> `
        -Certificado <thumbprint> -Version 0.0.0.1
   ```

3. Install that one first (8.2), with the VCLibs dependency.
4. Then repackage and install the real one with its own version — `-Version 1.0.0.0` — and the
   portal takes it as an update. It goes in.

Keep the real version above the seed's from then on, and you will not meet this again for this
package. If `D:\DevelopmentFiles` is genuinely full of orphaned first versions of other things,
they can be deleted through the portal's file API with
`knownfolderid=DevelopmentFiles` — files first, then the emptied folders — but that is housekeeping
for your console, not part of installing this.

### Removing it from the console

⚠ **Your saves go with it.** They live inside the package, in its `LocalState`, and disappear with
it. To keep them, download them first from the Device Portal's **File explorer**: they are under
`LocalState\PSXRecomp\SLUS-01105\saves`.

To uninstall, in the Device Portal: **My games & apps**, find the game in the list, and **Remove**.
Nothing on your PC is touched: the `.msix`, the project, your disc and your BIOS stay
where they were.

Reinstalling afterwards starts from scratch, with empty saves. If what you want is to **update**
without losing them, do not uninstall: install a package with a **higher version** on top — the
`-Version` you pass to `empaquetar-uwp.ps1` (§7). The same version replaces nothing.

---

## 9. The disc and the BIOS

They live in the app's own data folder, which the first boot creates:

```text
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
