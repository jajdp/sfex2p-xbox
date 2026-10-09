# -*- coding: utf-8 -*-
# El renderizador de la consola es el de software, y hay que saberlo ANTES de crear la ventana.
#
# En la consola no hay OpenGL (el backend GL es un sustituto inerte, `parche_uwp_gl.py`). El runtime ya lo detecta
# y avisa —«renderer = opengl requested but unavailable — falling back to software»—, pero ese cambio llega tarde:
# la preferencia `g_video_renderer` sigue valiendo «opengl» cuando se crea la ventana, y entonces se le pide a SDL
# una ventana con contexto GL, que en la Xbox falla y se lleva por delante el arranque entero:
#     SDL_CreateWindow failed: Could not initialize OpenGL / GLES library
# El parche fija el renderizador por software en el perfil UWP, justo antes de elegir el backend.
#
# Idempotente y todo o nada; escritura atómica.
# Uso: parche_uwp_render_software.py <raíz del proyecto del juego>
import os
import sys

if len(sys.argv) < 2:
    sys.exit('uso: %s <ruta de la raiz del proyecto del juego>' % os.path.basename(sys.argv[0]))
RAIZ = sys.argv[1]
MARCA = 'Recompilaciones (2026-10-05): UWP — software renderer'

ANCLA = '''    s_netplay_gl_present = 0;
    s_netplay_sim_native_scale = 0;
    gl_renderer_set_cpu_auth_dual(0);'''

# El mismo trío aparece dos veces en main.cpp: hay que llevarse también el comentario de encima.
VIEJO = ''' * present not yet cpu-auth — fall back to a software window. */
''' + ANCLA

NUEVO = ''' * present not yet cpu-auth — fall back to a software window. */
''' + ANCLA + '''
#if defined(PSX_UWP)
    /* ''' + MARCA + '''. There is no opengl32 on the console and the GL
     * backend is an inert stub, so software is the only renderer. This must be settled HERE, before the
     * window is created: SDL_WINDOW_OPENGL makes SDL ask for a GL context, which fails on Xbox and takes
     * the whole launch down ("SDL_CreateWindow failed: Could not initialize OpenGL / GLES library"). */
    if (g_video_renderer != 0) {
        std::fprintf(stdout,
                     "psxrecomp: UWP — forcing the software renderer (no OpenGL on the console)\\n");
        g_video_renderer = 0;
    }
#endif'''


def main():
    ruta = os.path.join(RAIZ, 'psxrecomp', 'runtime', 'src', 'main.cpp')
    with open(ruta, 'rb') as f:
        crudo = f.read().decode('utf-8')
    eol = '\r\n' if '\r\n' in crudo else '\n'
    t = crudo.replace('\r\n', '\n')
    if MARCA in t:
        print('el parche ya estaba')
        return
    if t.count(VIEJO) != 1:
        raise SystemExit('main.cpp: %d apariciones del ancla' % t.count(VIEJO))
    t = t.replace(VIEJO, NUEVO)
    with open(ruta + '.tmp', 'w', encoding='utf-8', newline='') as f:
        f.write(t.replace('\n', eol))
    os.replace(ruta + '.tmp', ruta)
    print('main.cpp: en la consola, renderizador por software antes de crear la ventana')


if __name__ == '__main__':
    main()
