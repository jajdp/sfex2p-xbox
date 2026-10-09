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
import sys

if len(sys.argv) < 2:
    sys.exit('uso: %s <ruta de la raiz del proyecto del juego>' % os.path.basename(sys.argv[0]))
RAIZ = sys.argv[1]
MARCA = 'Recompilaciones (2026-10-05): el plugin del 16:9 sin recomp-ui'
MARCA2 = 'Recompilaciones (2026-10-05): MSVC'

JUEGO_VIEJO = '''if(CMAKE_SYSTEM_NAME STREQUAL "WindowsStore")'''

JUEGO_NUEVO = '''# ''' + MARCA + '''. El 16:9 es propiedad del mod sfex2p.widescreen y el mod
# exige su plugin de confianza dentro del ejecutable. El framework solo compila CODEGEN_SETUP_SOURCES cuando hay
# recomp-ui (su otro archivo necesita las cabeceras del lanzador), y en la consola recomp-ui va apagado: sin esto,
# el runtime se niega a arrancar con «trusted plugin is unavailable: sfex2p.widescreen».
if(NOT PSX_RECOMP_UI)
    target_sources(psx-runtime PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/sfex2p_widescreen.c")
endif()

if(CMAKE_SYSTEM_NAME STREQUAL "WindowsStore")'''

# La línea del puntero de la sección, tal cual esté alineada en el archivo.
MOD_PATRON = re.compile(
    r'( *)static (void \(__cdecl\* name##_constructor\)\(void\) = name;)( *)\\\n')
MOD_CAMBIO = (
    '\\1/* ' + MARCA2 + ': sin `static` y con /include:, para que el enlazador no se lleve\\3\\\\\n'
    '\\1 * por delante un inicializador al que nadie hace referencia: el plugin no se registraría. */\\3\\\\\n'
    '\\1\\2\\3\\\\\n'
    '\\1__pragma(comment(linker, "/include:" #name "_constructor"))\\3\\\\\n')


def parchear(ruta, viejo, nuevo, marca, codificacion='utf-8'):
    with open(ruta, 'rb') as f:
        crudo = f.read().decode(codificacion)
    eol = '\r\n' if '\r\n' in crudo else '\n'
    t = crudo.replace('\r\n', '\n')
    if marca in t:
        return False
    if t.count(viejo) != 1:
        raise SystemExit('%s: %d apariciones del ancla' % (os.path.basename(ruta), t.count(viejo)))
    t = t.replace(viejo, nuevo)
    with open(ruta + '.tmp', 'w', encoding=codificacion, newline='') as f:
        f.write(t.replace('\n', eol))
    os.replace(ruta + '.tmp', ruta)
    return True


def parchear_macro(ruta):
    with open(ruta, 'rb') as f:
        crudo = f.read().decode('utf-8-sig')
    eol = '\r\n' if '\r\n' in crudo else '\n'
    t = crudo.replace('\r\n', '\n')
    if MARCA2 in t:
        return False
    t2, n = MOD_PATRON.subn(MOD_CAMBIO, t)
    if n != 1:
        raise SystemExit('mod_plugins.h: %d apariciones del ancla' % n)
    with open(ruta + '.tmp', 'w', encoding='utf-8-sig', newline='') as f:
        f.write(t2.replace('\n', eol))
    os.replace(ruta + '.tmp', ruta)
    return True


def main():
    hechos = []
    if parchear(os.path.join(RAIZ, 'CMakeLists.txt'), JUEGO_VIEJO, JUEGO_NUEVO, MARCA):
        hechos.append('CMakeLists.txt (el plugin se compila sin recomp-ui)')
    if parchear_macro(os.path.join(RAIZ, 'psxrecomp', 'runtime', 'include', 'mod_plugins.h')):
        hechos.append('mod_plugins.h (el registro sobrevive al enlazador de MSVC)')
    print('; '.join(hechos) if hechos else 'el parche ya estaba')


if __name__ == '__main__':
    main()
