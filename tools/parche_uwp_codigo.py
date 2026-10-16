# Los tres cambios de código que pide el perfil UWP, los que impiden enlazar contra el App Container:
#   1. `MessageBoxA` no existe en UWP (main.cpp lo usa para avisar al jugador): los dos avisos quedan solo en el
#      registro cuando se compila para la consola.
#   2. El SDL2 compilado para WindowsStore que usa este port anota en `g_psx_prev_exec_state` cómo se activó la
#      aplicación (3 = la consola la había terminado). Esa variable la define el runtime, así que aquí también hay
#      que definirla, aunque todavía no se lea: sin ella, SDL no enlaza. Quien la usa es `parche_uwp_reanudar.py`.
#   3. El diálogo de archivos de Windows (`OPENFILENAMEA`), que el App Container no tiene y en la consola no
#      tendría dónde abrirse.
# Idempotente y todo o nada; escritura atómica.
# Uso: parche_uwp_codigo.py <raíz del proyecto del juego>
import parchear

MARCA = 'Recompilaciones (2026-10-04): UWP'

CAMBIOS = [
    # 1. los dos avisos con MessageBoxA (cada línea es única por su icono)
    ('''    if (!g_headless) MessageBoxA(NULL, msg.c_str(), title, MB_OK | MB_ICONWARNING);''',
     '''#if !defined(PSX_UWP)   /* ''' + MARCA + ''': no message boxes on the console */
    if (!g_headless) MessageBoxA(NULL, msg.c_str(), title, MB_OK | MB_ICONWARNING);
#endif'''),

    ('''    if (!g_headless) MessageBoxA(NULL, msg.c_str(), title, MB_OK | MB_ICONINFORMATION);''',
     '''#if !defined(PSX_UWP)   /* ''' + MARCA + ''': no message boxes on the console */
    if (!g_headless) MessageBoxA(NULL, msg.c_str(), title, MB_OK | MB_ICONINFORMATION);
#endif'''),

    # 2. la variable que usa el SDL2 parcheado del otro port
    ('''static std::string s_picker_game_name = "PSXRecomp";''',
     '''/* ''' + MARCA + ''': the SDL2 built for WindowsStore records here how the app was
 * activated: 0 = normal start, 3 = the console had terminated it, 4 = the user closed it. It has to be
 * defined even before anything reads it: without it, SDL does not link. */
#if defined(PSX_UWP)
extern "C" int g_psx_prev_exec_state = -1;
#endif

static std::string s_picker_game_name = "PSXRecomp";'''),

    # 3. el diálogo de archivos: en la consola no hay dónde abrirlo, y el App Container no tiene
    #    OPENFILENAMEA.
    ('''#ifdef _WIN32
    char path_buf[4096];''',
     '''#if defined(_WIN32) && !defined(PSX_UWP)   /* ''' + MARCA + ''': no file dialog on the console */
    char path_buf[4096];'''),
]


def main():
    parchear.informe(parchear.aplicar(
        parchear.runtime(parchear.raiz(), 'src', 'main.cpp'), CAMBIOS, MARCA,
        'main.cpp: %d cambios para UWP (diálogos y g_psx_prev_exec_state)' % len(CAMBIOS)))


if __name__ == '__main__':
    main()
