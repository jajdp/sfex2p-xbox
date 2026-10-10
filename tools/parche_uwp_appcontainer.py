# Las APIs que quedan sin resolver al enlazar el perfil UWP SOLO contra `WindowsApp.lib` —la biblioteca paraguas del
# App Container—, que es lo que hay que hacer para que el ejecutable importe el CRT de la consola (las variantes
# `_app`) y no el de escritorio. Con el entorno de escritorio esto no se notaba: lo resolvía `kernel32.lib`.
#   1. Las **fibras**, que son el motor del planificador del BIOS: en el App Container no están `CreateFiber` ni
#      `ConvertThreadToFiber`, solo sus variantes `…Ex`. El camino aparte se elige por `WINAPI_FAMILY`, que es
#      la macro con la que el SDK distingue una aplicación del App Container.
#   2. El **objeto de trabajo** con el que la autocompilación mata el árbol de procesos del compilador: en la consola
#      no se lanza ninguno (el perfil ya dejó fuera `CreateProcess`), así que `s_job` es siempre NULL y la llamada es
#      código muerto; se deja fuera para no importar `TerminateJobObject`, que tampoco existe.
# Idempotente y todo o nada; escritura atómica.
# Uso: parche_uwp_appcontainer.py <raíz del proyecto del juego>
import parchear

MARCA = 'Recompilaciones (2026-10-05): App Container'

FIBRA_VIEJO = '''#include "psx_fiber.h"

#if defined(_WIN32)

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
'''

FIBRA_NUEVO = '''#include "psx_fiber.h"

/* ''' + MARCA + ''': the App Container exports neither CreateFiber nor ConvertThreadToFiber,
 * only CreateFiberEx and ConvertThreadToFiberEx. The block below is the desktop one; the one in the
 * middle is the console's. */
#if defined(_WIN32) && defined(WINAPI_FAMILY) && WINAPI_FAMILY == WINAPI_FAMILY_APP

#define WIN32_LEAN_AND_MEAN
#include <windows.h>

psx_fiber_t psx_fiber_convert_thread(void)
{
    void* fiber = ConvertThreadToFiberEx(NULL, FIBER_FLAG_FLOAT_SWITCH);
    if (!fiber && GetLastError() == ERROR_ALREADY_FIBER)
        fiber = GetCurrentFiber();
    return (psx_fiber_t)fiber;
}

psx_fiber_t psx_fiber_current(void)
{
    return (psx_fiber_t)GetCurrentFiber();
}

psx_fiber_t psx_fiber_create(size_t stack_size, psx_fiber_entry entry, void* arg)
{
    return (psx_fiber_t)CreateFiberEx((SIZE_T)stack_size, 0,
                                      FIBER_FLAG_FLOAT_SWITCH,
                                      (LPFIBER_START_ROUTINE)entry, arg);
}

void psx_fiber_switch(psx_fiber_t target)
{
    if (target) SwitchToFiber((LPVOID)target);
}

void psx_fiber_destroy(psx_fiber_t fiber)
{
    if (fiber) DeleteFiber((LPVOID)fiber);
}

#elif defined(_WIN32)

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
'''

JOB_VIEJO = '''    /* Kill the compile tree; the dying pipe write end unblocks the watcher. */
    if (s_job) TerminateJobObject(s_job, 1);
    else if (proc_dup) TerminateProcess(proc_dup, 1);
'''

JOB_NUEVO = '''    /* Kill the compile tree; the dying pipe write end unblocks the watcher. */
#if defined(PSX_UWP)
    /* ''' + MARCA + ''': there are no job objects in the App Container, and the
     * console never launches a compiler, so s_job is always NULL. */
    if (proc_dup) TerminateProcess(proc_dup, 1);
#else
    if (s_job) TerminateJobObject(s_job, 1);
    else if (proc_dup) TerminateProcess(proc_dup, 1);
#endif
'''


def main():
    raiz = parchear.raiz()
    parchear.informe(
        parchear.aplicar(parchear.runtime(raiz, 'src', 'psx_fiber.c'),
                         [(FIBRA_VIEJO, FIBRA_NUEVO)], MARCA,
                         'psx_fiber.c (fibras del App Container)'),
        parchear.aplicar(parchear.runtime(raiz, 'src', 'autocompile.c'),
                         [(JOB_VIEJO, JOB_NUEVO)], MARCA,
                         'autocompile.c (sin objeto de trabajo)'))


if __name__ == '__main__':
    main()
