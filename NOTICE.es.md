# Aviso

*(English: [NOTICE.md](NOTICE.md))*

## Sin afiliación

Esto es un proyecto de aficionados, no oficial y sin ánimo de lucro. **No está afiliado a
Capcom, Arika, Sony ni Microsoft**, ni a ninguna de sus filiales, ni cuenta con su respaldo;
tampoco está afiliado a los autores del framework
[PSXRecomp](https://github.com/RetroPortingToolKit/psxrecomp) ni a los del
[proyecto del juego](https://github.com/strider973/Street-Fighter-EX2-Plus-Recompiled) sobre el
que se construye este port. *Street Fighter*, *Street Fighter EX2 Plus*, *Xbox* y todos los
nombres y marcas relacionados son propiedad de sus respectivos titulares, y aquí se usan
únicamente para decir con qué funciona esto.

Aquí no se vende nada y no se monetiza nada.

## Lo que este repositorio no distribuye

Ni código del juego. Ni imagen del disco. Ni BIOS. Ni ejecutable compilado. Ni paquete `.msix`.
Ni partidas guardadas. Ni arte, ni audio, ni música, ni letras del juego: **tampoco los mosaicos
del paquete**, y por eso `package/Assets/` está vacío y [`docs/ASSETS.md`](docs/ASSETS.md) te
pide que pongas los tuyos.

Por sí solo, nada de lo que hay aquí produce un juego jugable. Hace falta tu propia copia
legítima del disco, una BIOS retail y una compilación del proyecto del juego que funcione, y
este repositorio no da ninguna de las tres, ni puede darlas.

## Lo que sí contiene de obra ajena

**Parches contra el framework PSXRecomp.** Los dieciséis scripts citan en total **117 líneas**
del código del framework: son las anclas que cada parche comprueba antes de escribir, para
fallar del lado seguro en vez de estropear un árbol que no reconoce. PSXRecomp lo publica su
autor bajo la PolyForm Noncommercial License 1.0.0, que permite obras derivadas no comerciales;
este repositorio es una de ellas y se publica bajo [esa misma licencia](LICENSE).

**Cero líneas del proyecto del juego.** `strider973/Street-Fighter-EX2-Plus-Recompiled` no tiene
licencia, así que de él no se reproduce nada. El instalador se ancla en los nombres de
parámetro del propio CMake y añade su bloque al final del archivo, que no necesita ancla alguna.

**`src/SDL_winrt_main_NonXAML.cpp`** es la entrada WinRT de SDL, *puesta en dominio público por
David Ludwig*, con los cambios que este port necesitaba (el directorio temporal del paquete, la
carpeta de datos que siembra en cada arranque y la redirección del registro). El original forma
parte de [SDL](https://github.com/libsdl-org/SDL).

**Aquí no hay ninguna captura.** La que había —la pantalla de título del juego en una consola—
es sobre todo el logotipo y la marca de Capcom, así que se quitó. Una captura se ganaría su
sitio enseñando el trabajo; esa enseñaba arte ajeno.

## Retirada y contacto

Si tienes derechos sobre este material y quieres que algo de aquí se retire o se cambie,
escribe a **jajdpmail@gmail.com** diciendo a qué te opones y en calidad de qué escribes.

Las peticiones de los titulares de derechos se atienden: se quita la parte en disputa, o se
retira el repositorio entero, sin discutirlo, y recibirás una respuesta confirmándolo. No hace
falta ningún aviso ni trámite legal más allá de ese correo para llegar a quien mantiene esto.
