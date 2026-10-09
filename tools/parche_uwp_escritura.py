# -*- coding: utf-8 -*-
# Lo que la consola tiene que poder ESCRIBIR: tarjetas de memoria y estados.
#
# Hallado el 2026-10-06 probando la reanudación, en el registro de la consola:
#     savestate: SAVE FAILED slot 99 -> S:\Program Files\WindowsApps\<paquete>\saves/scph1001/state_…pst
# Esa es la **carpeta de instalación**, que es de solo lectura. El motivo: el `game.toml` se carga de ahí (es lo
# que el runtime encuentra primero) y su `[runtime] memcard_dir = "saves"` es una ruta RELATIVA, que se resuelve
# contra la carpeta de ese mismo archivo. Así que todo lo que el juego quiere escribir —las dos tarjetas de memoria
# y los estados— apuntaba a un sitio donde no se puede escribir. El parche de las rutas (`parche_uwp_rutas.py`) no
# lo cubría: aquel cambia el ancla del runtime, no la ruta que ya venía resuelta desde el game.toml.
#
# El parche la vuelve a anclar en la carpeta de datos (LocalState) en cuanto queda resuelta: si es relativa, se
# cuelga de ahí; si es absoluta y cae fuera, se sustituye por la carpeta del mismo nombre dentro de los datos.
#
# ⚠ Esto vale para cualquier port de este framework a la consola: sin ello el juego parece funcionar, pero no
# guarda nada.
#
# Idempotente y todo o nada; escritura atómica. Los comentarios del código van en inglés, como el resto del runtime.
# Uso: parche_uwp_escritura.py <raíz del proyecto del juego>
import os
import sys

if len(sys.argv) < 2:
    sys.exit('uso: %s <ruta de la raiz del proyecto del juego>' % os.path.basename(sys.argv[0]))
RAIZ = sys.argv[1]
MARCA = 'Recompilaciones (2026-10-06): writable state on the console'

VIEJO = '''    /* Resolve the effective memory-card directory now (before the launcher) so
     * the launcher can introspect the real card files. The same default is used'''

NUEVO = '''#if defined(PSX_UWP)
    /* ''' + MARCA + '''. game.toml is loaded from the read-only install folder,
     * so its relative [runtime] memcard_dir ("saves") resolved against THAT folder and every write —
     * both memory cards and save states — failed with SAVE FAILED / no card file. Anchor it on the
     * writable data folder (the same root exe_dir_from_argv returns on this port). */
    {
        const std::filesystem::path uwp_root = exe_dir_from_argv(argv[0]);
        const std::string root_s = uwp_root.string();
        if (memcard_dir.empty()) {
            memcard_dir = uwp_root;
        } else if (memcard_dir.is_relative()) {
            memcard_dir = (uwp_root / memcard_dir).lexically_normal();
        } else if (memcard_dir.string().compare(0, root_s.size(), root_s) != 0) {
            memcard_dir = (uwp_root / memcard_dir.filename()).lexically_normal();
        }
        for (std::filesystem::path *p : { &memcard1_path, &memcard2_path }) {
            if (p->empty()) continue;
            if (p->is_relative()) *p = (memcard_dir / *p).lexically_normal();
            else if (p->string().compare(0, root_s.size(), root_s) != 0)
                *p = (memcard_dir / p->filename()).lexically_normal();
        }
        std::error_code uwp_ec;
        std::filesystem::create_directories(memcard_dir, uwp_ec);
        std::fprintf(stdout, "psxrecomp: UWP — writable state directory = %s\\n",
                     memcard_dir.string().c_str());
    }
#endif
    /* Resolve the effective memory-card directory now (before the launcher) so
     * the launcher can introspect the real card files. The same default is used'''


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
    print('main.cpp: en la consola, las tarjetas y los estados van a la carpeta de datos')


if __name__ == '__main__':
    main()
