# «Volver donde lo dejaste»: reanudar tras la terminación en segundo plano.
#
# En el modo desarrollador, la Xbox **TERMINA** un juego UWP que pasa a segundo plano (Microsoft, *System resources
# for UWP apps and games on Xbox One*: «Games will be suspended and terminated in the background»), así que al volver
# de Home la aplicación se relanza de cero. No es un fallo del port: el sistema la relanza con
# `PreviousExecutionState = Terminated` (3) y espera que la aplicación se restaure sola.
#
# Lo que hace esto viable es que el sistema de estados del framework **ya funciona**: `boot_state.c` serializa
# la máquina entera y `savestate.c` lo ejecuta en un punto seguro (block leader, `in_exception == 0`). Sin un
# serializador que funcione no habría nada que guardar al irse al fondo.
#
# Qué hace el parche:
#   - `savestate.h/.c`: una ranura reservada, **99** (`SAVESTATE_SLOT_SUSPEND`), fuera de las 12 del jugador, con su
#     archivo `state_<entrada>_suspend.pst` junto a las tarjetas, y `savestate_slot_discard()` para tirarla.
#   - `main.cpp`: `resume_state_note_background()` —en el bucle de eventos de SDL: cuando la ventana se oculta, se
#     minimiza o pierde el foco, se guarda la máquina; la aplicación sigue viva unos segundos antes de que la
#     consola la suspenda, y una vez suspendida ya no se podría— y `resume_state_maybe_restore()`, tras
#     `savestate_configure`: si el arranque viene de una terminación (`g_psx_prev_exec_state == 3`) y hay estado
#     guardado, se restaura; si no, se descarta, porque era de una sesión que terminó bien.
#   - En el PC está apagado salvo `PSX_RESUME_STATE=1`, y `PSX_PREV_EXEC_STATE=<n>` simula el relanzamiento (3 =
#     Terminated), que es como se prueba sin consola.
#
# El estado de activación lo pone la entrada UWP en `g_psx_prev_exec_state`; en la consola `AppInstance::
# GetActivatedEventArgs()` devuelve nulo, así que quien lo anota de verdad es el SDL2 compilado para WindowsStore,
# en `SDL_WinRTApp::OnAppActivated`.
#
# Idempotente y todo o nada; escritura atómica. Los comentarios del código van en inglés, como el resto del runtime.
# Uso: parche_uwp_reanudar.py <raíz del proyecto del juego>
import parchear

MARCA = 'Recompilaciones (2026-10-06): resume after termination'

# ---------------------------------------------------------------- savestate.h
H_VIEJO = '''#define SAVESTATE_SLOTS 12'''
H_NUEVO = '''#define SAVESTATE_SLOTS 12

/* ''' + MARCA + '''. Reserved slot, outside the player's 12: the whole machine
 * saved when the console sends the game to the background, so the relaunch that follows a Dev Mode
 * termination can pick it up. Its file is state_<entry_pc>_suspend.pst, next to the memory cards. */
#define SAVESTATE_SLOT_SUSPEND 99'''

H_DISCARD_VIEJO = '''int savestate_slot_exists(int slot);'''
H_DISCARD_NUEVO = '''int savestate_slot_exists(int slot);

/* ''' + MARCA + ''': delete a slot's file (used for the reserved suspend slot,
 * so a session that ended normally never resumes into a stale machine). */
int savestate_slot_discard(int slot);'''

# ---------------------------------------------------------------- savestate.c
C_PATH_VIEJO = '''int savestate_slot_path(int slot, char* out, size_t cap) {
    if (!s_configured || !out || cap == 0) return 0;
    if (slot < 0 || slot >= SAVESTATE_SLOTS) return 0;'''
C_PATH_NUEVO = '''int savestate_slot_path(int slot, char* out, size_t cap) {
    if (!s_configured || !out || cap == 0) return 0;
    if (slot == SAVESTATE_SLOT_SUSPEND) {   /* ''' + MARCA + ''' */
        snprintf(out, cap, "%s%sstate_%08X_suspend.pst",
                 s_dir, (s_dir[0] ? "/" : ""), (unsigned)s_entry_pc);
        return 1;
    }
    if (slot < 0 || slot >= SAVESTATE_SLOTS) return 0;'''

C_SAVE_VIEJO = '''static int request_save_inner(int slot) {
    if (!s_configured) { fprintf(stderr, "savestate: not configured\\n"); return 0; }
    if (slot < 0 || slot >= SAVESTATE_SLOTS) return 0;'''
C_SAVE_NUEVO = '''static int request_save_inner(int slot) {
    if (!s_configured) { fprintf(stderr, "savestate: not configured\\n"); return 0; }
    if ((slot < 0 || slot >= SAVESTATE_SLOTS) && slot != SAVESTATE_SLOT_SUSPEND) return 0;'''

C_LOAD_VIEJO = '''static int request_load_inner(int slot) {
    if (!s_configured) { fprintf(stderr, "savestate: not configured\\n"); return 0; }
    if (slot < 0 || slot >= SAVESTATE_SLOTS) return 0;'''
C_LOAD_NUEVO = '''static int request_load_inner(int slot) {
    if (!s_configured) { fprintf(stderr, "savestate: not configured\\n"); return 0; }
    if ((slot < 0 || slot >= SAVESTATE_SLOTS) && slot != SAVESTATE_SLOT_SUSPEND) return 0;'''

C_DISCARD_VIEJO = '''int savestate_slot_mtime(int slot, int64_t* out_time) {'''
C_DISCARD_NUEVO = '''int savestate_slot_discard(int slot) {   /* ''' + MARCA + ''' */
    char path[600];
    if (!savestate_slot_path(slot, path, sizeof(path))) return 0;
    return remove(path) == 0;
}

int savestate_slot_mtime(int slot, int64_t* out_time) {'''

# ---------------------------------------------------------------- main.cpp
M_FUN_VIEJO = '''static int fps_telemetry_enabled(void) {'''
M_FUN_NUEVO = '''/* ==== ''' + MARCA + ''' ====
 * In Dev Mode the console TERMINATES a UWP game sent to the background, so coming back from Home
 * relaunched this one from scratch. The whole machine is saved when the window is hidden, minimized or
 * loses focus — the app keeps running for a few seconds before the console suspends it, and once
 * suspended nothing can be saved any more — and restored when the system relaunches the app after
 * terminating it. The UWP entry point publishes that activation state in g_psx_prev_exec_state
 * (3 = Terminated); on the console AppInstance returns null, so the value really comes from the
 * SDL2 built for WindowsStore (SDL_WinRTApp::OnAppActivated).
 * Off on the desktop unless PSX_RESUME_STATE=1; PSX_PREV_EXEC_STATE=<n> fakes the relaunch there. */
extern "C" int g_psx_prev_exec_state;

static Uint64 g_resume_quiet_until = 0;   /* no saves while a restore settles */

static int resume_state_enabled(void) {
#if defined(PSX_UWP)
    return 1;
#else
    const char* e = std::getenv("PSX_RESUME_STATE");
    return e && e[0] && e[0] != '0';
#endif
}

/* Periodic save, which is what actually makes "come back where you left it" work on the console: the
 * suspension notice arrives, but the emulator never gets to run again, so a state staged there is never
 * written. Staged like any other save (deferred to a safe block boundary), so it does not interrupt the
 * game; the interval is deliberately long enough not to be felt. */
#ifndef PSX_RESUME_AUTOSAVE_MS
#define PSX_RESUME_AUTOSAVE_MS 10000
#endif

static void resume_state_tick(void) {
    static Uint64 next = 0;
    if (!resume_state_enabled()) return;
    const Uint64 now = SDL_GetTicks64();
    if (now < g_resume_quiet_until) return;
    if (!next) { next = now + PSX_RESUME_AUTOSAVE_MS; return; }
    if (now < next) return;
    next = now + PSX_RESUME_AUTOSAVE_MS;
    if (savestate_pending()) return;
    savestate_request_save(SAVESTATE_SLOT_SUSPEND);
}

static void resume_state_note_background(int window_event) {
    if (!resume_state_enabled()) return;
    if (savestate_pending()) return;                  /* a save/load is already staged */
    if (SDL_GetTicks64() < g_resume_quiet_until) return;
    if (savestate_request_save(SAVESTATE_SLOT_SUSPEND))
        std::fprintf(stdout, "resume: window event %d -> saving the machine for a relaunch\\n",
                     window_event);
}

/* SDL hands the WinRT suspension notices (SDL_APP_WILLENTERBACKGROUND / DIDENTERBACKGROUND) to an
 * event WATCH, synchronously, because once the app is suspended nobody pumps the queue any more — on
 * the console no SDL_WINDOWEVENT ever reaches the main loop before the system terminates the game.
 * The watch also logs what arrived, so the console can be diagnosed from the PC. */
static int SDLCALL resume_state_watch(void *data, SDL_Event *ev) {
    (void)data;
    if (!ev) return 0;
    if (ev->type == SDL_APP_WILLENTERBACKGROUND || ev->type == SDL_APP_DIDENTERBACKGROUND ||
        ev->type == SDL_APP_TERMINATING) {
        std::fprintf(stdout, "resume: app event 0x%X\\n", (unsigned)ev->type);
        std::fflush(stdout);
        resume_state_note_background((int)ev->type);
        /* NO waiting here: in WinRT this watch runs on the SAME thread as the emulator (SDL calls
         * it from SDL_PumpEvents), so sleeping would block the very loop that has to write the
         * state. The save lands at the next safe block boundary, during the seconds the console
         * still gives the app before terminating it. */
    } else if (ev->type == SDL_WINDOWEVENT) {
        std::fprintf(stdout, "resume: window event %d\\n", (int)ev->window.event);
        std::fflush(stdout);
    }
    return 0;
}

static void resume_state_maybe_restore(void) {
    if (!resume_state_enabled()) return;
    int prev = g_psx_prev_exec_state;
#if !defined(PSX_UWP)
    if (const char* e = std::getenv("PSX_PREV_EXEC_STATE")) prev = std::atoi(e);
#endif
    static int watching = 0;
    if (!watching) { SDL_AddEventWatch(resume_state_watch, NULL); watching = 1; }
    const int have = savestate_slot_exists(SAVESTATE_SLOT_SUSPEND);
    std::fprintf(stdout, "resume: previous execution state %d, saved machine %s\\n",
                 prev, have ? "present" : "absent");
    g_resume_quiet_until = SDL_GetTicks64() + 5000;
    if (prev == 3 && have) {
        if (savestate_request_load(SAVESTATE_SLOT_SUSPEND)) {
            g_resume_quiet_until = SDL_GetTicks64() + 15000;   /* let the restore land first */
            std::fprintf(stdout, "resume: terminated in the background -> restoring the saved machine\\n");
        }
    } else if (have) {
        savestate_slot_discard(SAVESTATE_SLOT_SUSPEND);
        std::fprintf(stdout, "resume: the last session ended normally -> saved machine discarded\\n");
    }
}

static int fps_telemetry_enabled(void) {'''

M_TICK_VIEJO = '''    if (fps_telemetry_enabled() && !psx_netplay_in_load_barrier()) {'''
M_TICK_NUEVO = '''    resume_state_tick();   /* ''' + MARCA + ''' */
    if (fps_telemetry_enabled() && !psx_netplay_in_load_barrier()) {'''

M_TOAST_VIEJO = '''extern "C" void psx_frontend_on_savestate_notify(int is_load, int slot, int ok) {
    char buf[64];
    const int disp = slot + 1;'''
M_TOAST_NUEVO = '''extern "C" void psx_frontend_on_savestate_notify(int is_load, int slot, int ok) {
    char buf[64];
    const int disp = slot + 1;
    /* ''' + MARCA + '''. The reserved slot is the port's own business: it is
     * written every few seconds while playing, so it must not put a toast on screen. */
    if (slot == SAVESTATE_SLOT_SUSPEND) {
        if (!is_load && ok) psx_savestate_menu_note_slots_changed();
        if (is_load && ok) savestate_input_guard_arm();
        return;
    }'''

M_EV_VIEJO = '''            } else if (ev.type == SDL_CONTROLLERDEVICEADDED) {
                refresh_player_devices();
            } else if (ev.type == SDL_CONTROLLERDEVICEREMOVED) {
                bool ours = false;'''
M_EV_NUEVO = '''            } else if (ev.type == SDL_WINDOWEVENT &&
                       (ev.window.event == SDL_WINDOWEVENT_HIDDEN ||
                        ev.window.event == SDL_WINDOWEVENT_MINIMIZED ||
                        ev.window.event == SDL_WINDOWEVENT_FOCUS_LOST)) {
                /* ''' + MARCA + ''' */
                resume_state_note_background((int)ev.window.event);
            } else if (ev.type == SDL_CONTROLLERDEVICEADDED) {
                refresh_player_devices();
            } else if (ev.type == SDL_CONTROLLERDEVICEREMOVED) {
                bool ours = false;'''

M_CFG_VIEJO = '''                            bios_token, openbios_ws);
        psx_rewind_set_depth((uint32_t)g_rewind_depth);'''
M_CFG_NUEVO = '''                            bios_token, openbios_ws);
        resume_state_maybe_restore();   /* ''' + MARCA + ''' */
        psx_rewind_set_depth((uint32_t)g_rewind_depth);'''


def main():
    raiz = parchear.raiz()
    parchear.informe(
        parchear.aplicar(parchear.runtime(raiz, 'include', 'savestate.h'),
                         [(H_VIEJO, H_NUEVO), (H_DISCARD_VIEJO, H_DISCARD_NUEVO)], MARCA,
                         'savestate.h (la ranura reservada)'),
        parchear.aplicar(parchear.runtime(raiz, 'src', 'savestate.c'),
                         [(C_PATH_VIEJO, C_PATH_NUEVO), (C_SAVE_VIEJO, C_SAVE_NUEVO),
                          (C_LOAD_VIEJO, C_LOAD_NUEVO), (C_DISCARD_VIEJO, C_DISCARD_NUEVO)], MARCA,
                         'savestate.c (ruta, peticiones y descarte)'),
        parchear.aplicar(parchear.runtime(raiz, 'src', 'main.cpp'),
                         [(M_FUN_VIEJO, M_FUN_NUEVO), (M_TICK_VIEJO, M_TICK_NUEVO),
                          (M_EV_VIEJO, M_EV_NUEVO), (M_TOAST_VIEJO, M_TOAST_NUEVO),
                          (M_CFG_VIEJO, M_CFG_NUEVO)], MARCA,
                         'main.cpp (guardar al irse al fondo y restaurar al volver)'))


if __name__ == '__main__':
    main()
