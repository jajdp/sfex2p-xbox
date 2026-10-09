# -*- coding: utf-8 -*-
# R3 enciende y apaga el contador de FPS, como en Street Fighter EX Plus Alpha y en Castlevania Chronicles.
#
# El contador ya lo trae el framework: `fps_telemetry_toggle()` publica «Game 60 FPS 1.00x» en el rótulo de la
# ventana y en el aviso de pantalla (host_osd), que el renderizador por software de la consola sí dibuja. Lo que
# no hay en la consola es cómo encenderlo: el atajo del framework es una TECLA, y allí no hay teclado.
#
# Se ata al botón **R3** (pulsar el stick derecho): el mando va en modo digital, donde los clics de los sticks del
# DualShock no existen, así que el juego nunca ve ese botón, y es el mismo de los otros dos ports de la casa.
#
# ⚠ DÓNDE VA LA COMPROBACIÓN — la misma trampa que en Street Fighter EX Plus Alpha, y aquí se repitió dos veces:
#   1. En el bucle de eventos de SDL: NO funciona. Ese bucle es el bombeo que evita que la ventana se congele y el
#      evento del botón no llega ahí.
#   2. Dentro de `pad_buttons_for()`, preguntando a SDL por el botón: TAMPOCO. Esa función no se recorre siempre
#      para el jugador 1 (depende de la política del mando y de si hay dispositivo asignado).
#   3. Lo que SÍ funciona, y es lo que ya se había aprendido en el otro juego: sobre la **palabra de botones ya
#      combinada** del jugador 1 (ranura 0), justo antes de entregarla al SIO — `apply_pad_slot_to_sio`. En esa
#      palabra, al estilo del mando de PlayStation, **0 = pulsado**, y R3 es el bit 2.
# El botón no se consume: la palabra se entrega igual.
#
# Idempotente y todo o nada; escritura atómica.
# Uso: parche_uwp_fps_r3.py <raíz del proyecto del juego>
import os
import sys

if len(sys.argv) < 2:
    sys.exit('uso: %s <ruta de la raiz del proyecto del juego>' % os.path.basename(sys.argv[0]))
RAIZ = sys.argv[1]
MARCA = 'Recompilaciones (2026-10-05): UWP — R3 toggles the FPS readout'

# --- lo que hay que retirar de los dos intentos fallidos -------------------------------------------
EVENTO_PUESTO = '''#if defined(PSX_UWP)
            /* ''' + MARCA + '''. The framework's own shortcut is a
             * keyboard key and the console has no keyboard; R3 is free here (this game never reads L3/R3)
             * and matches the other two console ports. */
#if defined(PSX_SDL3)
            if (ev.type == SDL_EVENT_GAMEPAD_BUTTON_DOWN &&
                ev.gbutton.button == SDL_GAMEPAD_BUTTON_RIGHT_STICK) {
#else
            if (ev.type == SDL_CONTROLLERBUTTONDOWN &&
                ev.cbutton.button == SDL_CONTROLLER_BUTTON_RIGHTSTICK) {
#endif
                fps_telemetry_toggle();
                continue;
            }
#endif
'''

SONDEO_PUESTO = '''#if defined(PSX_UWP)
    /* ''' + MARCA + '''. The framework's own shortcut is a keyboard
     * key and the console has no keyboard, so player 1's R3 (right stick click) does it instead: free in
     * this game, and the same button as in the other two console ports. Polled here — where the runtime
     * already asks the pad for its state every frame — because the SDL event never reaches the pump loop.
     * The button is not consumed: the game still sees it. */
    if (player == 1 && p.kind == 2 && p.handle) {
        static bool r3_was_down = false;
        const bool r3_down =
            SDL_GameControllerGetButton(p.handle, SDL_CONTROLLER_BUTTON_RIGHTSTICK) != 0;
        if (r3_down && !r3_was_down) fps_telemetry_toggle();
        r3_was_down = r3_down;
    }
#endif
'''

# --- lo bueno: sobre la palabra del pad, antes del SIO ----------------------------------------------
SIO_VIEJO = '''static void apply_pad_slot_to_sio(int s, const PsxNetPad& pad) {
    if (sio_pad_on_multitap(s) && !sio_get_multitap_analog())
        sio_set_pad_config_capable(s, 0);
    sio_set_pad_state_slot(s, pad.buttons);'''

SIO_NUEVO = '''#if defined(PSX_UWP)
/* ''' + MARCA + '''. The framework's own shortcut is a keyboard key and
 * the console has no keyboard, so player 1's R3 does it. Edge-triggered on the COMBINED pad word just
 * before it reaches the SIO — the SDL event never reaches the pump loop and pad_buttons_for() is not
 * always walked for player 1 (same lesson as the EX Plus Alpha port). PlayStation pad word: 0 = pressed,
 * bit 2 = R3. The word is passed on untouched, so the game still sees the button. */
#define PSX_PAD_BIT_R3_FPS (1u << 2)

static void fps_toggle_from_pad(uint16_t word) {
    static bool held = false;
    const bool down = (word & PSX_PAD_BIT_R3_FPS) == 0;
    if (down && !held) fps_telemetry_toggle();
    held = down;
}
#endif

static void apply_pad_slot_to_sio(int s, const PsxNetPad& pad) {
    if (sio_pad_on_multitap(s) && !sio_get_multitap_analog())
        sio_set_pad_config_capable(s, 0);
#if defined(PSX_UWP)
    if (s == 0) fps_toggle_from_pad(pad.buttons);
#endif
    sio_set_pad_state_slot(s, pad.buttons);'''

# Y una línea en el registro cada vez que se alterna: así se puede comprobar desde el PC, por el Device Portal,
# que la pulsación llegó, aunque el aviso de pantalla no se viera.
TRAZA_VIEJO = '''    host_osd_push(enabled ? "FPS readout on" : "FPS readout off", 1500);'''
TRAZA_NUEVO = '''    host_osd_push(enabled ? "FPS readout on" : "FPS readout off", 1500);
    /* ''' + MARCA + ''': también al registro, para poder comprobarlo desde fuera. */
    std::fprintf(stdout, "psxrecomp: FPS readout %s\\n", enabled ? "on" : "off");'''


def main():
    ruta = os.path.join(RAIZ, 'psxrecomp', 'runtime', 'src', 'main.cpp')
    with open(ruta, 'rb') as f:
        crudo = f.read().decode('utf-8')
    eol = '\r\n' if '\r\n' in crudo else '\n'
    t = crudo.replace('\r\n', '\n')
    hechos = []
    for viejo, que in ((EVENTO_PUESTO, 'el intento por evento'),
                       (SONDEO_PUESTO, 'el intento por sondeo del mando')):
        if viejo in t:
            t = t.replace(viejo, '')
            hechos.append('quitado ' + que)
    if SIO_NUEVO not in t:
        if t.count(SIO_VIEJO) != 1:
            raise SystemExit('main.cpp: %d apariciones del ancla del SIO' % t.count(SIO_VIEJO))
        t = t.replace(SIO_VIEJO, SIO_NUEVO)
        hechos.append('R3 sobre la palabra del pad, antes del SIO')
    if TRAZA_NUEVO not in t:
        if t.count(TRAZA_VIEJO) != 1:
            raise SystemExit('main.cpp: %d apariciones del ancla de la traza' % t.count(TRAZA_VIEJO))
        t = t.replace(TRAZA_VIEJO, TRAZA_NUEVO)
        hechos.append('traza del contador en el registro')
    if not hechos:
        print('el parche ya estaba')
        return
    with open(ruta + '.tmp', 'w', encoding='utf-8', newline='') as f:
        f.write(t.replace('\n', eol))
    os.replace(ruta + '.tmp', ruta)
    print('main.cpp: ' + '; '.join(hechos))


if __name__ == '__main__':
    main()
