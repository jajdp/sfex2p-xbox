# Lo que le faltaba al perfil UWP para que la consola pueda ARRANCAR la aplicación. En las importaciones del
# ejecutable sobraban dos cosas (ws2_32 NO era una de ellas: un ejecutable que arranca también la importa):
#   1. `OPENGL32.dll` — el backend GL del runtime (`gpu_gl_renderer.c`) llama a GL 1.x directamente, y esa DLL no
#      existe en la consola. El sustituto inerte está en `src/gpu_gl_renderer_stub.c` de este repositorio: define
#      los mismos símbolos para que el resto del runtime enlace igual, y el perfil UWP lo compila en lugar del
#      original, con lo que el runtime se queda con el dibujo por software, que es lo que usa la consola.
#   2. `dbghelp`, `comdlg32` y `opengl32` en el enlace: en el App Container no existen, y basta con importarlas para
#      que la aplicación no se active. En UWP no hay que enlazar ninguna: `WindowsApp.lib` —la biblioteca paraguas
#      que CMake pone cuando CMAKE_SYSTEM_NAME es WindowsStore— ya trae lo permitido, los sockets incluidos.
# Idempotente y todo o nada; escritura atómica.
# Uso: parche_uwp_gl.py <raíz del proyecto del juego>
import os
import shutil

import parchear

MARCA = 'Recompilaciones (2026-10-05): UWP without OpenGL'

SUSTITUTO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         'src', 'gpu_gl_renderer_stub.c')
CAMBIOS = [
    # 1. la selección de la fuente del backend GL, justo antes de la lista de fuentes del runtime
    ('''set(PSXRECOMP_RUNTIME_SOURCES
    ${PSXRECOMP_ROOT}/runtime/src/main.cpp''',
     '''# ''' + MARCA + ''': there is no opengl32.dll on the console, and merely importing it stops the
# app from being activated. The UWP profile compiles an inert replacement and the runtime keeps to
# the software rasterizer.
if(PSX_UWP)
    set(PSXRECOMP_GL_RENDERER_SOURCE
        ${PSXRECOMP_ROOT}/runtime/src/gpu_gl_renderer_stub.c)
else()
    set(PSXRECOMP_GL_RENDERER_SOURCE
        ${PSXRECOMP_ROOT}/runtime/src/gpu_gl_renderer.c)
endif()

set(PSXRECOMP_RUNTIME_SOURCES
    ${PSXRECOMP_ROOT}/runtime/src/main.cpp'''),

    # 2. la fuente, dentro de la lista
    ('''    ${PSXRECOMP_ROOT}/runtime/src/gpu_gl_renderer.c
    ${PSXRECOMP_ROOT}/runtime/src/gpu_vk_renderer.c''',
     '''    ${PSXRECOMP_GL_RENDERER_SOURCE}
    ${PSXRECOMP_ROOT}/runtime/src/gpu_vk_renderer.c'''),

    # 3. el enlace: en UWP, ninguna de las cuatro bibliotecas de escritorio
    ('''    if(WIN32 OR MINGW)
        # opengl32: GL backend (gpu_gl_renderer.c). GL 1.x is exported directly''',
     '''    if(PSX_UWP)
        # ''' + MARCA + ''': opengl32, dbghelp and comdlg32 do not exist in the App Container, and
        # importing them is enough to stop the console from activating the app. Nothing has to be
        # linked here: WindowsApp.lib - the umbrella library CMake adds for WindowsStore - already
        # carries what is allowed, the lobby client's sockets included.
    elseif(WIN32 OR MINGW)
        # opengl32: GL backend (gpu_gl_renderer.c). GL 1.x is exported directly'''),
]


def main():
    raiz = parchear.raiz()
    if not os.path.isfile(SUSTITUTO):
        raise SystemExit('falta en el repositorio: src/gpu_gl_renderer_stub.c')
    # Primero el runtime.cmake, que es lo que puede no cuadrar: si muere ahí, el árbol se queda
    # sin tocar. El sustituto se copia solo cuando el cmake ya quedó escrito, y por eso mismo una
    # segunda pasada no lo repone — para eso está la marca, que dice que el parche ya estaba.
    hecho = parchear.aplicar(parchear.runtime(raiz, 'runtime.cmake'), CAMBIOS, MARCA,
                             'runtime.cmake: %d cambios (UWP sin OpenGL)' % len(CAMBIOS),
                             'utf-8-sig')
    if hecho:
        shutil.copyfile(SUSTITUTO, parchear.runtime(raiz, 'src', 'gpu_gl_renderer_stub.c'))
        hecho = 'gpu_gl_renderer_stub.c copiado; ' + hecho
    parchear.informe(hecho)


if __name__ == '__main__':
    main()
