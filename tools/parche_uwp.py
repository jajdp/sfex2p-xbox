# Perfil UWP (Xbox) para el psxrecomp de Street Fighter EX2 Plus. El framework no trae ningún perfil para la
# consola, así que el parche lo añade al runtime.cmake (la versión con la que se trabajó está en el CHANGELOG):
#   - PSX_UWP se enciende solo cuando CMAKE_SYSTEM_NAME es «WindowsStore»;
#   - sin servidor de depuración, sin lanzador y sin Vulkan, que no caben en la consola;
#   - SDL2 por paquete de CMake (el framework pide SDL3 por defecto, y SDL3 no tiene WinRT: hay que configurar con
#     -DPSX_SDL_BACKEND=SDL2 y el SDL2 2.30.2 compilado para WindowsStore);
#   - PSX_UWP=1 en el compilador, para las guardas del código.
# Idempotente y todo o nada; escritura atómica. Uso: parche_uwp.py <raíz del proyecto del juego>
import parchear

MARCA = 'Recompilaciones (2026-10-04): UWP/Xbox profile'

CAMBIOS = [
    # 1. la variable, al principio
    ('''include("${PSXRECOMP_ROOT}/cmake/psx_dependency_archive.cmake")''',
     '''# ''' + MARCA + '''. The profile only turns itself on when building for the console.
set(PSX_UWP OFF)
if(CMAKE_SYSTEM_NAME STREQUAL "WindowsStore")
    set(PSX_UWP ON)
    message(STATUS "psxrecomp: UWP/Xbox profile")
endif()

include("${PSXRECOMP_ROOT}/cmake/psx_dependency_archive.cmake")'''),

    # 2. sin servidor de depuración
    ('''# PSX_STATIC_RUNTIME: produce a 100% self-contained MinGW exe.''',
     '''if(PSX_UWP)
    # ''' + MARCA + ''': the console does not allow the debug server's TCP socket.
    set(PSX_DEBUG_TOOLS OFF CACHE BOOL "No debug server in the UWP profile" FORCE)
endif()

# PSX_STATIC_RUNTIME: produce a 100% self-contained MinGW exe.'''),

    # 3. SDL2 como paquete de CMake en UWP
    ('''    if(NOT SDL2_INCLUDE_DIRS OR NOT SDL2_LIBRARIES)
        if(MSVC)''',
     '''    if(PSX_UWP)
        # ''' + MARCA + ''': an SDL2 built for WindowsStore ships its own CMake package.
        find_package(SDL2 CONFIG REQUIRED)
        if(TARGET SDL2::SDL2-static)
            set(SDL2_LIBRARIES SDL2::SDL2-static)
        elseif(TARGET SDL2::SDL2)
            set(SDL2_LIBRARIES SDL2::SDL2)
        else()
            message(FATAL_ERROR "the UWP SDL2 package exports neither SDL2::SDL2-static nor SDL2::SDL2")
        endif()
    endif()
    if(NOT PSX_UWP AND (NOT SDL2_INCLUDE_DIRS OR NOT SDL2_LIBRARIES))
        if(MSVC)'''),

    # 4. la definición para el código
    ('''        $<$<CXX_COMPILER_ID:MSVC>:SDL_MAIN_HANDLED>
    )''',
     '''        # NOT defined on UWP: that is what makes SDL rename main() to SDL_main(), which the WinRT entry calls
        $<$<AND:$<CXX_COMPILER_ID:MSVC>,$<NOT:$<BOOL:${PSX_UWP}>>>:SDL_MAIN_HANDLED>
        $<$<BOOL:${PSX_UWP}>:PSX_UWP=1>
        $<$<BOOL:${PSX_UWP}>:_CRT_SECURE_NO_WARNINGS>
        # on UWP the PLATFORM_ID is WindowsStore, not Windows: without this, the min/max macros of
        # windows.h break mod_runtime.cpp ("illegal token on right side of ::")
        $<$<BOOL:${PSX_UWP}>:NOMINMAX>
        # with Ninja the API family has to be declared by hand: it is what makes SDL2 see itself as
        # WinRT (__WINRT__) and export SDL_WinRTRunApp, the console's entry point
        $<$<BOOL:${PSX_UWP}>:WINAPI_FAMILY=WINAPI_FAMILY_APP>
    )
    if(PSX_UWP)
        # the console only activates apps marked as App Container; without this the package installs
        # but will not start ("Failed to launch the application")
        target_link_options(${target} PRIVATE /APPCONTAINER)
    endif()'''),
]


def main():
    # runtime.cmake se lee y se escribe con 'utf-8-sig' para conservar su BOM.
    parchear.informe(
        parchear.aplicar(parchear.runtime(parchear.raiz(), 'runtime.cmake'), CAMBIOS, MARCA,
                         'runtime.cmake: perfil UWP/Xbox añadido (%d cambios)' % len(CAMBIOS),
                         'utf-8-sig'),
        nada='el perfil UWP ya estaba')


if __name__ == '__main__':
    main()
