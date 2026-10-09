# Construir el port y meterlo en la consola

*(English: [INSTALL.md](INSTALL.md))*

Nueve pasos. Del 1 al 3 se hacen una sola vez; del 4 en adelante, rehacerlo son dos órdenes.

## 1. Lo que hace falta antes

| | |
|---|---|
| **El proyecto del juego, ya funcionando en tu PC** | [strider973/Street-Fighter-EX2-Plus-Recompiled](https://github.com/strider973/Street-Fighter-EX2-Plus-Recompiled) sobre el framework [PSXRecomp](https://github.com/RetroPortingToolKit/psxrecomp), clonado con `--recurse-submodules`. Compílalo y juégalo en Windows primero: si ahí no corre, en la consola tampoco, y estarías depurando dos cosas a la vez |
| **Tu propio disco** | Un volcado NTSC-U de `SLUS-01105` (`.cue` + `.bin`) |
| **Una BIOS retail SCPH-1001** | El proyecto del juego va con `openbios = false`: la OpenBIOS incluida no arranca este título |
| **Visual Studio 2022** | «Desarrollo de escritorio con C++» **y** «Desarrollo de la Plataforma universal de Windows», más el SDK de Windows 10/11 y Ninja |
| **Un SDL2 compilado para WindowsStore** | Paso 2 |
| **Una Xbox en modo desarrollador** | Registrada, con el Device Portal accesible desde tu PC |

Este port se hizo contra el framework en el commit `36e124d3` del submódulo `psxrecomp`. Un
framework mucho más nuevo puede haber movido el código en el que se anclan los parches; cada
parche comprueba su ancla y se detiene en vez de estropear nada, así que lo sabrás en el acto.

## 2. Un SDL2 para WindowsStore

**SDL3 no tiene WinRT**, así que el port usa el backend SDL2. Hace falta un SDL2 compilado para
`WindowsStore`; el probado es el 2.30.2. Desde un árbol de fuentes de SDL2 2.30.2:

```powershell
cmake -S <fuentes-sdl2> -B <build-sdl2> -G Ninja `
      -DCMAKE_SYSTEM_NAME=WindowsStore -DCMAKE_SYSTEM_VERSION=10.0 `
      -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=<instalacion-sdl2>
cmake --build <build-sdl2> --target install
```

Lo que luego se pasa en `-Sdl2` es la carpeta que contiene `SDL2Config.cmake`, normalmente
`<instalacion-sdl2>/cmake` o `<instalacion-sdl2>/lib/cmake/SDL2`.

## 3. Un certificado para firmar

El modo desarrollador acepta paquetes autofirmados. Crea uno y **apunta su sujeto**: el
`Publisher` del manifiesto tiene que coincidir con él letra por letra.

```powershell
$c = New-SelfSignedCertificate -Type Custom -Subject "CN=TuNombre" `
       -KeyUsage DigitalSignature -FriendlyName "Firma UWP" `
       -CertStoreLocation "Cert:\CurrentUser\My" `
       -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3", "2.5.29.19={text}")
$c.Thumbprint     # esto es lo que se pasa en -Certificado
```

Después, en `package/Package.appxmanifest`, cambia los dos `CHANGE-ME`:

```xml
<Identity Name="SFEX2Plus-Recomp" Publisher="CN=TuNombre" ProcessorArchitecture="x64" Version="1.0.0.0" />
...
<PublisherDisplayName>TuNombre</PublisherDisplayName>
```

El empaquetador compara los dos antes de hacer nada y se detiene si no coinciden, que es mejor
que enterarse al llegar a `signtool`.

## 4. Aplicar el perfil UWP

```powershell
python tools/apply_uwp.py <ruta de la raíz del proyecto del juego>
python tools/apply_uwp.py --list      # los dieciséis pasos, en orden, y para qué es cada uno
```

Copia la entrada WinRT a `<proyecto>/UWP/`, la registra al final del `CMakeLists.txt` del
proyecto y aplica los dieciséis parches en orden. Cada paso es idempotente y comprueba lo que
espera encontrar: pasarlo dos veces no cambia nada y, si un paso no reconoce el árbol, se
detiene ahí en vez de dejarlo a medias.

Qué cambia y por qué cada cosa: [`HOW-IT-WORKS.md`](HOW-IT-WORKS.md) (en inglés).

## 5. Configurar y compilar

```powershell
pwsh -File tools/configurar-uwp.ps1 -Raiz <proyecto> -Build <compilación> -Sdl2 <cmake de SDL2> -Compilar
```

Entra en el entorno de UWP (`vcvarsall x64 uwp`, que busca con `vswhere`) y configura con
**Ninja**. No con el generador de Visual Studio: es multiconfiguración y este framework escribe
un archivo de versión por configuración, que CMake rechaza con *«Evaluation file to be written
multiple times»*.

Lo de `vcvarsall x64 uwp` importa por sí solo: pone en `LIB` el CRT del App Container, de modo
que el ejecutable importa `msvcp140_app.dll` en vez del `msvcp140.dll` de escritorio. Con
`vcvars64`, el paquete se instala y la consola se niega a activarlo.

Sale `Street_Fighter_EX2_Plus.exe` (unos 16,6 MB) en la carpeta de compilación. Un minuto largo.

## 6. Los mosaicos del paquete

Pon once PNG en `package/Assets/`. Este repositorio no trae ninguno: los nombres y las medidas
exactas están en [`ASSETS.md`](ASSETS.md). Valen imágenes de color liso.

## 7. Empaquetar y firmar

```powershell
pwsh -File tools/empaquetar-uwp.ps1 -Build <compilación> -Juego <proyecto> -Salida <carpeta> `
     -Certificado <huella> -Version 1.0.0.0
```

Reúne el ejecutable, el manifiesto, los mosaicos, la configuración inicial y los paquetes de
mods; rehace `resources.pri` con `makepri` (sin el bloque `<packaging>` de la configuración por
defecto, que parte el PRI por escala y hace que la consola lo rechace); empaqueta con
`makeappx`; y firma con tu certificado.

Para añadir un mod, `-Mod <carpeta del paquete>`. Con `-VCLibs` apuntando a
`Microsoft.VCLibs.x64.14.00.appx`, lo deja junto a la salida para instalarlo.

Sale `<identidad>_<versión>_x64.msix`, unos 8,5 MB. **El disco y la BIOS no van dentro**: van a
la consola aparte, en el paso 9.

## 8. Instalarlo en la consola

### 8.1 La dependencia: VCLibs

El ejecutable importa el CRT del App Container —`msvcp140_app.dll`, `vcruntime140_app.dll`,
`vccorlib140_app.dll`—, que no va dentro del paquete sino en un **paquete de marco** que hay que
instalar una vez en la consola. El manifiesto lo declara:

```xml
<PackageDependency Name="Microsoft.VCLibs.140.00" MinVersion="14.0.33519.0"
                   Publisher="CN=Microsoft Corporation, O=Microsoft Corporation, L=Redmond, S=Washington, C=US" />
```

**El archivo que hace falta es `Microsoft.VCLibs.x64.14.00.appx`** (unos 900 KB). Ya lo tienes:
lo instalan el SDK de Windows y Visual Studio, aquí —

```
C:\Program Files (x86)\Microsoft SDKs\Windows Kits\10\ExtensionSDKs\Microsoft.VCLibs\14.0\Appx\Retail\x64\Microsoft.VCLibs.x64.14.00.appx
```

⚠ **Hay dos archivos fáciles de coger por error, y ninguno vale:**

- `Microsoft.VCLibs.x64.14.00.Desktop.appx`, que es al que apunta `aka.ms`, es la versión del
  **puente de escritorio**. Es otro paquete, y la consola seguirá diciendo que falta la
  dependencia.
- `…\Appx\**Debug**\x64\Microsoft.VCLibs.x64.Debug.14.00.appx` solo sirve si firmas en
  configuración Debug. Este port se compila en Release.

Pasándole `-VCLibs <esa ruta>` a `empaquetar-uwp.ps1`, lo copia a `<salida>\Dependencies\`, así
el `.msix` y su dependencia quedan juntos y no hay que buscarla con el portal abierto.

Se instala **una vez por consola**: los paquetes siguientes, y las versiones siguientes de este,
ya la encuentran.

### 8.2 Subirlo

En el Device Portal (`https://<ip-de-la-consola>:11443`), en **My games & apps → Add**:

1. **App package** → tu `.msix`.
2. **Certificate** → no hace falta: el paquete va firmado y el modo desarrollador lo acepta.
3. **Optional packages / Dependency** → aquí es donde se añade
   `Microsoft.VCLibs.x64.14.00.appx`, la primera vez.
4. **Next → Install**, y esperar al *Package successfully registered*.

Si aun así dice que falta la dependencia, lo más seguro es que hayas añadido uno de los dos
archivos equivocados de 8.1.

### 8.3 Si sale `There is not enough space on the disk`

No es que la consola esté llena, y el mensaje engaña. **La primera instalación de una familia de
paquetes va a `D:\DevelopmentFiles`**, una partición de unos 5 GB que el modo desarrollador
guarda justo para eso; las *actualizaciones* de una familia ya registrada van a otro
almacenamiento. Esa partición se llena con la primera versión de todo lo que hayas instalado
alguna vez, y **desinstalar un juego no la vacía**: las carpetas se quedan ahí.

Así que la salida es conseguir que tu paquete entre como **actualización** y no como primera
instalación, con una *semilla*:

> Una **semilla** es un paquete con la **misma identidad** que el de verdad —mismo
> `Identity Name` y mismo `Publisher`— pero con una **versión más baja** y un **ejecutable
> mínimo** dentro. No tiene que arrancar nunca. Su único trabajo es registrar la familia en la
> consola, gastando poco, para que el paquete de verdad llegue como una actualización.

1. Haz una carpeta con cualquier `.exe` pequeño renombrado a `Street_Fighter_EX2_Plus.exe` (con
   un par de MB sobra: no se ejecuta nunca):

   ```powershell
   New-Item -ItemType Directory -Force <build-semilla> | Out-Null
   Copy-Item C:\Windows\System32\notepad.exe <build-semilla>\Street_Fighter_EX2_Plus.exe
   ```

2. Empaquétala con una **versión más baja** que la de verdad, y todo lo demás igual:

   ```powershell
   pwsh -File tools/empaquetar-uwp.ps1 -Build <build-semilla> -Juego <proyecto> -Salida <salida> `
        -Certificado <huella> -Version 0.0.0.1
   ```

3. Instala primero esa (8.2), con la dependencia de VCLibs.
4. Después vuelve a empaquetar el de verdad con su versión —`-Version 1.0.0.0`— e instálalo: el
   portal lo toma como actualización. Y entra.

De ahí en adelante, con mantener la versión real por encima de la de la semilla, no vuelves a
toparte con esto en este paquete. Si `D:\DevelopmentFiles` está de verdad lleno de primeras
versiones huérfanas de otras cosas, se pueden borrar por la API de archivos del portal con
`knownfolderid=DevelopmentFiles` —primero los archivos y después las carpetas ya vacías—, pero
eso es mantenimiento de tu consola, no parte de instalar esto.

## 9. El disco y la BIOS

Viven en la carpeta de datos de la propia aplicación, que crea el primer arranque:

```
…\Packages\<identidad>\LocalState\PSXRecomp\SLUS-01105\
    disc\    bios\    saves\    logs\
```

Se suben por el explorador de archivos del Device Portal, al `LocalState` de esta aplicación:

- la **BIOS**, a `bios\`;
- el **disco**, a `disc\`. El portal rechaza con un 500 la subida de los 447 MB de una vez, así
  que parte el `.bin` en trozos de **150 MiB** llamados `<disco>.bin.parte1`, `.parte2`… y sube
  esos: la entrada del port los une una sola vez, en el siguiente arranque, y los deja como
  respaldo. Sube también el `.cue`.

En cada arranque, la entrada **siembra** además `game.toml` y los mods desde dentro del paquete
(así una versión nueva llega de verdad), deja en paz `settings.toml`, `input.ini` y
`keybinds.ini` si ya existen —son tuyos—, escribe `bios.cfg` y `disc.cfg` con rutas
**absolutas**, y redirige la salida del runtime a `logs\salida.txt` y `logs\errores.txt`.

Lee esos dos registros. En una consola son lo único que tienes.

## Si algo no sale bien

| Síntoma | Causa |
|---|---|
| `Failed to launch the application` | Lo causan seis cosas, y cada una tapa a la siguiente. [`HOW-IT-WORKS.md`](HOW-IT-WORKS.md) §1 las lista con su pinta. La que más se queda a mano es la **dependencia de VCLibs que falta en el manifiesto** |
| El paquete instala pero no sale ventana | Mira `logs\errores.txt`. Si dice `Could not initialize OpenGL / GLES library`, el renderizador por software no se fijó antes de crear la ventana: el paso 4 no llegó al final |
| `trusted plugin is unavailable: sfex2p.widescreen` | El plugin del mod 16:9 no está dentro del ejecutable. Hace falta `parche_uwp_plugin_16_9.py` (paso 14 del perfil) y el código del plugin en el proyecto |
| `package does not target this game/image` | Los mods se validan antes de resolver el disco. El empaquetador quita la clave `disc` del `game.toml` que va dentro y `parche_uwp_disco_mods.py` lo resuelve antes; si rehiciste el paquete a mano, esa clave habrá vuelto |
| No hay mando | Todas las ranuras tienen que estar en «auto» (`parche_uwp_mando.py`). Cuando funciona, el registro dice `opened controller for slot:` |
| No guarda nada | `memcard_dir` es una ruta relativa y se resuelve contra la carpeta de instalación, que es de solo lectura. `parche_uwp_escritura.py` la vuelve a anclar; el registro lo confirma con `UWP — writable state directory = …` |
| El juego empieza de cero al volver de Home | Es lo normal sin `parche_uwp_reanudar.py`: el modo desarrollador termina un juego suspendido. Con él, la máquina se guarda cada 10 segundos y se restaura al relanzar |
| Las peleas bajan de 60 FPS en 16:9 | Los dos últimos pasos del perfil (`parche_wide_splice.py` y `parche_wide_bandas.py`) son los que recuperan eso |
