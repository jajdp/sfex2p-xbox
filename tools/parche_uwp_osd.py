# -*- coding: utf-8 -*-
# El aviso en pantalla (y con él el contador de FPS), encendido en la consola.
#
# `host_osd.c` dibuja los avisos de la esquina —y el estado permanente con los FPS— con su propia fuente de 8x8
# incrustada, pero todo eso está detrás de `#if defined(RECOMP_LAUNCHER)`: solo se compila cuando el producto lleva
# el lanzador de recomp-ui. En la consola el lanzador va apagado, así que `host_osd_set_status()` no hacía nada y
# el contador de FPS únicamente iba al **rótulo de la ventana**, que en la Xbox no se ve. Ese era el motivo de que
# el contador no apareciera aunque estuviese encendido.
#
# El parche lo enciende también para el perfil UWP. No hace falta nada de recomp-ui: la fuente y el dibujo (que va
# por el SDL_Renderer, el mismo que presenta la imagen del juego) están enteros en ese archivo.
#
# Idempotente y todo o nada; escritura atómica.
# Uso: parche_uwp_osd.py <raíz del proyecto del juego>
import os
import sys

if len(sys.argv) < 2:
    sys.exit('uso: %s <ruta de la raiz del proyecto del juego>' % os.path.basename(sys.argv[0]))
RAIZ = sys.argv[1]
MARCA = 'Recompilaciones (2026-10-05): UWP — on-screen OSD'

VIEJO = '''#if defined(RECOMP_LAUNCHER)
#define HOST_OSD_VISUAL 1
#else
#define HOST_OSD_VISUAL 0
#endif'''

NUEVO = '''/* ''' + MARCA + '''. The console has no launcher and no window title bar,
 * so without this the FPS readout had nowhere to go: the toast/status layer is the only way to show it.
 * Nothing here needs recomp-ui — the 8x8 font and the blit live in this file. */
#if defined(RECOMP_LAUNCHER) || defined(PSX_UWP)
#define HOST_OSD_VISUAL 1
#else
#define HOST_OSD_VISUAL 0
#endif'''


def main():
    ruta = os.path.join(RAIZ, 'psxrecomp', 'runtime', 'src', 'host_osd.c')
    with open(ruta, 'rb') as f:
        crudo = f.read().decode('utf-8')
    eol = '\r\n' if '\r\n' in crudo else '\n'
    t = crudo.replace('\r\n', '\n')
    if MARCA in t:
        print('el parche ya estaba')
        return
    if t.count(VIEJO) != 1:
        raise SystemExit('host_osd.c: %d apariciones del ancla' % t.count(VIEJO))
    t = t.replace(VIEJO, NUEVO)
    with open(ruta + '.tmp', 'w', encoding='utf-8', newline='') as f:
        f.write(t.replace('\n', eol))
    os.replace(ruta + '.tmp', ruta)
    print('host_osd.c: el aviso en pantalla se compila también para la consola')


if __name__ == '__main__':
    main()
