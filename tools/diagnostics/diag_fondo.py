# -*- coding: utf-8 -*-
# Diagnóstico del fondo que se corta a media altura: dónde se parte la cadena y si el plugin llega a repararla.
#
# El usuario lo tuvo en pantalla el 2026-10-06 y la captura lo mostró claro: el escenario se dibuja hasta media
# altura y debajo queda el relleno (negro), con los personajes bien. Eso es la cadena de 207 piezas del fondo
# ensanchado cortada por algún sitio. Lo que no se sabe es **por dónde** ni **cuándo**, y adivinarlo ya salió mal una
# vez (comprobar la cadena entera dejó el juego sin personajes: un terminador en medio es normal cuando el juego usa
# menos piezas).
#
# Esto anota en el registro, una vez por segundo como mucho y solo cuando cambia, el primer enlace que no apunta a
# donde debería, por búfer:
#     sfex2p: [fondo] buf 0 corte en la pieza 153 de 207 (tag=0x00FFFFFF) reparado=1
# Con eso se sabe si el corte está en la pieza que el juego enlaza (153), en otra, y si la reparación del VBlank
# llega a tiempo o el juego la vuelve a romper en cada cuadro.
# Se quita con --quitar.
#
# Uso: diag_fondo.py <raíz del proyecto del juego>
import os
import sys

args = [a for a in sys.argv[1:] if not a.startswith('--')]
QUITAR = '--quitar' in sys.argv
if not args:
    sys.exit('uso: %s <ruta de la raiz del proyecto del juego>' % os.path.basename(sys.argv[0]))
RAIZ = args[0]
MARCA = 'Recompilaciones: diagnostico de la cadena del fondo'

VIEJO = '''    for (uint32_t b = 0; b < 2u; b++) {
        const uint32_t buf = s_bg_base + b * BG_STRIDE;
        const uint32_t medio = buf + (BG_PRIMS_GAME - 1u) * BG_PRIM_BYTES;   /* last packet the game links */'''

NUEVO = '''    /* ''' + MARCA + ''' */
    {
        static uint32_t ultimo[2] = { 0xFFFFFFFFu, 0xFFFFFFFFu };
        for (uint32_t b = 0; b < 2u; b++) {
            const uint32_t buf = s_bg_base + b * BG_STRIDE;
            uint32_t corte = 0xFFFFFFFFu, tag = 0u;
            for (uint32_t k = 0; k + 1u < BG_PRIMS; k++) {
                const uint32_t p = buf + k * BG_PRIM_BYTES;
                const uint32_t w = psx_mod_read_word(p);
                if ((w & 0x00FFFFFFu) != ((p + BG_PRIM_BYTES) & 0x00FFFFFFu)) {
                    corte = k; tag = w; break;
                }
            }
            if (corte != ultimo[b]) {
                ultimo[b] = corte;
                if (corte == 0xFFFFFFFFu)
                    fprintf(stdout, "sfex2p: [fondo] buf %u entero\n", b);
                else
                    fprintf(stdout, "sfex2p: [fondo] buf %u corte en la pieza %u de %u (tag=0x%08X)\n",
                                b, corte + 1u, (unsigned)BG_PRIMS, tag);
            }
        }
    }
    for (uint32_t b = 0; b < 2u; b++) {
        const uint32_t buf = s_bg_base + b * BG_STRIDE;
        const uint32_t medio = buf + (BG_PRIMS_GAME - 1u) * BG_PRIM_BYTES;   /* last packet the game links */'''


def main():
    ruta = os.path.join(RAIZ, 'sfex2p_widescreen.c')
    with open(ruta, 'rb') as f:
        crudo = f.read().decode('utf-8')
    eol = '\r\n' if '\r\n' in crudo else '\n'
    t = crudo.replace('\r\n', '\n')
    if QUITAR:
        if MARCA not in t:
            print('el diagnóstico no estaba')
            return
        t = t.replace(NUEVO, VIEJO)
        mensaje = 'diagnóstico del fondo quitado'
    else:
        if MARCA in t:
            print('el diagnóstico ya estaba')
            return
        if t.count(VIEJO) != 1:
            raise SystemExit('sfex2p_widescreen.c: %d apariciones del ancla' % t.count(VIEJO))
        t = t.replace(VIEJO, NUEVO)
        mensaje = 'diagnóstico del fondo puesto'
    with open(ruta + '.tmp', 'w', encoding='utf-8', newline='') as f:
        f.write(t.replace('\n', eol))
    os.replace(ruta + '.tmp', ruta)
    print(mensaje)


if __name__ == '__main__':
    main()
