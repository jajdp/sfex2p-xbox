# Street Fighter EX2 Plus en Xbox — el port UWP

Cómo coger la recompilación estática de *Street Fighter EX2 Plus* (PlayStation, 1999,
`SLUS-01105`) sobre [PSXRecomp](https://github.com/RetroPortingToolKit/psxrecomp) y hacerla
correr **en una Xbox Series en modo desarrollador**, como un paquete UWP que compilas y firmas
tú.

*(English: [README.md](README.md))*

No es teoría: el juego arranca, pasa por la BIOS y la presentación de Capcom, llega al título y
se juega con mando, en 16:9, a **60 FPS**, y vuelve donde lo dejaste cuando la consola lo
suspende.

## Qué es este repositorio

**Una receta y las herramientas que la aplican.** El framework de este juego no tiene soporte
UWP ninguno, así que el port es un perfil hecho desde cero: un perfil de CMake para
`WindowsStore`, una entrada WinRT y un juego de parches comprobados para lo que un App Container
no permite. Todo se aplica **sobre tu propia copia** del proyecto del juego, en tu máquina.

## Qué **no** es

Aquí no hay **código del juego, ni imagen de disco, ni BIOS, ni ejecutable compilado, ni paquete
`.msix`, ni arte**. Por sí solo no produce un juego jugable, y nada de lo que puedas descargar
aquí es un juego. Hace falta tu propio volcado del disco, una BIOS retail y una compilación del
proyecto del juego que ya funcione. Ver [`NOTICE.es.md`](NOTICE.es.md).

Los once mosaicos del paquete **tampoco están**: los que se usaron en la consola de verdad
salieron del arte del propio juego, que es de Capcom. Los pones tú —
[`docs/ASSETS.md`](docs/ASSETS.md) lista las medidas exactas, y el empaquetador se detiene con
un mensaje claro si falta alguno.

## Qué hace falta antes

| | |
|---|---|
| El proyecto del juego | [strider973/Street-Fighter-EX2-Plus-Recompiled](https://github.com/strider973/Street-Fighter-EX2-Plus-Recompiled) sobre el framework [PSXRecomp](https://github.com/RetroPortingToolKit/psxrecomp), clonado con `--recurse-submodules`, **compilando y funcionando antes en tu PC** |
| Tu propio disco | Un volcado NTSC-U de `SLUS-01105`, más una **BIOS retail SCPH-1001** — el proyecto va con `openbios = false`, así que la OpenBIOS incluida no sirve |
| Visual Studio 2022 | Con las herramientas de C++ y la carga de trabajo **UWP**, más Ninja y el SDK de Windows 10/11 |
| Un SDL2 para WindowsStore | SDL3 no tiene WinRT. El probado es el 2.30.2 |
| Una Xbox en modo desarrollador | Y un certificado para firmar: uno autofirmado vale ([`docs/INSTALL.es.md`](docs/INSTALL.es.md) §3) |

## Cómo va

```powershell
# 1. parchear tu copia del proyecto del juego (idempotente, atómico, no borra nada)
python tools/apply_uwp.py <ruta de la raíz del proyecto>

# 2. configurar y compilar con Ninja dentro del entorno de UWP
pwsh -File tools/configurar-uwp.ps1 -Raiz <proyecto> -Build <build> -Sdl2 <cmake de SDL2> -Compilar

# 3. empaquetar y firmar (tus mosaicos, tu certificado)
pwsh -File tools/empaquetar-uwp.ps1 -Build <build> -Juego <proyecto> -Salida <salida> -Certificado <huella>
```

Después se instala el `.msix` por el Device Portal y se suben el disco y la BIOS al
`LocalState` de la aplicación. Paso a paso, con la parte de la consola:
**[`docs/INSTALL.es.md`](docs/INSTALL.es.md)**.

## Qué tuvo que resolver

Cada una de estas fue un fallo real en la consola, y cada una tapaba a la siguiente. El detalle,
con lo que decía el registro en cada caso, está en
**[`docs/HOW-IT-WORKS.md`](docs/HOW-IT-WORKS.md)** (en inglés).

| | Síntoma | Arreglo |
|---|---|---|
| 1 | `Failed to launch the application` | Seis causas distintas: importar la `OPENGL32.dll` de escritorio, el CRT de escritorio, la dependencia de VCLibs que faltaba en el manifiesto, fibras y objetos de trabajo que el App Container no tiene, el runtime anclando sus archivos en una carpeta de solo lectura, y un contexto GL que se seguía pidiendo tras caer a software |
| 2 | Los mods se rechazaban sin decir nada | El framework valida los paquetes de mods —y la huella de disco que cada uno exige— *antes* de resolver dónde está el disco |
| 3 | Sin mando | Sin lanzador que asigne dispositivos, el jugador 1 se queda en el teclado, y en una consola no hay teclado |
| 4 | 51-55 FPS en 16:9 | El rasterizador por software dibujaba cada primitiva dos veces. El centro de la superficie ancha es una copia 1:1 de la VRAM, así que no hay que volver a dibujarlo: **60 sostenidos** |
| 5 | Empezaba de cero al volver de Home | El modo desarrollador termina un juego suspendido. El estado se guarda cada 10 segundos y se restaura al relanzar |
| 6 | No guardaba nunca nada | `memcard_dir` es relativa y se resolvía contra la carpeta de instalación, que es de solo lectura: las dos tarjetas y todos los estados |

## Los mods van aparte

El 16:9 y el menú en español son sus propios repositorios, y el empaquetador los toma con `-Mod`:

- [jajdp/sfex2p-widescreen](https://github.com/jajdp/sfex2p-widescreen) — 16:9 de verdad
- [jajdp/sfex2p-es](https://github.com/jajdp/sfex2p-es) — los menús en español

## Créditos y licencia

Port y herramientas de **Recompilaciones**. Publicado bajo la
[PolyForm Noncommercial License 1.0.0](LICENSE), la misma licencia del framework PSXRecomp del
que esto es una obra derivada.

Los scripts de parcheo llevan sus comentarios en español, que es donde se escribieron; la
documentación está en los dos idiomas.

*Street Fighter EX2 Plus* es © Capcom / Arika. Este proyecto no está afiliado a ellos, ni a
Sony, ni a Microsoft, ni al autor de PSXRecomp, y no distribuye nada que les pertenezca. El
detalle —qué hay y qué no hay aquí exactamente, y cómo pedir una retirada— está en
[`NOTICE.es.md`](NOTICE.es.md). Los titulares de derechos pueden escribir a
**jajdpmail@gmail.com**.
