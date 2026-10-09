# -*- coding: utf-8 -*-
# Perfil UWP (Xbox) para el psxrecomp de Street Fighter EX2 Plus. Este framework (00438851) no lo trae —a diferencia
# del de Street Fighter EX Plus Alpha, que es un fork con el perfil ya hecho—, así que el parche lo añade al
# runtime.cmake:
#   - PSX_UWP se enciende solo cuando CMAKE_SYSTEM_NAME es «WindowsStore»;
#   - sin servidor de depuración, sin lanzador y sin Vulkan, que no caben en la consola;
#   - SDL2 por paquete de CMake (el framework pide SDL3 por defecto, y SDL3 no tiene WinRT: hay que configurar con
#     -DPSX_SDL_BACKEND=SDL2 y el SDL2 2.30.2 compilado para WindowsStore);
#   - PSX_UWP=1 en el compilador, para las guardas del código.
# Idempotente y todo o nada; escritura atómica. Uso: parche_uwp.py <raíz del proyecto del juego>
import os
import sys

if len(sys.argv) < 2:
    sys.exit('uso: %s <ruta de la raiz del proyecto del juego>' % os.path.basename(sys.argv[0]))
RAIZ = sys.argv[1]
MARCA = 'Recompilaciones (2026-10-04): perfil UWP/Xbox'

CAMBIOS = [
    # 1. la variable, al principio
    ('''include("${PSXRECOMP_ROOT}/cmake/psx_dependency_archive.cmake")''',
     '''# ''' + MARCA + '''. El perfil se enciende solo al compilar para la consola.
set(PSX_UWP OFF)
if(CMAKE_SYSTEM_NAME STREQUAL "WindowsStore")
    set(PSX_UWP ON)
    message(STATUS "psxrecomp: perfil UWP/Xbox")
endif()

include("${PSXRECOMP_ROOT}/cmake/psx_dependency_archive.cmake")'''),

    # 2. sin servidor de depuración
    ('''# PSX_STATIC_RUNTIME: produce a 100% self-contained MinGW exe.''',
     '''if(PSX_UWP)
    # ''' + MARCA + ''': la consola no admite el servidor TCP de depuración.
    set(PSX_DEBUG_TOOLS OFF CACHE BOOL "Sin servidor de depuración en el perfil UWP" FORCE)
endif()

# PSX_STATIC_RUNTIME: produce a 100% self-contained MinGW exe.'''),

    # 3. SDL2 como paquete de CMake en UWP
    ('''    if(NOT SDL2_INCLUDE_DIRS OR NOT SDL2_LIBRARIES)
        if(MSVC)''',
     '''    if(PSX_UWP)
        # ''' + MARCA + ''': el SDL2 compilado para WindowsStore trae su paquete de CMake.
        find_package(SDL2 CONFIG REQUIRED)
        if(TARGET SDL2::SDL2-static)
            set(SDL2_LIBRARIES SDL2::SDL2-static)
        elseif(TARGET SDL2::SDL2)
            set(SDL2_LIBRARIES SDL2::SDL2)
        else()
            message(FATAL_ERROR "el paquete SDL2 de UWP no exporta SDL2::SDL2-static ni SDL2::SDL2")
        endif()
    endif()
    if(NOT PSX_UWP AND (NOT SDL2_INCLUDE_DIRS OR NOT SDL2_LIBRARIES))
        if(MSVC)'''),

    # 4. la definición para el código
    ('''        $<$<CXX_COMPILER_ID:MSVC>:SDL_MAIN_HANDLED>
    )''',
     '''        # en UWP NO se define: así SDL renombra main() a SDL_main(), que es a quien llama la entrada WinRT
        $<$<AND:$<CXX_COMPILER_ID:MSVC>,$<NOT:$<BOOL:${PSX_UWP}>>>:SDL_MAIN_HANDLED>
        $<$<BOOL:${PSX_UWP}>:PSX_UWP=1>
        $<$<BOOL:${PSX_UWP}>:_CRT_SECURE_NO_WARNINGS>
        # en UWP el PLATFORM_ID es WindowsStore, no Windows: sin esto, las macros min/max de windows.h
        # rompen mod_runtime.cpp («illegal token on right side of ::»)
        $<$<BOOL:${PSX_UWP}>:NOMINMAX>
        # con Ninja hay que declarar la familia de API a mano: es lo que hace que SDL2 se vea como WinRT
        # (__WINRT__) y exporte SDL_WinRTRunApp, la entrada de la consola
        $<$<BOOL:${PSX_UWP}>:WINAPI_FAMILY=WINAPI_FAMILY_APP>
    )
    if(PSX_UWP)
        # la consola solo activa aplicaciones marcadas como App Container; sin esto el paquete instala
        # pero no arranca («Failed to launch the application»)
        target_link_options(${target} PRIVATE /APPCONTAINER)
    endif()'''),
]


def main():
    ruta = os.path.join(RAIZ, 'psxrecomp', 'runtime', 'runtime.cmake')
    with open(ruta, 'rb') as f:
        crudo = f.read().decode('utf-8-sig')
    eol = '\r\n' if '\r\n' in crudo else '\n'
    t = crudo.replace('\r\n', '\n')
    if MARCA in t:
        print('el perfil UWP ya estaba')
        return
    for viejo, nuevo in CAMBIOS:
        if t.count(viejo) != 1:
            raise SystemExit('runtime.cmake: %d apariciones de %r' % (t.count(viejo), viejo[:60]))
        t = t.replace(viejo, nuevo)
    with open(ruta + '.tmp', 'w', encoding='utf-8-sig', newline='') as f:
        f.write(t.replace('\n', eol))
    os.replace(ruta + '.tmp', ruta)
    print('runtime.cmake: perfil UWP/Xbox añadido (%d cambios)' % len(CAMBIOS))


if __name__ == '__main__':
    main()
