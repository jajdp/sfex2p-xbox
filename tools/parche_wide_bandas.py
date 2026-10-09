# -*- coding: utf-8 -*-
# Segunda vuelta del empalme (`parche_wide_splice.py`, que hay que aplicar antes): la pasada ancha ya no dibuja
# la parte central de las primitivas que SÍ llegan a los márgenes.
#
# Con el empalme, las primitivas que se quedan dentro del encuadre 4:3 no se dibujan dos veces, y la pasada ancha
# bajó de 3,4-3,6 ms por cuadro a 1,0-1,4. Lo que queda es el fondo del escenario y lo que asoma por los lados: esas
# primitivas se rasterizaban ENTERAS en la superficie ancha, aunque su parte central se tapa luego con la VRAM. Aquí
# se recorta cada una a la banda que de verdad aporta: una pasada por margen, con el área de dibujo reducida a esa
# banda, y ninguna pasada por el centro.
#
# El bucle `for (int band = 0; band < 2; ++band)` sustituye a la llamada única: `wide_band()` ajusta el recorte y
# devuelve 0 cuando la primitiva no toca esa banda. Con el empalme apagado (estirado del fondo 2D o escala > 1)
# hace una sola pasada con el recorte completo, que es el camino de siempre.
#
# Idempotente y todo o nada; escritura atómica. Los comentarios del código van en inglés, como el resto del runtime.
# Uso: parche_wide_bandas.py <raíz del proyecto del juego>
import os
import re
import sys

if len(sys.argv) < 2:
    sys.exit('uso: %s <ruta de la raiz del proyecto del juego>' % os.path.basename(sys.argv[0]))
RAIZ = sys.argv[1]
MARCA = 'Recompilaciones (2026-10-06): wide pass clipped to the margins'

AYUDA_VIEJA = '''static inline int wide_min3(int a, int b, int c) {'''

AYUDA_NUEVA = '''/* ''' + MARCA + '''.
 * A primitive that reaches a margin still had its centre rasterized into the wide surface, where the
 * present then covers it with VRAM. Draw it once per margin instead, with the draw area narrowed to
 * that band: band 0 = left of the centre, band 1 = right of it. Returns 0 when the primitive does not
 * reach that band. With the splice off (backdrop stretch / scale > 1) band 0 is the whole surface and
 * band 1 is skipped, which is the original single pass. */
static inline int wide_band(RTarget *t, int s, int xa, int xb, int band) {
    if (!g_wide_splice || g_scale != 1) return band == 0;
    if (xa > xb) { int tmp = xa; xa = xb; xb = tmp; }
    const int lo = wide_centre_lo(s) + WIDE_SPLICE_GUARD;
    const int hi = wide_centre_hi(s) - WIDE_SPLICE_GUARD;
    if (band == 0) {
        if (xa >= lo) return 0;
        t->cx1 = 0;
        t->cx2 = lo - 1;
        return 1;
    }
    if (xb < hi) return 0;
    t->cx1 = hi;
    t->cx2 = g_wide_w * s - 1;
    return 1;
}

static inline int wide_min3(int a, int b, int c) {'''


def envolver(t, llamada):
    """Cambia `if (wide_needs_pass(s, A, B))\\n<llamada>(...);` por el bucle de bandas."""
    patron = re.compile(
        r'( *)if \(wide_needs_pass\(s, ([^;]+?)\)\)\n'          # la guarda
        r'( *)(' + re.escape(llamada) + r'\(&wt,.*?\);)\n',     # la llamada, hasta su punto y coma
        re.S)

    def rep(m):
        ind, args, ind2, cuerpo = m.group(1), m.group(2), m.group(3), m.group(4)
        cuerpo = cuerpo.replace('\n', '\n    ')
        return ('%sfor (int band = 0; band < 2; ++band) {\n'
                '%s    if (!wide_band(&wt, s, %s, band)) continue;\n'
                '%s    %s\n'
                '%s}\n') % (ind, ind, args, ind2, cuerpo, ind)

    return patron.subn(rep, t)


LLAMADAS = ['raster_flat_triangle', 'raster_gouraud_triangle', 'raster_textured_triangle',
            'raster_shaded_textured_triangle', 'raster_textured_rect', 'raster_textured_rect_scaled']


def main():
    ruta = os.path.join(RAIZ, 'psxrecomp', 'runtime', 'src', 'gpu_sw_renderer.c')
    with open(ruta, 'rb') as f:
        crudo = f.read().decode('utf-8')
    eol = '\r\n' if '\r\n' in crudo else '\n'
    t = crudo.replace('\r\n', '\n')
    if MARCA in t:
        print('el parche ya estaba')
        return
    if 'wide_needs_pass' not in t:
        raise SystemExit('falta parche_wide_splice.py: no encuentro wide_needs_pass')
    if t.count(AYUDA_VIEJA) != 1:
        raise SystemExit('gpu_sw_renderer.c: %d apariciones del ancla de la ayuda' % t.count(AYUDA_VIEJA))
    t = t.replace(AYUDA_VIEJA, AYUDA_NUEVA, 1)
    total = 0
    for llamada in LLAMADAS:
        t, n = envolver(t, llamada)
        total += n
    if total < 6:
        raise SystemExit('solo se envolvieron %d llamadas de 6' % total)
    with open(ruta + '.tmp', 'w', encoding='utf-8', newline='') as f:
        f.write(t.replace('\n', eol))
    os.replace(ruta + '.tmp', ruta)
    print('gpu_sw_renderer.c: %d llamadas recortadas a sus bandas' % total)


if __name__ == '__main__':
    main()
