# -*- coding: utf-8 -*-
# El plugin del 16:9 en la consola.
#
# El 16:9 de este juego es propiedad de un mod (`sfex2p.widescreen`) y el mod no se puede activar sin su «plugin de
# confianza», que es código del juego compilado DENTRO del ejecutable: `sfex2p_widescreen.c`. El CMakeLists del juego
# lo pasa en `CODEGEN_SETUP_SOURCES`, pero el framework solo añade esa lista **cuando se compila con recomp-ui**
# (runtime.cmake: `if(PSX_RECOMP_UI) list(APPEND _psxg_extras ${PSXG_CODEGEN_SETUP_SOURCES})`), porque el otro
# archivo de la lista —el anfitrión de la generación— incluye las cabeceras del lanzador. En la consola recomp-ui va
# apagado, así que el plugin no entraba y el runtime se negaba a arrancar:
#     psxrecomp: cannot launch with selected mods: sfex2p.widescreen/widescreen:
#                trusted plugin is unavailable: sfex2p.widescreen
# El parche lo añade aparte cuando no hay recomp-ui: el plugin solo necesita el runtime.
#
# Y la segunda mitad, para MSVC: el registro usa un puntero a función en la sección «.CRT$XCU», declarado `static`
# (mod_plugins.h). Con clang —el compilador del juego en Windows— ese camino no se usa (allí el registro es
# `__attribute__((constructor))`), pero con MSVC, que es el compilador de la consola, una variable estática a la
# que nadie hace referencia se puede quedar fuera al enlazar y el plugin no llegaría a registrarse nunca. Se le
# quita el `static` y se fuerza su inclusión con `/include:`, que es la receta de Microsoft para los inicializadores
# de esa sección.
#
# Idempotente y todo o nada; escritura atómica.
# Uso: parche_uwp_plugin_16_9.py <raíz del proyecto del juego>
import os
import re

import parchear

MARCA = 'Recompilaciones (2026-10-05): the 16:9 plugin without recomp-ui'
MARCA2 = 'Recompilaciones (2026-10-05): MSVC'

JUEGO_VIEJO = '''if(CMAKE_SYSTEM_NAME STREQUAL "WindowsStore")'''

JUEGO_NUEVO = '''# ''' + MARCA + '''. Widescreen belongs to the sfex2p.widescreen mod, and the
# mod demands its trusted plugin inside the executable. The framework only compiles CODEGEN_SETUP_SOURCES when
# recomp-ui is present (its other file needs the launcher's headers), and recomp-ui is off on the console:
# without this, the runtime refuses to start with "trusted plugin is unavailable: sfex2p.widescreen".
if(NOT PSX_RECOMP_UI)
    target_sources(psx-runtime PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/sfex2p_widescreen.c")
endif()

if(CMAKE_SYSTEM_NAME STREQUAL "WindowsStore")'''

# La línea del puntero de la sección, tal cual esté alineada en el archivo.
MOD_PATRON = re.compile(
    r'( *)static (void \(__cdecl\* name##_constructor\)\(void\) = name;)( *)\\\n')
MOD_CAMBIO = (
    '\\1/* ' + MARCA2 + ': no `static`, plus /include:, so the linker does not drop an\\3\\\\\n'
    '\\1 * initializer nothing references: the plugin would never register. */\\3\\\\\n'
    '\\1\\2\\3\\\\\n'
    '\\1__pragma(comment(linker, "/include:" #name "_constructor"))\\3\\\\\n')


def parchear_macro(ruta):
    """La macro del registro va por expresión regular: hay que respetar su alineación y sus `\\`."""
    texto, eol = parchear.leer(ruta, 'utf-8-sig')
    if MARCA2 in texto:
        return None
    nuevo, n = MOD_PATRON.subn(MOD_CAMBIO, texto)
    if n != 1:
        raise SystemExit('mod_plugins.h: %d apariciones del ancla' % n)
    parchear.escribir(ruta, nuevo, eol, 'utf-8-sig')
    return 'mod_plugins.h (el registro sobrevive al enlazador de MSVC)'


def main():
    raiz = parchear.raiz()
    parchear.informe(
        parchear.aplicar(os.path.join(raiz, 'CMakeLists.txt'), [(JUEGO_VIEJO, JUEGO_NUEVO)], MARCA,
                         'CMakeLists.txt (el plugin se compila sin recomp-ui)'),
        parchear_macro(parchear.runtime(raiz, 'include', 'mod_plugins.h')))


if __name__ == '__main__':
    main()
