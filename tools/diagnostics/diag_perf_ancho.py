# -*- coding: utf-8 -*-
# Diagnóstico: cuánto cuesta la pasada ancha del 16:9 en el rasterizador por software.
#
# En modo ancho, cada primitiva se dibuja DOS veces: en la VRAM fiel y en la superficie ancha
# (`if (g_wide_cur) { … }`, siete sitios de gpu_sw_renderer.c). Esto cronometra ese segundo dibujo y lo publica
# una vez por segundo en el registro, junto al contador de FPS:
#     psxrecomp: [ancho] 128.4 ms/s en 112340 primitivas (2.14 ms/cuadro)
# Con eso se sabe cuánto hay que ganar antes de reescribir nada. Se quita con --quitar.
#
# Uso: diag_perf_ancho.py <raíz del proyecto del juego>
import os
import re
import sys

args = [a for a in sys.argv[1:] if not a.startswith('--')]
QUITAR = '--quitar' in sys.argv
if not args:
    sys.exit('uso: %s <ruta de la raiz del proyecto del juego>' % os.path.basename(sys.argv[0]))
RAIZ = args[0]
MARCA = 'Recompilaciones: cronometro de la pasada ancha'

CABECERA_VIEJA = '''static inline int wide_dx(void) { return g_wide_off - g_wide_cur_base; }'''
CABECERA_NUEVA = '''static inline int wide_dx(void) { return g_wide_off - g_wide_cur_base; }

/* ''' + MARCA + ''' */
#include <windows.h>
static LONGLONG g_wide_ticks = 0;
static uint64_t g_wide_prims = 0;
static uint64_t g_nat_prims = 0;
static inline LONGLONG wide_t0(void) {
    LARGE_INTEGER t; QueryPerformanceCounter(&t); return t.QuadPart;
}
static inline void wide_t1(LONGLONG t0) {
    LARGE_INTEGER t; QueryPerformanceCounter(&t);
    g_wide_ticks += t.QuadPart - t0;
    g_wide_prims++;
}
void sw_wide_perf_take(double *ms, unsigned long long *prims, unsigned long long *nat) {
    if (nat) *nat = g_nat_prims;
    g_nat_prims = 0;
    LARGE_INTEGER f; QueryPerformanceFrequency(&f);
    if (ms) *ms = f.QuadPart ? (double)g_wide_ticks * 1000.0 / (double)f.QuadPart : 0.0;
    if (prims) *prims = g_wide_prims;
    g_wide_ticks = 0;
    g_wide_prims = 0;
}'''

# El cronómetro, alrededor de cada uno de los siete bloques de la pasada ancha.
VIEJO_IF = '    if (g_wide_cur) {\n'
NUEVO_IF = '    if (g_wide_cur) {\n        const LONGLONG _wt0 = wide_t0();\n'

# main.cpp: la línea del registro, junto al contador de FPS.
MAIN_VIEJO = '''            if (!g_headless) {
                char osd[96];'''
MAIN_NUEVO = '''            {   /* ''' + MARCA + ''' */
                double wide_ms = 0.0; unsigned long long wide_prims = 0;
                sw_wide_perf_take(&wide_ms, &wide_prims);
                if (wide_prims)
                    std::fprintf(stdout,
                                 "psxrecomp: [ancho] %.1f ms/s en %llu primitivas (%.2f ms/cuadro)\\n",
                                 wide_ms, wide_prims, fps > 0.0 ? wide_ms / fps : 0.0);
            }
            if (!g_headless) {
                char osd[96];'''


# La declaración tiene que ir en ámbito global: dentro de una función, MSVC da C2598.
MAIN_DECL_VIEJO = '''static int fps_telemetry_enabled(void) {'''
MAIN_DECL_NUEVO = '''/* ''' + MARCA + ''' */
extern "C" void sw_wide_perf_take(double *ms, unsigned long long *prims, unsigned long long *nat);

static int fps_telemetry_enabled(void) {'''


def cerrar_bloques(t):
    """Pone el cierre del cronómetro al final de cada bloque de la pasada ancha."""
    salida = []
    i = 0
    n = 0
    while True:
        j = t.find(NUEVO_IF, i)
        if j < 0:
            salida.append(t[i:])
            break
        # busca el cierre del bloque contando llaves desde la apertura
        k = j + len(NUEVO_IF)
        nivel = 1
        while nivel and k < len(t):
            if t[k] == '{':
                nivel += 1
            elif t[k] == '}':
                nivel -= 1
                if nivel == 0:
                    break
            k += 1
        salida.append(t[i:k])
        salida.append('    wide_t1(_wt0);\n    ')
        i = k
        n += 1
    return ''.join(salida), n


def main():
    sw = os.path.join(RAIZ, 'psxrecomp', 'runtime', 'src', 'gpu_sw_renderer.c')
    mn = os.path.join(RAIZ, 'psxrecomp', 'runtime', 'src', 'main.cpp')
    with open(sw, 'rb') as f:
        crudo = f.read().decode('utf-8')
    eol = '\r\n' if '\r\n' in crudo else '\n'
    t = crudo.replace('\r\n', '\n')
    with open(mn, 'rb') as f:
        crudo_m = f.read().decode('utf-8')
    eol_m = '\r\n' if '\r\n' in crudo_m else '\n'
    m = crudo_m.replace('\r\n', '\n')

    if QUITAR:
        if MARCA not in t:
            print('el diagnóstico no estaba')
            return
        t = t.replace(CABECERA_NUEVA, CABECERA_VIEJA)
        t = t.replace('        const LONGLONG _wt0 = wide_t0();\n', '')
        t = t.replace('    wide_t1(_wt0);\n    ', '')
        m = m.replace(MAIN_NUEVO, MAIN_VIEJO)
        m = m.replace(MAIN_DECL_NUEVO, MAIN_DECL_VIEJO)
        mensaje = 'diagnóstico de la pasada ancha quitado'
    else:
        if MARCA in t:
            print('el diagnóstico ya estaba')
            return
        if t.count(CABECERA_VIEJA) != 1:
            raise SystemExit('gpu_sw_renderer.c: %d apariciones del ancla' % t.count(CABECERA_VIEJA))
        t = t.replace(CABECERA_VIEJA, CABECERA_NUEVA, 1)
        cuantos = t.count(VIEJO_IF)
        t = t.replace(VIEJO_IF, NUEVO_IF)
        t, cerrados = cerrar_bloques(t)
        if cuantos != cerrados:
            raise SystemExit('bloques abiertos %d, cerrados %d' % (cuantos, cerrados))
        if m.count(MAIN_VIEJO) != 1:
            raise SystemExit('main.cpp: %d apariciones del ancla' % m.count(MAIN_VIEJO))
        if m.count(MAIN_DECL_VIEJO) != 1:
            raise SystemExit('main.cpp: %d apariciones del ancla de la declaracion' % m.count(MAIN_DECL_VIEJO))
        m = m.replace(MAIN_DECL_VIEJO, MAIN_DECL_NUEVO, 1)
        m = m.replace(MAIN_VIEJO, MAIN_NUEVO, 1)
        mensaje = 'diagnóstico puesto en %d bloques de la pasada ancha' % cerrados

    for ruta, texto, fin in ((sw, t, eol), (mn, m, eol_m)):
        with open(ruta + '.tmp', 'w', encoding='utf-8', newline='') as f:
            f.write(texto.replace('\n', fin))
        os.replace(ruta + '.tmp', ruta)
    print(mensaje)


if __name__ == '__main__':
    main()
