# -*- coding: utf-8 -*-
# Diagnóstico del fondo incompleto: vuelca el MAPA de celdas del escenario, que es quien decide qué se dibuja.
#
# El desensamblado de func_80137AD0 (2026-10-06) dejó el mecanismo a la vista:
#
#   s1 = 0x801E7F00        mapa = [s1+4]   scrollX = (s16)[s1+18]   scrollY = (s16)[s1+22]
#   filas  = 6 - (scrollY >> 5), descartando <= 0 y con tope 9
#   fila0  = clamp((scrollY >> 5) + 8, 0, 13)        <- el juego CLAMPA la fila: repite la de arriba y la de abajo
#   columna del mapa = (scrollX >> 5 - 3 + c) & 63   <- pero la columna ENVUELVE en 64
#   celda  = (s16)[mapa + (fila + columna * 14) * 8]
#   si la celda es 0 -> NO se dibuja esa pieza (y no consume pieza de la cadena: 0x80137E74 va antes
#   del destino del salto en 0x80137E7C)
#
# De ahí la sospecha: los huecos que el usuario ve abajo en los costados son celdas a 0 del mapa, no una
# cadena rota. En 4:3 el juego solo mira 17 columnas y el escenario únicamente trae datos donde se veía.
# Esto lo comprueba: una vez por segundo escribe la rejilla de las filas y columnas que el juego recorre,
# con '.' = celda con contenido y 'X' = celda vacía, más el scroll y los índices. Se quita con --quitar.
#
# Uso: diag_mapa_fondo.py [<ruta del .c>] [--quitar]
import os
import sys

args = [a for a in sys.argv[1:] if not a.startswith('--')]
QUITAR = '--quitar' in sys.argv
if not args:
    sys.exit('uso: %s <ruta del archivo a inspeccionar>' % os.path.basename(sys.argv[0]))
RUTA = args[0]
MARCA = 'Recompilaciones: volcado del mapa del fondo'

ANCLA = 'static void sfex2p_widescreen_vblank(void) {\n    if (!s_bg_base) return;\n'

CODIGO = '''/* ''' + MARCA + '''. Lee la rejilla que el juego consulta en func_80137AD0 y anota, una vez por
 * segundo, qué celdas estan vacias ('X'): esas son las piezas que el juego decide NO dibujar. */
#define BG_MAP_ANCHOR 0x801E7F00u

static void bg_dump_map(void) {
    static int cuadros = 0;
    static char previo[16 * 32];
    char rejilla[16 * 32];
    char linea[160];
    uint32_t mapa, p;
    int sx, sy, fila_scroll, col_base, fila0, filas, f, c, n = 0;

    if (++cuadros < 60) return;
    cuadros = 0;

    mapa = psx_mod_read_word(BG_MAP_ANCHOR + 4u);
    if (!mapa) return;
    sx = (int)(int16_t)(uint16_t)(psx_mod_read_word(BG_MAP_ANCHOR + 16u) >> 16);
    sy = (int)(int16_t)(uint16_t)(psx_mod_read_word(BG_MAP_ANCHOR + 20u) >> 16);
    fila_scroll = sy >> 5;
    col_base = (sx >> 5) - (int)BG_EXTRA_COLS;
    fila0 = fila_scroll + 8;
    filas = 6 - fila_scroll;
    if (filas <= 0) return;
    if (filas > (int)BG_ROWS) filas = (int)BG_ROWS;

    for (f = 0; f < filas; f++) {
        int fila = fila0 + f;
        if (fila < 0) fila = 0;
        if (fila > 13) fila = 13;
        for (c = 0; c < (int)BG_COLS; c++) {
            const uint32_t col = (uint32_t)(col_base + c) & 63u;
            const uint32_t celda = (uint32_t)fila + col * 14u;
            const uint16_t v = (uint16_t)(psx_mod_read_word(mapa + celda * 8u) & 0xFFFFu);
            rejilla[n++] = v ? '.' : 'X';
        }
    }
    rejilla[n] = 0;
    if (n == (int)strlen(previo) && memcmp(rejilla, previo, (size_t)n) == 0) return;
    memcpy(previo, rejilla, (size_t)n + 1u);

    snprintf(linea, sizeof linea, "sx=%d sy=%d col_base=%d fila0=%d filas=%d", sx, sy, col_base, fila0, filas);
    bg_line(linea);
    for (f = 0; f < filas; f++) {
        snprintf(linea, sizeof linea, "  fila %2d  %.*s", fila0 + f > 13 ? 13 : (fila0 + f < 0 ? 0 : fila0 + f),
                 (int)BG_COLS, rejilla + f * (int)BG_COLS);
        bg_line(linea);
    }
}

'''

LLAMADA = ('static void sfex2p_widescreen_vblank(void) {\n'
           '    if (!s_bg_base) return;\n'
           '    bg_dump_map();   /* ' + MARCA + ' */\n')

# bg_line: en el PC basta stdout; en UWP hay que escribir al archivo que se puede leer con el juego vivo.
BG_LINE_PC = '''/* ''' + MARCA + ''' */
static void bg_line(const char *s) {
    fprintf(stdout, "sfex2p: [mapa] %s\\n", s);
    fflush(stdout);
}

'''

BG_LINE_UWP = '''/* ''' + MARCA + ''' */
static void bg_line(const char *s) {
    const char *tmp = getenv("TEMP");
    char ruta[512];
    FILE *f;
    if (!tmp) return;
    snprintf(ruta, sizeof ruta, "%s/../../LocalState/PSXRecomp/SLUS-01105/logs/fondo.txt", tmp);
    f = fopen(ruta, "a");
    if (!f) return;
    fprintf(f, "sfex2p: [mapa] %s\\n", s);
    fclose(f);
}

'''

INCLUDES = '#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n'


def main():
    with open(RUTA, 'rb') as f:
        crudo = f.read().decode('utf-8')
    eol = '\r\n' if '\r\n' in crudo else '\n'
    t = crudo.replace('\r\n', '\n')

    if QUITAR:
        if MARCA not in t:
            print('el volcado no estaba')
            return
        i = t.index('/* ' + MARCA)
        j = t.index('static void sfex2p_widescreen_vblank', i)
        t = t[:i] + t[j:]
        # puede quedar el otro bloque (bg_line o el volcado): repetir hasta limpiar
        while MARCA in t:
            i = t.index('/* ' + MARCA)
            j = t.index('\n\n', i) + 2
            t = t[:i] + t[j:]
        t = t.replace('    bg_dump_map();   /* ' + MARCA + ' */\n', '')
        mensaje = 'volcado del mapa quitado'
    else:
        if MARCA in t:
            print('el volcado ya estaba')
            return
        if ANCLA not in t:
            raise SystemExit('no encuentro el VBlank del plugin en %s' % RUTA)
        es_uwp = 'getenv("TEMP")' in t
        bloque = (BG_LINE_UWP if es_uwp else BG_LINE_PC) + CODIGO
        if '#include <stdio.h>' not in t:
            t = t.replace('#include "mod_plugins.h"\n', '#include "mod_plugins.h"\n' + INCLUDES, 1)
        elif '#include <string.h>' not in t:
            t = t.replace('#include <stdio.h>\n', '#include <stdio.h>\n#include <string.h>\n', 1)
        t = t.replace(ANCLA, bloque + LLAMADA, 1)
        mensaje = 'volcado del mapa puesto (%s)' % ('UWP' if es_uwp else 'PC')

    with open(RUTA + '.tmp', 'w', encoding='utf-8', newline='') as f:
        f.write(t.replace('\n', eol))
    os.replace(RUTA + '.tmp', RUTA)
    print(mensaje)


if __name__ == '__main__':
    main()
