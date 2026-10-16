# En la consola, el contador de FPS viene ENCENDIDO de fábrica.
#
# El framework lo enciende por la variable de entorno PSX_FPS_TELEMETRY, que en la Xbox no hay cómo poner, o por
# un atajo de teclado, que tampoco existe allí. Como el contador es justamente lo que hace falta para comprobar si
# un escenario baja de 60, en el perfil UWP se enciende por defecto; R3 lo apaga y lo vuelve a encender
# (`parche_uwp_fps_r3.py`), y quien no lo quiera puede dejar PSX_FPS_TELEMETRY=0 si algún día hay cómo.
#
# Idempotente y todo o nada; escritura atómica.
# Uso: parche_uwp_fps_encendido.py <raíz del proyecto del juego>
import parchear

MARCA = 'Recompilaciones (2026-10-05): UWP — FPS readout on by default'

VIEJO = '''static int fps_telemetry_enabled(void) {
    if (s_fps_telemetry_enabled < 0) {
        const char *e = std::getenv("PSX_FPS_TELEMETRY");
        s_fps_telemetry_enabled = (e && e[0] && e[0] != '0') ? 1 : 0;
    }
    return s_fps_telemetry_enabled;
}'''

NUEVO = '''static int fps_telemetry_enabled(void) {
    if (s_fps_telemetry_enabled < 0) {
        const char *e = std::getenv("PSX_FPS_TELEMETRY");
#if defined(PSX_UWP)
        /* ''' + MARCA + '''. The console has neither an environment
         * to set the variable in nor a keyboard for the shortcut, and the readout is exactly what tells
         * whether a stage drops below 60. R3 turns it off and on again. */
        s_fps_telemetry_enabled = (e && e[0]) ? (e[0] != '0') : 1;
#else
        s_fps_telemetry_enabled = (e && e[0] && e[0] != '0') ? 1 : 0;
#endif
    }
    return s_fps_telemetry_enabled;
}'''


def main():
    parchear.informe(parchear.aplicar(
        parchear.runtime(parchear.raiz(), 'src', 'main.cpp'),
        [(VIEJO, NUEVO)], MARCA, 'main.cpp: en la consola, el contador de FPS arranca encendido'))


if __name__ == '__main__':
    main()
