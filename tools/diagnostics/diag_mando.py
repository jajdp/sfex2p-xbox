# -*- coding: utf-8 -*-
# Diagnóstico temporal: qué botones del mando ve SDL en la consola.
#
# R3 no encendía el contador de FPS ni por evento ni por sondeo, y el registro no mostraba la pulsación. Esto
# anota en el registro, cada vez que cambia, la máscara de botones que devuelve SDL para el mando del jugador 1,
# con lo que se puede ver qué índice llega al pulsar cada botón (y si el clic del stick llega siquiera).
# Se quita con --quitar.
# Uso: diag_mando.py <raíz del proyecto del juego>
import os
import sys

args = [a for a in sys.argv[1:] if not a.startswith('--')]
QUITAR = '--quitar' in sys.argv
if not args:
    sys.exit('uso: %s <ruta de la raiz del proyecto del juego>' % os.path.basename(sys.argv[0]))
RAIZ = args[0]
MARCA = 'Recompilaciones: diagnóstico del mando'

VIEJO = '''    if (player == 1 && p.kind == 2 && p.handle) {
        static bool r3_was_down = false;'''

NUEVO = '''    if (player == 1 && p.kind == 2 && p.handle) {
        /* ''' + MARCA + ''' */
        {
            static uint32_t botones_antes = 0xFFFFFFFFu;
            uint32_t botones = 0;
            for (int b = 0; b < SDL_CONTROLLER_BUTTON_MAX; ++b)
                if (SDL_GameControllerGetButton(p.handle, (SDL_GameControllerButton)b))
                    botones |= (1u << b);
            if (botones != botones_antes) {
                std::fprintf(stdout, "psxrecomp: [diag mando] botones=0x%08X (max=%d)\\n",
                             botones, (int)SDL_CONTROLLER_BUTTON_MAX);
                botones_antes = botones;
            }
        }
        static bool r3_was_down = false;'''


def main():
    ruta = os.path.join(RAIZ, 'psxrecomp', 'runtime', 'src', 'main.cpp')
    with open(ruta, 'rb') as f:
        crudo = f.read().decode('utf-8')
    eol = '\r\n' if '\r\n' in crudo else '\n'
    t = crudo.replace('\r\n', '\n')
    puesto = MARCA in t
    if QUITAR:
        if not puesto:
            print('el diagnóstico no estaba')
            return
        if t.count(NUEVO) != 1:
            raise SystemExit('main.cpp: no encuentro el bloque del diagnóstico')
        t = t.replace(NUEVO, VIEJO)
        mensaje = 'main.cpp: diagnóstico del mando quitado'
    else:
        if puesto:
            print('el diagnóstico ya estaba')
            return
        if t.count(VIEJO) != 1:
            raise SystemExit('main.cpp: %d apariciones del ancla' % t.count(VIEJO))
        t = t.replace(VIEJO, NUEVO)
        mensaje = 'main.cpp: diagnóstico del mando puesto'
    with open(ruta + '.tmp', 'w', encoding='utf-8', newline='') as f:
        f.write(t.replace('\n', eol))
    os.replace(ruta + '.tmp', ruta)
    print(mensaje)


if __name__ == '__main__':
    main()
