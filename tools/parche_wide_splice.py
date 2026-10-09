# -*- coding: utf-8 -*-
# El 16:9 a 60 FPS en la consola: la pasada ancha deja de redibujar el centro.
#
# EL PROBLEMA (medido en la consola el 2026-10-06, con la demostración del propio juego y el cronómetro
# de `diag_perf_ancho.py`): en 16:9 las peleas iban a **51-55 FPS (0,85-0,92x)** y en 4:3 a **60-62 (1,00x)**. En
# modo ancho el rasterizador por software dibuja **cada primitiva dos veces** —una en la VRAM fiel y otra en la
# superficie ancha—, y esa segunda pasada costaba **3,4-3,6 ms de cada cuadro** (unas 25 000 primitivas por segundo),
# más de lo que sobra en un cuadro de 16,68 ms.
#
# LA IDEA. El centro de la superficie ancha es una copia 1:1 de la VRAM: la traslación entre las dos es un entero
# (`wide_dx`), así que los mismos píxeles salen de las mismas cuentas. Lo único que la superficie ancha aporta son
# los **márgenes** que el 4:3 no muestra. Entonces:
#   1. al componer la imagen para presentar (`sw_render_wide_display`), las columnas del centro se leen **de la
#      VRAM**, que ya está dibujada, en vez de la superficie ancha; y
#   2. en la pasada ancha se **saltan las primitivas que no llegan a los márgenes**, que en este juego son casi
#      todas: sus escenarios están modelados para el encuadre 4:3 (técnico §4.6).
# El resultado es idéntico en pantalla y el trabajo de la segunda pasada baja a lo que de verdad se ve de más.
#
# SEGURIDAD. El estirado del fondo 2D (`wide_bd_get`) sí cambia el centro de la superficie ancha, así que en cuanto
# se usa una vez, el empalme se apaga para toda la sesión y todo vuelve al camino de siempre. En este juego está
# apagado (`[widescreen] nw_phase_backdrop = false`). El empalme tampoco se usa con el espejo de alta resolución
# (escala > 1), que la consola no usa.
#
# Idempotente y todo o nada; escritura atómica. Los comentarios del código van en inglés, como el resto del runtime.
# Uso: parche_wide_splice.py <raíz del proyecto del juego>
import os
import sys

if len(sys.argv) < 2:
    sys.exit('uso: %s <ruta de la raiz del proyecto del juego>' % os.path.basename(sys.argv[0]))
RAIZ = sys.argv[1]
MARCA = 'Recompilaciones (2026-10-06): native-wide centre splice'

# --- 1. las ayudas, junto a wide_dx ------------------------------------------------------------------
H_VIEJO = '''static inline int wide_dx(void) { return g_wide_off - g_wide_cur_base; }'''

H_NUEVO = '''static inline int wide_dx(void) { return g_wide_off - g_wide_cur_base; }

/* ==== ''' + MARCA + ''' ====
 * The centre of the wide surface is a 1:1 copy of canonical VRAM — the two differ by the INTEGER
 * translation wide_dx(), so identical inputs produce identical pixels. Only the revealed margins are
 * new. So the present path reads the centre columns straight from VRAM (sw_render_wide_display) and
 * the wide pass skips any primitive that does not reach a margin. On this game almost every primitive
 * is inside the 4:3 frame, which is where the second rasterization pass was being spent.
 * The 2D-backdrop stretch DOES change the centre of the wide surface: the first time it runs, the
 * splice is disabled for the rest of the session and everything goes back to the old path. */
#define WIDE_SPLICE_GUARD 2          /* keep primitives this close to the seam (scaled px) */
static int g_wide_splice = 1;        /* 0 once the backdrop stretch has been used */

static inline int wide_centre_lo(int s) { return g_wide_off * s; }
static inline int wide_centre_hi(int s) {
    int nw = g_wide_w - 2 * g_wide_off;
    return (g_wide_off + nw) * s;
}
/* 1 when the primitive spanning [xa,xb] (wide space, scaled px) has to be drawn. */
static inline int wide_needs_pass(int s, int xa, int xb) {
    if (!g_wide_splice || g_scale != 1) return 1;
    if (xa > xb) { int t = xa; xa = xb; xb = t; }
    return xa < wide_centre_lo(s) + WIDE_SPLICE_GUARD ||
           xb >= wide_centre_hi(s) - WIDE_SPLICE_GUARD;
}
static inline int wide_min3(int a, int b, int c) {
    int m = a < b ? a : b; return m < c ? m : c;
}
static inline int wide_max3(int a, int b, int c) {
    int m = a > b ? a : b; return m > c ? m : c;
}'''

# --- 2. el estirado del fondo apaga el empalme --------------------------------------------------------
BD_VIEJO = '''            b.center = (float)g_wide_cur_base + (float)native_w / 2.0f;'''
BD_NUEVO = '''            b.center = (float)g_wide_cur_base + (float)native_w / 2.0f;
            /* ''' + MARCA + ''': the stretch rewrites the centre too. */
            g_wide_splice = 0;'''

# --- 3. los cuatro triángulos -------------------------------------------------------------------------
def tri(nombre, args_extra):
    """Devuelve (viejo, nuevo) para un bloque de triángulo de la pasada ancha."""
    viejo = ('''        WideBd bd = wide_bd_get();
        ''' + nombre + '''(&wt,
''')
    return viejo


TRIS = [
    # (llamada, texto original de los argumentos, texto nuevo)
    ('''        WideBd bd = wide_bd_get();
        raster_flat_triangle(&wt,
            precise_wide_x(0,x0,s,dx,&bd), precise_scaled(1,0,y0,s),
            precise_wide_x(1,x1,s,dx,&bd), precise_scaled(1,1,y1,s),
            precise_wide_x(2,x2,s,dx,&bd), precise_scaled(1,2,y2,s), color);''',
     '''        WideBd bd = wide_bd_get();
        const int wx0 = precise_wide_x(0,x0,s,dx,&bd);
        const int wx1 = precise_wide_x(1,x1,s,dx,&bd);
        const int wx2 = precise_wide_x(2,x2,s,dx,&bd);
        if (wide_needs_pass(s, wide_min3(wx0,wx1,wx2), wide_max3(wx0,wx1,wx2)))
        raster_flat_triangle(&wt,
            wx0, precise_scaled(1,0,y0,s),
            wx1, precise_scaled(1,1,y1,s),
            wx2, precise_scaled(1,2,y2,s), color);'''),

    ('''        WideBd bd = wide_bd_get();
        raster_gouraud_triangle(&wt,
            precise_wide_x(0,x0,s,dx,&bd), precise_scaled(1,0,y0,s), c0,
            precise_wide_x(1,x1,s,dx,&bd), precise_scaled(1,1,y1,s), c1,
            precise_wide_x(2,x2,s,dx,&bd), precise_scaled(1,2,y2,s), c2);''',
     '''        WideBd bd = wide_bd_get();
        const int wx0 = precise_wide_x(0,x0,s,dx,&bd);
        const int wx1 = precise_wide_x(1,x1,s,dx,&bd);
        const int wx2 = precise_wide_x(2,x2,s,dx,&bd);
        if (wide_needs_pass(s, wide_min3(wx0,wx1,wx2), wide_max3(wx0,wx1,wx2)))
        raster_gouraud_triangle(&wt,
            wx0, precise_scaled(1,0,y0,s), c0,
            wx1, precise_scaled(1,1,y1,s), c1,
            wx2, precise_scaled(1,2,y2,s), c2);'''),

    ('''        WideBd bd = wide_bd_get();
        raster_textured_triangle(&wt,
                                 precise_wide_x(0,x0,s,dx,&bd), precise_scaled(1,0,y0,s), u0, v0,
                                 precise_wide_x(1,x1,s,dx,&bd), precise_scaled(1,1,y1,s), u1, v1,
                                 precise_wide_x(2,x2,s,dx,&bd), precise_scaled(1,2,y2,s), u2, v2,
                                 clut_x, clut_y, texpage, g_perspective_valid,
                                 g_perspective_q[0], g_perspective_q[1], g_perspective_q[2]);''',
     '''        WideBd bd = wide_bd_get();
        const int wx0 = precise_wide_x(0,x0,s,dx,&bd);
        const int wx1 = precise_wide_x(1,x1,s,dx,&bd);
        const int wx2 = precise_wide_x(2,x2,s,dx,&bd);
        if (wide_needs_pass(s, wide_min3(wx0,wx1,wx2), wide_max3(wx0,wx1,wx2)))
        raster_textured_triangle(&wt,
                                 wx0, precise_scaled(1,0,y0,s), u0, v0,
                                 wx1, precise_scaled(1,1,y1,s), u1, v1,
                                 wx2, precise_scaled(1,2,y2,s), u2, v2,
                                 clut_x, clut_y, texpage, g_perspective_valid,
                                 g_perspective_q[0], g_perspective_q[1], g_perspective_q[2]);'''),

    ('''        WideBd bd = wide_bd_get();
        raster_shaded_textured_triangle(&wt,
            precise_wide_x(0,x0,s,dx,&bd), precise_scaled(1,0,y0,s), u0, v0, r0, g0, b0,
            precise_wide_x(1,x1,s,dx,&bd), precise_scaled(1,1,y1,s), u1, v1, r1, g1, b1,
            precise_wide_x(2,x2,s,dx,&bd), precise_scaled(1,2,y2,s), u2, v2, r2, g2, b2,
            clut_x, clut_y, texpage, raw_texture, g_perspective_valid,
            g_perspective_q[0], g_perspective_q[1], g_perspective_q[2]);''',
     '''        WideBd bd = wide_bd_get();
        const int wx0 = precise_wide_x(0,x0,s,dx,&bd);
        const int wx1 = precise_wide_x(1,x1,s,dx,&bd);
        const int wx2 = precise_wide_x(2,x2,s,dx,&bd);
        if (wide_needs_pass(s, wide_min3(wx0,wx1,wx2), wide_max3(wx0,wx1,wx2)))
        raster_shaded_textured_triangle(&wt,
            wx0, precise_scaled(1,0,y0,s), u0, v0, r0, g0, b0,
            wx1, precise_scaled(1,1,y1,s), u1, v1, r1, g1, b1,
            wx2, precise_scaled(1,2,y2,s), u2, v2, r2, g2, b2,
            clut_x, clut_y, texpage, raw_texture, g_perspective_valid,
            g_perspective_q[0], g_perspective_q[1], g_perspective_q[2]);'''),
]

# --- 4. el centro, desde la VRAM, al componer la imagen ------------------------------------------------
PRES_VIEJO = '''    for (int row = 0; row < out_h; row++) {
        int vy = disp_y * s + row;
        if (vy < 0) vy = 0;
        if (vy >= H) vy = H - 1;
        const uint16_t *src = surf + (size_t)vy * W;
        uint32_t *dst = (uint32_t *)((uint8_t *)out_pixels + row * out_pitch);
        for (int col = 0; col < W; col++) { dst[col] = rgb555_to_argb(src[col]); count++; }
    }
    return count;'''

PRES_NUEVO = '''    /* ''' + MARCA + ''': the centre columns come from canonical VRAM, which is
     * already drawn; the wide surface only owns the revealed margins. Falls back to the plain copy
     * when the splice is off (backdrop stretch), at scale > 1, or if the centre would leave VRAM. */
    const int native_w = g_wide_w - 2 * g_wide_off;
    const int c_lo = g_wide_off * s, c_hi = (g_wide_off + native_w) * s;
    const int splice = g_wide_splice && s == 1 && native_w > 0 &&
                       base_x >= 0 && base_x + native_w <= VRAM_WIDTH;
    for (int row = 0; row < out_h; row++) {
        int vy = disp_y * s + row;
        if (vy < 0) vy = 0;
        if (vy >= H) vy = H - 1;
        const uint16_t *src = surf + (size_t)vy * W;
        uint32_t *dst = (uint32_t *)((uint8_t *)out_pixels + row * out_pitch);
        if (splice) {
            const uint16_t *vram_row = g_vram + (size_t)vy * VRAM_WIDTH + base_x;
            for (int col = 0; col < c_lo; col++) { dst[col] = rgb555_to_argb(src[col]); count++; }
            for (int col = c_lo; col < c_hi; col++) { dst[col] = rgb555_to_argb(vram_row[col - c_lo]); count++; }
            for (int col = c_hi; col < W; col++) { dst[col] = rgb555_to_argb(src[col]); count++; }
        } else {
            for (int col = 0; col < W; col++) { dst[col] = rgb555_to_argb(src[col]); count++; }
        }
    }
    return count;'''


# --- 5. los rectángulos con textura -------------------------------------------------------------------
# La guarda va pegada al `else` a propósito: parche_wide_bandas.py toma los espacios que haya delante
# del `if` como sangría del bucle que escribe en su lugar.
R1_VIEJO = """        } else
            raster_textured_rect(&wt, (x+dx)*s, y*s, w*s, h*s, u, v, clut_x, clut_y, texpage);"""

R1_NUEVO = """        } else if (wide_needs_pass(s, (x+dx)*s, (x+w+dx)*s - 1))
            raster_textured_rect(&wt, (x+dx)*s, y*s, w*s, h*s, u, v, clut_x, clut_y, texpage);"""

R2_VIEJO = """        raster_textured_rect_scaled(&wt, (xl+dx)*s, y*s, (xr-xl)*s, h*s, u0, v0, u1, v1,
                                    clut_x, clut_y, texpage);"""

R2_NUEVO = """        if (wide_needs_pass(s, (xl+dx)*s, (xr+dx)*s - 1))
        raster_textured_rect_scaled(&wt, (xl+dx)*s, y*s, (xr-xl)*s, h*s, u0, v0, u1, v1,
                                    clut_x, clut_y, texpage);"""

RECTS = [(R1_VIEJO, R1_NUEVO), (R2_VIEJO, R2_NUEVO)]


def main():
    ruta = os.path.join(RAIZ, 'psxrecomp', 'runtime', 'src', 'gpu_sw_renderer.c')
    with open(ruta, 'rb') as f:
        crudo = f.read().decode('utf-8')
    eol = '\r\n' if '\r\n' in crudo else '\n'
    t = crudo.replace('\r\n', '\n')
    if MARCA in t:
        print('el parche ya estaba')
        return
    cambios = [(H_VIEJO, H_NUEVO), (BD_VIEJO, BD_NUEVO), (PRES_VIEJO, PRES_NUEVO)] + TRIS + RECTS
    for viejo, nuevo in cambios:
        if t.count(viejo) != 1:
            raise SystemExit('gpu_sw_renderer.c: %d apariciones de %r' % (t.count(viejo), viejo[:70]))
        t = t.replace(viejo, nuevo)
    with open(ruta + '.tmp', 'w', encoding='utf-8', newline='') as f:
        f.write(t.replace('\n', eol))
    os.replace(ruta + '.tmp', ruta)
    print('gpu_sw_renderer.c: empalme del centro (%d cambios)' % len(cambios))


if __name__ == '__main__':
    main()
