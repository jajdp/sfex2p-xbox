/* Software-only UWP replacement for the desktop OpenGL backend.
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
