# Cómo funciona el port

Qué cambian de verdad los dieciséis parches, y por qué existe cada uno. Todos salen de un fallo
real en una consola real, en este orden, cada uno escondiendo al siguiente.

*(English: [HOW-IT-WORKS.md](HOW-IT-WORKS.md))*

Si solo quieres construirlo, lee antes [`INSTALL.es.md`](INSTALL.es.md).

## 0. Por qué un perfil desde cero

El framework que usa este juego **no tiene ningún soporte de UWP**. No había un perfil
`WindowsStore` que encender, así que `parche_uwp.py` escribe uno en `runtime/runtime.cmake`:

| Pieza | Por qué |
|---|---|
| `PSX_UWP` cuando `CMAKE_SYSTEM_NAME` es `WindowsStore` | El interruptor del que cuelga todo lo demás |
| Sin servidor de depuración, sin lanzador, sin Vulkan | No caben en una consola |
| SDL2 por `find_package` | **SDL3 no tiene WinRT**, así que la compilación necesita `-DPSX_SDL_BACKEND=SDL2` y un SDL2 compilado para WindowsStore |
| `NOMINMAX` | En UWP el identificador de plataforma es `WindowsStore`, **no** `Windows`, así que el guard que normalmente esconde las macros `min`/`max` de `windows.h` no se activa y `mod_runtime.cpp` falla con *«illegal token on right side of ::»* |
| `WINAPI_FAMILY=WINAPI_FAMILY_APP` | Con el generador Ninja, CMake no la pone, y sin ella SDL2 no se ve como WinRT y nunca exporta `SDL_WinRTRunApp` |
| `SDL_MAIN_HANDLED` **sin** definir en UWP | Así SDL renombra `main()` a `SDL_main()`, que es a quien llama la entrada WinRT |
| `/APPCONTAINER` al enlazar | La consola solo activa aplicaciones marcadas así. Sin eso, el paquete instala y no arranca |

**El generador tiene que ser Ninja.** El de Visual Studio es multiconfiguración, y este framework
emite un archivo de versión por configuración, lo que CMake rechaza: *«Evaluation file to be
written multiple times»*.

## 1. Los seis fallos del arranque

Durante un día la compilación iba bien, el paquete instalaba, y el Device Portal respondía
**«Failed to launch the application»** y nada más. No era un problema: eran seis.

Dos cosas lo hicieron abordable, y las dos vale la pena robarlas: comparar las **importaciones del
PE** del ejecutable contra las de un port que sí arranca, y **redirigir la salida del runtime a
`logs\`** desde la entrada — en una consola la salida estándar no va a ninguna parte, así que sin
eso se trabaja a ciegas.

| # | Qué estaba mal | Arreglo |
|---|---|---|
| 1 | El ejecutable importaba **`OPENGL32.dll`**, que no existe en la consola | `gpu_gl_renderer_stub.c`: un backend GL inerte que expone los 39 símbolos del original (sacados con `dumpbin /symbols`), y el bloque de enlace `if(WIN32 OR MINGW)` excluido en UWP. `WindowsApp.lib` ya aporta lo permitido, **sockets incluidos** — `ws2_32` nunca fue el problema, el port que funciona también la importa. `parche_uwp_gl.py` |
| 2 | Importaba el **CRT de escritorio** (`msvcp140.dll`) y `kernel32.dll` | Compilar dentro de **`vcvarsall x64 uwp`**, no de `vcvars64`, para que `LIB` apunte al CRT de App Container y las importaciones pasen a ser `msvcp140_app.dll`, `vcruntime140_app.dll` y `vccorlib140_app.dll` |
| 3 | El manifiesto **no declaraba el paquete VCLibs** | `<PackageDependency Name="Microsoft.VCLibs.140.00" …>`. MSBuild lo añade solo; un manifiesto escrito a mano, no. **Era lo que de verdad impedía la activación** |
| 4 | **Fibras y objetos de trabajo**: el App Container no tiene `CreateFiber`, `ConvertThreadToFiber` ni `TerminateJobObject` | Las variantes `…Ex` para las fibras, y fuera la llamada muerta a `autocompile`. `parche_uwp_appcontainer.py` |
| 5 | El runtime **ancla todos sus archivos al directorio del ejecutable**, que en UWP es de solo lectura | `exe_dir_from_argv` devuelve la carpeta de datos (§2). `parche_uwp_rutas.py` |
| 6 | Aun después de que el runtime avisara de que caía a software, la ventana se seguía pidiendo con contexto GL: `SDL_CreateWindow failed: Could not initialize OpenGL / GLES library` | Fijar el renderizador por software **antes** de crear la ventana. `parche_uwp_render_software.py` |

## 2. La carpeta de datos, y el disco

El runtime dice en sus propios comentarios que su ancla es el directorio del ejecutable y **nunca**
el directorio de trabajo. En una consola eso es la carpeta de instalación del paquete, de solo
lectura, así que el perfil lo apunta a

```text
…\Packages\<identidad>\LocalState\PSXRecomp\SLUS-01105\
```

obtenida de la carpeta temporal del paquete subiendo dos niveles: así nada tiene que inicializar el
Windows Runtime antes que SDL.

La entrada WinRT (`src/SDL_winrt_main_NonXAML.cpp`) prepara esa carpeta en cada arranque: crea
`disc\`, `bios\`, `saves\` y `logs\`; **siembra** lo que trae el paquete (`game.toml` y los mods
siempre, para que un paquete nuevo los actualice de verdad; `settings.toml`, `input.ini` y
`keybinds.ini` solo si faltan, porque esos son del jugador); **une el disco** a partir de las partes
de 150 MiB que el Device Portal obliga a subir; escribe `bios.cfg` y `disc.cfg` con rutas
**absolutas**, ya que una relativa se resolvería contra el directorio de trabajo; y redirige
`stdout`/`stderr` a `logs\`, sin buffer, porque una caída perdería justo lo que hace falta leer.

### El disco se resuelve DESPUÉS de validar los mods

El framework valida los paquetes de mods —y la huella de disco que cada uno exige— **antes** de
averiguar dónde está el disco: `mod_runtime_commit()` corre unas líneas antes que
`resolve_disc_for_runtime()`. Hasta entonces la única ruta que tiene es la del `game.toml`, que es
la del PC de quien generó el proyecto. En una consola eso daba una huella vacía, y **ningún mod con
`disc_sha256` llegaba a aplicarse**: los menús en español se rechazaban con
`package does not target this game/image`, mientras el mod de 16:9 pasaba porque no exige ninguna
huella. Arreglado por los dos lados: el empaquetador quita esa clave del `game.toml` que va dentro,
y `parche_uwp_disco_mods.py` resuelve el disco justo antes de la comprobación.

## 3. El plugin, el mando, el contador de FPS

- **El plugin del 16:9.** El aspecto ancho es del mod `sfex2p.widescreen`, y un mod con plugin de
  confianza no se puede activar si ese plugin no está dentro del ejecutable. El framework solo
  compila `CODEGEN_SETUP_SOURCES` **cuando recomp-ui está encendido**, y en una consola está
  apagado, así que el runtime se negaba a arrancar con
  `trusted plugin is unavailable: sfex2p.widescreen`. `parche_uwp_plugin_16_9.py` lo compila aparte
  y además arregla el registro para MSVC: el puntero de `.CRT$XCU` era `static` y el enlazador tenía
  derecho a tirarlo (con clang, que es el que construye la versión de PC, ese camino ni se usa).
- **El mando.** Sin lanzador que asigne dispositivos, una compilación de producto deja al jugador 1
  en el **teclado**, y una consola no tiene teclado: el mando no se abría y nadie lo decía. En UWP
  todas las ranuras van en «auto», el primer mando libre (`parche_uwp_mando.py`). El registro lo
  confirma: `opened controller for slot: Xbox One Game Controller`.
- **El contador de FPS.** El framework ya lo calcula, pero su capa visual (`host_osd.c`) está entera
  detrás de `#if defined(RECOMP_LAUNCHER)`: sin lanzador no se compila, y el número solo iba al
  **título de la ventana**, que en una consola no ve nadie. `parche_uwp_osd.py` lo habilita para el
  perfil UWP —no necesita recomp-ui, porque la fuente de 8×8 y el dibujado con `SDL_Renderer` viven
  en ese mismo archivo—, `parche_uwp_fps_encendido.py` lo deja encendido de fábrica, y
  `parche_uwp_fps_r3.py` ata **R3** al conmutador. Ese último es más delicado de lo que parece: la
  comprobación del botón tiene que ir sobre la **palabra de botones ya combinada** del jugador 1,
  justo antes de entregarla al SIO (`apply_pad_slot_to_sio`, bit 2, `0 = pulsado`). Ni el evento de
  SDL ni preguntar dentro de `pad_buttons_for()` funcionan.

## 4. 60 FPS en 16:9: empalmar el centro

**Medido, no supuesto.** En 16:9 las peleas iban a **51-55 FPS**; en 4:3, a 60-62. La causa: en modo
ancho el rasterizador por software dibuja **cada primitiva dos veces**, una en la VRAM canónica y
otra en la superficie ancha. Cronometrar esa segunda pasada —con un parche desechable que envolvía
cada bloque ancho en un contador de rendimiento e imprimía el total junto al contador de FPS— dio
**3,4-3,6 ms de cada cuadro**, a unas 25 000 primitivas por segundo. Un cuadro a 60 Hz son 16,68 ms.

La idea: el centro de la superficie ancha es una **copia 1:1 de la VRAM** —entre las dos solo hay la
traslación entera `wide_dx()`, así que con las mismas entradas salen los mismos píxeles—. Lo único
que añade la superficie ancha son los **márgenes**. Entonces:

1. al componer la imagen (`sw_render_wide_display`), las columnas del centro se leen **de la VRAM**,
   que ya está dibujada, y solo los márgenes salen de la superficie ancha;
2. la pasada ancha **se salta las primitivas que no llegan a un margen**, que en este juego son casi
   todas: sus escenarios están modelados para el cuadro 4:3;
3. y las que sí llegan se **recortan a la banda** a la que de verdad contribuyen, una pasada por
   margen, en vez de rasterizarse enteras.

(1) y (2) son `parche_wide_splice.py`; (3) es `parche_wide_bandas.py`.

| | Pasada ancha | FPS en pelea |
|---|---|---|
| Antes | 3,4-3,6 ms/cuadro | 51-55 |
| Con el empalme | 1,0-1,4 ms/cuadro | 56-62 |
| Con las bandas también | **0,7-0,8 ms/cuadro** | **60 sostenidos** (59-62) |

**Qué lo apaga.** El estirado del fondo 2D (`wide_bd_get`) sí reescribe el centro de la superficie
ancha, así que la primera vez que se usa, el empalme se desactiva solo para el resto de la sesión y
todo vuelve al camino antiguo. En este juego el estirado está apagado
(`[widescreen] nw_phase_backdrop = false`). También se queda apagado con el espejo de alta
resolución (escala > 1), que una consola no usa. En los dos casos tienes el rendimiento de antes y
la misma imagen.

## 5. Volver donde lo dejaste

El modo desarrollador **termina** un juego UWP que pasa a segundo plano —palabras de la propia
Microsoft: *«Games will be suspended and terminated in the background»*—. Volver desde Home
reiniciaba el juego. No es un fallo del port: el sistema relanza con
`PreviousExecutionState = Terminated` y espera que la aplicación se restaure sola.

Este framework pone fácil la parte difícil: `boot_state.c` serializa la máquina entera y
`savestate.c` lo ejecuta **en un punto seguro** (líder de bloque, sin excepción en vuelo). Lo único
que hacía falta era una **ranura reservada, la 99**, fuera de las doce del jugador.

Lo que **no** funcionó, medido en la consola:

| Intento | Qué pasó |
|---|---|
| `SDL_WINDOWEVENT` en el bucle de eventos | No llega nunca: la consola termina la aplicación antes |
| Un observador de eventos (`SDL_AddEventWatch`) | Estos **sí** llegan: `SDL_APP_WILLENTERBACKGROUND`, `FOCUS_LOST`, `DIDENTERBACKGROUND` |
| Esperar dentro del observador a que el guardado se ejecute | Interbloqueo: en WinRT el observador corre en el **mismo hilo** que el emulador (SDL lo llama desde `SDL_PumpEvents`), así que dormirse ahí bloquea justo el bucle que tiene que escribir |
| Pedir el guardado y dejar que siga | El emulador no vuelve a correr después del aviso, así que el `.pst` no se escribe nunca |

**Así que guarda mientras juegas**: cada 10 segundos en la ranura reservada, por el guardado
diferido del propio framework, y el último se restaura cuando la aplicación se relanza como
`Terminated`. Pierdes esos segundos como mucho. Un arranque normal **descarta** el estado guardado,
así que una sesión que terminó bien no se reanuda. `parche_uwp_reanudar.py`.

### Y el que llevaba escondido todo el tiempo

El registro lo decía con todas las letras:

```text
savestate: SAVE FAILED slot 99 -> S:\Program Files\WindowsApps\<paquete>\saves/...
```

Esa es la **carpeta de instalación**, de solo lectura. El `game.toml` se carga de ahí y su
`[runtime] memcard_dir = "saves"` es una ruta **relativa**, que se resuelve contra la carpeta de ese
archivo. O sea que **tanto las tarjetas de memoria como todos los estados guardados apuntaban a un
sitio donde no se puede escribir**, y el juego no había guardado nunca nada — nadie se había dado
cuenta, porque reanclar el runtime (§2) no cubre una ruta que llega ya resuelta desde `game.toml`.
`parche_uwp_escritura.py` la reancla, y el registro lo confirma al arrancar:

```text
psxrecomp: UWP — writable state directory = …\LocalState\PSXRecomp\SLUS-01105\saves
```
