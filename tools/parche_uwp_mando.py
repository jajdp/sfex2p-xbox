# -*- coding: utf-8 -*-
# El mando, en la consola.
#
# El runtime asigna el dispositivo de cada jugador por la clave `[controller] device` de los ajustes, y cuando no
# hay ajustes el reparto de fábrica es **teclado** para el jugador 1 (en una compilación de producto; la de
# depuración ya usa «auto»). La razón es que en el PC lo normal es que el lanzador escriba el dispositivo elegido
# antes de arrancar el juego. En la consola no hay teclado ni lanzador, así que el jugador 1 se quedaba sin nada:
# el juego llegaba al título y el mando no hacía nada, sin un solo aviso en el registro (el mensaje «opened
# controller for slot» solo sale cuando el jugador es de tipo mando).
#
# El parche deja «auto» —el primer mando conectado— para los dos jugadores cuando se compila para la consola. Si el
# segundo mando no está, el runtime no abre nada y ese puerto se comporta como un mando que nunca se pulsa.
#
# Idempotente y todo o nada; escritura atómica.
# Uso: parche_uwp_mando.py <raíz del proyecto del juego>
import os
import sys

if len(sys.argv) < 2:
    sys.exit('uso: %s <ruta de la raiz del proyecto del juego>' % os.path.basename(sys.argv[0]))
RAIZ = sys.argv[1]
MARCA = 'Recompilaciones (2026-10-05): UWP — pad defaults'

VIEJO = '''#if defined(PSX_DEBUG_TOOLS)
        player_device[i] = (i == 0) ? "auto" : "none";
#else
        player_device[i] = (i == 0) ? "keyboard" : "none";
#endif'''

NUEVO = '''#if defined(PSX_DEBUG_TOOLS)
        player_device[i] = (i == 0) ? "auto" : "none";
#elif defined(PSX_UWP)
        /* ''' + MARCA + '''. The console has no keyboard and no launcher to
         * assign a device, so every slot defaults to the first free game controller. A slot whose pad is
         * absent simply opens nothing (open_player bails) and reads as a pad that is never pressed. */
        player_device[i] = "auto";
#else
        player_device[i] = (i == 0) ? "keyboard" : "none";
#endif'''


def main():
    ruta = os.path.join(RAIZ, 'psxrecomp', 'runtime', 'src', 'main.cpp')
    with open(ruta, 'rb') as f:
        crudo = f.read().decode('utf-8')
    eol = '\r\n' if '\r\n' in crudo else '\n'
    t = crudo.replace('\r\n', '\n')
    if MARCA in t:
        print('el parche ya estaba')
        return
    if t.count(VIEJO) != 1:
        raise SystemExit('main.cpp: %d apariciones del ancla' % t.count(VIEJO))
    t = t.replace(VIEJO, NUEVO)
    with open(ruta + '.tmp', 'w', encoding='utf-8', newline='') as f:
        f.write(t.replace('\n', eol))
    os.replace(ruta + '.tmp', ruta)
    print('main.cpp: en la consola, los dos jugadores usan el primer mando libre')


if __name__ == '__main__':
    main()
