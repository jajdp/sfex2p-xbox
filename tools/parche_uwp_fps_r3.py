# -*- coding: utf-8 -*-
# R3 enciende y apaga el contador de FPS.
#
# El contador ya lo trae el framework: `fps_telemetry_toggle()` publica «Game 60 FPS 1.00x» en el rótulo de la
# ventana y en el aviso de pantalla (host_osd), que el renderizador por software de la consola sí dibuja. Lo que
# no hay en la consola es cómo encenderlo: el atajo del framework es una TECLA, y allí no hay teclado.
#
# Se ata al botón **R3** (pulsar el stick derecho): el mando va en modo digital, donde los clics de los sticks del
# DualShock no existen, así que el juego nunca ve ese botón, y es el mismo de los otros dos ports de la casa.
#
# ⚠ DÓNDE VA LA COMPROBACIÓN. Ni en el bucle de eventos de SDL —que es el bombeo que evita que la ventana se
# congele, y el evento del botón no llega ahí— ni dentro de `pad_buttons_for()` preguntando a SDL, porque esa
# función no se recorre siempre para el jugador 1: depende de la política del mando y de si hay dispositivo
# asignado. Va sobre la **palabra de botones ya combinada** del jugador 1 (ranura 0), justo antes de entregarla
# al SIO, en `apply_pad_slot_to_sio`. En esa palabra, al estilo del mando de PlayStation, **0 = pulsado**, y R3
# es el bit 2. El botón no se consume: la palabra se entrega igual.
#
# Idempotente y todo o nada; escritura atómica.
# Uso: parche_uwp_fps_r3.py <raíz del proyecto del juego>
import parchear

MARCA = 'Recompilaciones (2026-10-05): UWP — R3 toggles the FPS readout'

# --- la comprobacion, sobre la palabra del pad y antes del SIO -------------------------------------
SIO_VIEJO = '''static void apply_pad_slot_to_sio(int s, const PsxNetPad& pad) {
    if (sio_pad_on_multitap(s) && !sio_get_multitap_analog())
        sio_set_pad_config_capable(s, 0);
    sio_set_pad_state_slot(s, pad.buttons);'''

SIO_NUEVO = '''#if defined(PSX_UWP)
/* ''' + MARCA + '''. The framework's own shortcut is a keyboard key and
 * the console has no keyboard, so player 1's R3 does it. Edge-triggered on the COMBINED pad word just
 * before it reaches the SIO — the SDL event never reaches the pump loop and pad_buttons_for() is not
 * always walked for player 1. PlayStation pad word: 0 = pressed,
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
    parchear.informe(parchear.aplicar(
        parchear.runtime(parchear.raiz(), 'src', 'main.cpp'),
        [(SIO_VIEJO, SIO_NUEVO), (TRAZA_VIEJO, TRAZA_NUEVO)], MARCA,
        'main.cpp: R3 sobre la palabra del pad, y la traza del contador en el registro'))

if __name__ == '__main__':
    main()
