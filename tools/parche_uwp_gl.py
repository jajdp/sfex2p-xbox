# -*- coding: utf-8 -*-
# Lo que le faltaba al perfil UWP para que la consola pueda ARRANCAR la aplicación. Comparando las
# importaciones del ejecutable que no arranca con las del port de Street Fighter EX Plus Alpha, que sí corre en la
# la consola, sobraban dos cosas (y ws2_32 NO era una de ellas: el que funciona también la importa):
#   1. `OPENGL32.dll` — el backend GL del runtime (`gpu_gl_renderer.c`) llama a GL 1.x directamente, y esa DLL no
#      existe en la consola. El framework de EX Plus Alpha lo resuelve con un `gpu_gl_renderer_stub.c` que este no
#      trae; aquí se escribe uno equivalente (mismos símbolos, todo inerte) y el perfil UWP lo compila en su lugar,
#      con lo que el runtime se queda con el dibujo por software, que es lo que usa la consola de todas formas.
#   2. `dbghelp`, `comdlg32` y `opengl32` en el enlace: en el App Container no existen, y basta con importarlas para
#      que la aplicación no se active. En UWP no hay que enlazar ninguna: `WindowsApp.lib` —la biblioteca paraguas
#      que CMake pone cuando CMAKE_SYSTEM_NAME es WindowsStore— ya trae lo permitido, los sockets incluidos.
# Idempotente y todo o nada; escritura atómica.
# Uso: parche_uwp_gl.py <raíz del proyecto del juego>
import os
import sys

if len(sys.argv) < 2:
    sys.exit('uso: %s <ruta de la raiz del proyecto del juego>' % os.path.basename(sys.argv[0]))
RAIZ = sys.argv[1]
MARCA = 'Recompilaciones (2026-10-05): UWP sin OpenGL'

# El sustituto del backend GL. Define exactamente los símbolos externos que define `gpu_gl_renderer.c` (sacados
# con `dumpbin /symbols` de su objeto), para que el resto del runtime enlace igual: las 39 funciones `gl_*` y las
# variables globales que leen `gpu_sw_renderer.c` y el servidor de depuración. Todas inertes: `gl_backend_get`
# devuelve NULL, que es la señal de «GL no disponible» que `gpu_render.c` ya sabe tratar (cae al software).
STUB = r'''/* Software-only UWP replacement for the desktop OpenGL backend.
 *
 * The console has no opengl32.dll: an import of it is enough to stop the app
 * from being activated. This TU keeps the rest of the runtime link-compatible
 * (gpu_render.c, gpu_sw_renderer.c and the debug server all reference these
 * symbols) while GL stays unavailable, so the software rasterizer is used.
 * gl_backend_get() returning NULL is the documented "GL unavailable" signal. */
#include "gpu_gl_renderer.h"
#include "gpu_render.h"

#include <stddef.h>
#include <string.h>

/* Widescreen backdrop-stretch knobs read by gpu_sw_renderer.c and reported by
 * the debug server; the GL backend owns them on the desktop build. */
int g_ws_bd_stretch_on = 1;
int g_ws_bd_stretch_pct = 0;
int g_ws_bd_phase_thresh = 24;
int g_ws_bd_phase_mode = 1;

/* Backdrop-geometry diagnostics (debug server "bdg"). */
int g_bdg_applied = 0;
int g_bdg_prims = 0;
int g_bdg_clearx = -999999;
int g_bdg_cur = 0;
int g_bdg_base = 0;
int g_bdg_w = 0;
int g_bdg_off = 0;

/* Primitive-trace snapshot count (debug server "ptrace"). */
int g_ptrace_n = 0;

const GpuRenderBackend *gl_backend_get(void)
{
    return NULL;
}

int gl_renderer_init_context(struct SDL_Window *win)
{
    (void)win;
    return 0;
}

void gl_renderer_set_swap_interval(int interval) { (void)interval; }

void gl_renderer_set_interpolation(int enabled, double host_hz, double target_hz,
                                   double source_hz, int blend_mode)
{
    (void)enabled; (void)host_hz; (void)target_hz; (void)source_hz;
    (void)blend_mode;
}

void gl_renderer_set_interpolation_suspended(int suspended) { (void)suspended; }

int gl_renderer_interpolation_owns_cadence(void) { return 0; }

void gl_renderer_interpolation_diag(int *enabled, int *suspended,
                                    int *history_frames,
                                    double *host_hz, double *target_hz,
                                    uint64_t *swaps)
{
    if (enabled) *enabled = 0;
    if (suspended) *suspended = 0;
    if (history_frames) *history_frames = 0;
    if (host_hz) *host_hz = 0.0;
    if (target_hz) *target_hz = 0.0;
    if (swaps) *swaps = 0;
}

void gl_renderer_runtime_diag(uint64_t out[6])
{
    if (out) memset(out, 0, sizeof(uint64_t) * 6);
}

void gl_renderer_present(const uint32_t *pixels, int src_w, int src_h, int linear,
                         int force_4_3, int content_w)
{
    (void)pixels; (void)src_w; (void)src_h; (void)linear; (void)force_4_3;
    (void)content_w;
}

int gl_renderer_set_bezel(const void *rgba, int w, int h)
{
    (void)rgba; (void)w; (void)h;
    return 0;
}

int gl_renderer_has_bezel(void) { return 0; }

void gl_renderer_present_blank(void) {}

int gl_renderer_present_hold_last(void) { return 0; }

void gl_renderer_sync_cpu(void) {}
void gl_renderer_flush_cpu_uploads(void) {}
void gl_renderer_invalidate_present(void) {}
void gl_renderer_restage_vram_after_savestate(void) {}

void gl_renderer_set_cpu_auth_dual(int on) { (void)on; }
void gl_renderer_set_fmv_filter(int cfg_value) { (void)cfg_value; }
int  gl_renderer_cpu_auth_dual(void) { return 0; }

void gl_renderer_present_probe_reset(void) {}

void gl_renderer_present_probe_take(uint64_t *skip_delta, uint64_t *swap_delta,
                                    uint64_t *dirty_mark_delta,
                                    int *force_remaining)
{
    if (skip_delta) *skip_delta = 0;
    if (swap_delta) *swap_delta = 0;
    if (dirty_mark_delta) *dirty_mark_delta = 0;
    if (force_remaining) *force_remaining = 0;
}

int gl_renderer_present_rect_dirty(int disp_x, int disp_y, int w, int h)
{
    (void)disp_x; (void)disp_y; (void)w; (void)h;
    return 0;
}

void gl_renderer_present_vram(int disp_x, int disp_y, int w, int h, int linear,
                              int force_4_3)
{
    (void)disp_x; (void)disp_y; (void)w; (void)h; (void)linear; (void)force_4_3;
}

int gl_renderer_present_wide_fbo(int disp_x, int disp_y, int disp_h, int linear)
{
    (void)disp_x; (void)disp_y; (void)disp_h; (void)linear;
    return 0;
}

void gl_renderer_set_display_aspect(int num, int den) { (void)num; (void)den; }

void gl_renderer_set_wide_fast(int on) { (void)on; }
int  gl_renderer_get_wide_fast(void) { return 0; }

void gl_renderer_shutdown(void) {}

int gl_renderer_fbo_peek(int x, int y, int w, int h, uint16_t *out)
{
    (void)x; (void)y; (void)w; (void)h; (void)out;
    return 0;
}

void gl_renderer_diag(int *gpu_dirty, int pending[5], int pack[5])
{
    if (gpu_dirty) *gpu_dirty = 0;
    if (pending) memset(pending, 0, sizeof(int) * 5);
    if (pack) memset(pack, 0, sizeof(int) * 5);
}

uint64_t gl_renderer_coh_total(void) { return 0; }

int gl_renderer_coh_get(uint64_t seq, GlCohEvent *out)
{
    (void)seq;
    if (out) memset(out, 0, sizeof(*out));
    return 0;
}

uint64_t gl_renderer_pres_total(void) { return 0; }

int gl_renderer_pres_get(uint64_t seq, GlPresEvent *out)
{
    (void)seq;
    if (out) memset(out, 0, sizeof(*out));
    return 0;
}

int gl_renderer_perf_aggregate(int wide_filter, double out[18])
{
    (void)wide_filter;
    if (out) memset(out, 0, sizeof(double) * 18);
    return 0;
}

void gl_renderer_set_ws_ablate(int mode) { (void)mode; }
int  gl_renderer_get_ws_ablate(void) { return 0; }

uint64_t gl_renderer_perf_prim_split(double *out_tex_frac)
{
    if (out_tex_frac) *out_tex_frac = 0.0;
    return 0;
}

void gl_renderer_batch_diag(uint64_t out[8])
{
    if (out) memset(out, 0, sizeof(uint64_t) * 8);
}

int gl_renderer_vram_diff(uint32_t *count, int bbox[4],
                          int samples[8][2], uint16_t samples_px[8][2])
{
    if (count) *count = 0;
    if (bbox) memset(bbox, 0, sizeof(int) * 4);
    if (samples) memset(samples, 0, sizeof(int) * 8 * 2);
    if (samples_px) memset(samples_px, 0, sizeof(uint16_t) * 8 * 2);
    return 0;
}
'''

CAMBIOS = [
    # 1. la selección de la fuente del backend GL, justo antes de la lista de fuentes del runtime
    ('''set(PSXRECOMP_RUNTIME_SOURCES
    ${PSXRECOMP_ROOT}/runtime/src/main.cpp''',
     '''# ''' + MARCA + ''': en la consola no hay opengl32.dll, y con solo importarla la aplicación no se
# activa. El perfil UWP compila un sustituto inerte y el runtime se queda con el dibujo por software.
if(PSX_UWP)
    set(PSXRECOMP_GL_RENDERER_SOURCE
        ${PSXRECOMP_ROOT}/runtime/src/gpu_gl_renderer_stub.c)
else()
    set(PSXRECOMP_GL_RENDERER_SOURCE
        ${PSXRECOMP_ROOT}/runtime/src/gpu_gl_renderer.c)
endif()

set(PSXRECOMP_RUNTIME_SOURCES
    ${PSXRECOMP_ROOT}/runtime/src/main.cpp'''),

    # 2. la fuente, dentro de la lista
    ('''    ${PSXRECOMP_ROOT}/runtime/src/gpu_gl_renderer.c
    ${PSXRECOMP_ROOT}/runtime/src/gpu_vk_renderer.c''',
     '''    ${PSXRECOMP_GL_RENDERER_SOURCE}
    ${PSXRECOMP_ROOT}/runtime/src/gpu_vk_renderer.c'''),

    # 3. el enlace: en UWP, ninguna de las cuatro bibliotecas de escritorio
    ('''    if(WIN32 OR MINGW)
        # opengl32: GL backend (gpu_gl_renderer.c). GL 1.x is exported directly''',
     '''    if(PSX_UWP)
        # ''' + MARCA + ''': en el App Container no existen opengl32, dbghelp ni comdlg32, y
        # basta con importarlas para que la consola no active la aplicación. No hay que enlazar nada:
        # WindowsApp.lib —la biblioteca paraguas que CMake pone para WindowsStore— trae lo permitido,
        # los sockets del cliente de lobby incluidos (el port de SF EX Plus Alpha, que sí arranca,
        # también importa ws2_32.dll).
    elseif(WIN32 OR MINGW)
        # opengl32: GL backend (gpu_gl_renderer.c). GL 1.x is exported directly'''),
]


def main():
    cmake = os.path.join(RAIZ, 'psxrecomp', 'runtime', 'runtime.cmake')
    stub = os.path.join(RAIZ, 'psxrecomp', 'runtime', 'src', 'gpu_gl_renderer_stub.c')
    with open(cmake, 'rb') as f:
        crudo = f.read().decode('utf-8-sig')
    eol = '\r\n' if '\r\n' in crudo else '\n'
    t = crudo.replace('\r\n', '\n')
    if MARCA in t:
        print('el parche ya estaba')
        return
    for viejo, nuevo in CAMBIOS:
        if t.count(viejo) != 1:
            raise SystemExit('runtime.cmake: %d apariciones de %r' % (t.count(viejo), viejo[:60]))
        t = t.replace(viejo, nuevo)
    # el sustituto, con los finales de línea del framework
    with open(stub + '.tmp', 'w', encoding='utf-8', newline='') as f:
        f.write(STUB.replace('\n', eol))
    os.replace(stub + '.tmp', stub)
    with open(cmake + '.tmp', 'w', encoding='utf-8-sig', newline='') as f:
        f.write(t.replace('\n', eol))
    os.replace(cmake + '.tmp', cmake)
    print('gpu_gl_renderer_stub.c escrito y runtime.cmake con %d cambios (UWP sin OpenGL)' % len(CAMBIOS))


if __name__ == '__main__':
    main()
