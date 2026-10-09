# -*- coding: utf-8 -*-
# Los dos cambios de código que pide el perfil UWP de Street Fighter EX2 Plus, los que impiden enlazar:
#   1. `MessageBoxA` no existe en UWP (main.cpp lo usa para avisar al jugador): los dos avisos quedan solo en el
#      registro cuando se compila para la consola.
#   2. El SDL2 que se reutiliza del port de Street Fighter EX Plus Alpha lleva el parche de la reanudación, que anota
#      en `g_psx_prev_exec_state` cómo se activó la aplicación (3 = la consola la terminó). Esa variable la define el
#      runtime, así que aquí también hay que definirla; de paso deja medio camino hecho para «volver donde lo dejaste»
#      (Fase 11 del PLAN).
# Idempotente y todo o nada; escritura atómica.
# Uso: parche_uwp_codigo.py <raíz del proyecto del juego>
import os
import sys

if len(sys.argv) < 2:
    sys.exit('uso: %s <ruta de la raiz del proyecto del juego>' % os.path.basename(sys.argv[0]))
RAIZ = sys.argv[1]
MARCA = 'Recompilaciones (2026-10-04): UWP'

CAMBIOS = [
    # 1. los dos avisos con MessageBoxA (cada línea es única por su icono)
    ('''    if (!g_headless) MessageBoxA(NULL, msg.c_str(), title, MB_OK | MB_ICONWARNING);''',
     '''#if !defined(PSX_UWP)   /* ''' + MARCA + ''': sin cuadros de diálogo en la consola */
    if (!g_headless) MessageBoxA(NULL, msg.c_str(), title, MB_OK | MB_ICONWARNING);
#endif'''),

    ('''    if (!g_headless) MessageBoxA(NULL, msg.c_str(), title, MB_OK | MB_ICONINFORMATION);''',
     '''#if !defined(PSX_UWP)   /* ''' + MARCA + ''': sin cuadros de diálogo en la consola */
    if (!g_headless) MessageBoxA(NULL, msg.c_str(), title, MB_OK | MB_ICONINFORMATION);
#endif'''),

    # 2. la variable que usa el SDL2 parcheado del otro port
    ('''static std::string s_picker_game_name = "PSXRecomp";''',
     '''/* ''' + MARCA + ''': el SDL2 de WindowsStore que se reutiliza (el del port de SF EX Plus Alpha) anota aquí
 * cómo se activó la aplicación: 0 = arranque normal, 3 = la consola la había terminado, 4 = la cerró el usuario.
 * Hay que definirla aunque todavía no se use: sin ella, SDL no enlaza. */
#if defined(PSX_UWP)
extern "C" int g_psx_prev_exec_state = -1;
#endif

static std::string s_picker_game_name = "PSXRecomp";'''),

    # 3. el diálogo de archivos: en la consola no hay dónde abrirlo, y el App Container no tiene
    #    OPENFILENAMEA. Este cambio se hizo a mano el 2026-10-04 sobre el árbol y no estaba recogido
    #    aquí; sin él, el perfil no reproduce el ejecutable que corre en la consola.
    ('''#ifdef _WIN32
    char path_buf[4096];''',
     '''#if defined(_WIN32) && !defined(PSX_UWP)   /* ''' + MARCA + ''' no tiene el diálogo de archivos */
    char path_buf[4096];'''),
]


def main():
    ruta = os.path.join(RAIZ, 'psxrecomp', 'runtime', 'src', 'main.cpp')
    with open(ruta, 'rb') as f:
        crudo = f.read().decode('utf-8')
    eol = '\r\n' if '\r\n' in crudo else '\n'
    t = crudo.replace('\r\n', '\n')
    if MARCA in t:
        print('el parche ya estaba')
        return
    for viejo, nuevo in CAMBIOS:
        if t.count(viejo) != 1:
            raise SystemExit('main.cpp: %d apariciones de %r' % (t.count(viejo), viejo[:60]))
        t = t.replace(viejo, nuevo)
    with open(ruta + '.tmp', 'w', encoding='utf-8', newline='') as f:
        f.write(t.replace('\n', eol))
    os.replace(ruta + '.tmp', ruta)
    print('main.cpp: %d cambios para UWP (diálogos y g_psx_prev_exec_state)' % len(CAMBIOS))


if __name__ == '__main__':
    main()
