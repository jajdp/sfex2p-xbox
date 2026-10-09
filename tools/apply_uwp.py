#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aplica el perfil UWP completo a un árbol de Street Fighter EX2 Plus (PSXRecomp).

Uso:
    python tools/apply_uwp.py <raíz del proyecto del juego>
    python tools/apply_uwp.py --list

La raíz es la carpeta con CMakeLists.txt y game.toml. Cada paso es idempotente y comprueba lo que espera
encontrar antes de escribir, así que pasarlo dos veces no cambia nada y, si un paso no reconoce el árbol,
se detiene ahí en vez de dejarlo a medias.

Después de esto: tools/configurar-uwp.ps1 (configura y compila) y tools/empaquetar-uwp.ps1 (empaqueta y
firma). Ver docs/INSTALL.es.md.

Recompilaciones — https://github.com/jajdp/sfex2p-xbox
PolyForm Noncommercial License 1.0.0
"""
import os
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERR = os.path.join(REPO, 'tools')
ENTRADA = os.path.join(REPO, 'src', 'SDL_winrt_main_NonXAML.cpp')

MARCA = 'sfex2p-xbox (Recompilaciones)'

# El orden importa: el perfil primero, y las dos pasadas del ancho al final, la de bandas sobre la del
# empalme. Cada paso dice qué resuelve; el detalle está en docs/HOW-IT-WORKS.md.
PASOS = [
    ('parche_uwp.py',                 'el perfil UWP del runtime (runtime.cmake)'),
    ('parche_uwp_gl.py',              'quitar la importación de OPENGL32.dll (backend GL inerte)'),
    ('parche_uwp_codigo.py',          'las guardas de código del perfil'),
    ('parche_uwp_appcontainer.py',    'fibras y objetos de trabajo que el App Container no tiene'),
    ('parche_uwp_rutas.py',           'anclar los archivos del runtime en la carpeta de datos'),
    ('parche_uwp_render_software.py', 'fijar el renderizador por software antes de crear la ventana'),
    ('parche_uwp_disco_mods.py',      'resolver el disco antes de validar los mods'),
    ('parche_uwp_escritura.py',       'tarjetas de memoria y estados en una carpeta donde se pueda escribir'),
    ('parche_uwp_mando.py',           'todas las ranuras en «auto»: en la consola no hay teclado'),
    ('parche_uwp_osd.py',             'la capa visual del contador de FPS, sin lanzador'),
    ('parche_uwp_fps_encendido.py',   'el contador, encendido de fábrica'),
    ('parche_uwp_fps_r3.py',          'R3 conmuta el contador'),
    ('parche_uwp_reanudar.py',        'guardar cada 10 s y volver donde lo dejaste tras la suspensión'),
    ('parche_uwp_plugin_16_9.py',     'compilar el plugin del mod 16:9 sin recomp-ui'),
    ('parche_wide_splice.py',         'el empalme del centro: no dibujar dos veces lo ya dibujado'),
    ('parche_wide_bandas.py',         'recortar la pasada ancha a las bandas de los márgenes'),
]

BLOQUE_ENTRADA = '''
# ''' + MARCA + ''': la entrada de la consola. En UWP la aplicación no arranca por
# main(): hace falta el arranque WinRT de SDL compilado con /ZW, más el main(Platform::Array<String^>^)
# que exige vccorlib. Con el generador de Visual Studio lo pone el proyecto; con Ninja hay que ponerlo a
# mano, porque VS_WINRT_APPLICATION y VS_DEPLOYMENT_CONTENT son propiedades de ese generador.
if(CMAKE_SYSTEM_NAME STREQUAL "WindowsStore")
    target_sources(psx-runtime PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/UWP/SDL_winrt_main_NonXAML.cpp")
    set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/UWP/SDL_winrt_main_NonXAML.cpp"
                 PROPERTY COMPILE_OPTIONS "/ZW")
    set_target_properties(psx-runtime PROPERTIES OUTPUT_NAME "Street_Fighter_EX2_Plus" WIN32_EXECUTABLE TRUE)
endif()
'''


def main():
    if '--list' in sys.argv[1:]:
        print('El perfil UWP, en orden:\n')
        print('  %-32s %s' % ('(entrada WinRT)', 'src/SDL_winrt_main_NonXAML.cpp -> <árbol>/UWP/ y al CMakeLists'))
        for n, (script, que) in enumerate(PASOS, 1):
            print('  %2d. %-28s %s' % (n, script, que))
        return 0

    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    if len(args) != 1:
        sys.exit('uso: %s <ruta de la raiz del proyecto del juego>   (--list para ver los pasos)'
                 % os.path.basename(sys.argv[0]))
    raiz = os.path.abspath(args[0])
    for exigido in ('CMakeLists.txt', 'game.toml'):
        if not os.path.isfile(os.path.join(raiz, exigido)):
            sys.exit('no es la raíz de un proyecto del juego (falta %s): %s' % (exigido, raiz))
    if not os.path.isfile(ENTRADA):
        sys.exit('falta en el repositorio: %s' % ENTRADA)

    hechos = []

    # 1. La entrada WinRT: el archivo y su registro en el CMakeLists del juego.
    destino = os.path.join(raiz, 'UWP', 'SDL_winrt_main_NonXAML.cpp')
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    with open(ENTRADA, 'rb') as f:
        fuente = f.read()
    if not os.path.isfile(destino) or open(destino, 'rb').read() != fuente:
        with open(destino, 'wb') as f:
            f.write(fuente)
        hechos.append('UWP/SDL_winrt_main_NonXAML.cpp')

    cmake = os.path.join(raiz, 'CMakeLists.txt')
    with open(cmake, 'rb') as f:
        crudo = f.read().decode('utf-8')
    eol = '\r\n' if '\r\n' in crudo else '\n'
    texto = crudo.replace('\r\n', '\n')
    if 'SDL_winrt_main_NonXAML.cpp' not in texto:
        # Al final del archivo: no hace falta ancla, y así no se copia nada del CMakeLists del proyecto.
        texto = texto.rstrip('\n') + '\n' + BLOQUE_ENTRADA
        tmp = cmake + '.tmp'
        with open(tmp, 'w', encoding='utf-8', newline='') as f:
            f.write(texto.replace('\n', eol))
        os.replace(tmp, cmake)
        hechos.append('CMakeLists.txt: la entrada WinRT registrada')

    # 2. Los parches, en orden.
    for script, que in PASOS:
        ruta = os.path.join(HERR, script)
        if not os.path.isfile(ruta):
            sys.exit('falta en el repositorio: tools/%s' % script)
        print('-- %-30s %s' % (script, que))
        r = subprocess.run([sys.executable, ruta, raiz], capture_output=True, text=True,
                           encoding='utf-8', errors='replace')
        salida = (r.stdout or '').strip()
        if salida:
            print('\n'.join('   ' + l for l in salida.split('\n')))
        if r.returncode != 0:
            print((r.stderr or '').strip())
            sys.exit('\nse detuvo en %s (nada más se aplicó). El árbol no es el que este paso espera: '
                     'comprueba que es %s sin modificar y que los pasos anteriores están puestos.'
                     % (script, 'strider973/Street-Fighter-EX2-Plus-Recompiled'))
        hechos.append(script)

    print('\nListo: %d pasos aplicados.' % len(hechos))
    print('Ahora: tools/configurar-uwp.ps1 para configurar y compilar (docs/INSTALL.es.md §4).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
