# -*- coding: utf-8 -*-
# El disco, ANTES de validar los mods.
#
# El framework comprueba los paquetes de mods —y con ellos la huella del disco que cada uno exige— **antes** de
# resolver dónde está el disco de verdad: `mod_runtime_commit(resolved_disc)` ocurre unas líneas antes que
# `resolved_disc = resolve_disc_for_runtime(...)`. En el PC no se nota, porque a esas alturas `resolved_disc` ya
# trae la ruta que el game.toml del proyecto lleva escrita. En la consola esa ruta no puede existir: el disco vive
# en el LocalState del paquete y su ruta depende de la instalación, así que el empaquetado la deja fuera. Resultado:
# el sistema de mods calculaba la huella de un disco vacío y rechazaba el arranque con
#     psxrecomp: cannot launch with selected mods: package does not target this game/image: sfex2p.es
# (el 16:9 pasaba porque no exige huella de disco; el menú en español sí).
#
# El parche resuelve el disco desde `disc.cfg` —el puntero que escribe la entrada UWP con la ruta real— justo antes
# de esa comprobación, y solo cuando hace falta.
#
# Idempotente y todo o nada; escritura atómica.
# Uso: parche_uwp_disco_mods.py <raíz del proyecto del juego>
import os
import sys

if len(sys.argv) < 2:
    sys.exit('uso: %s <ruta de la raiz del proyecto del juego>' % os.path.basename(sys.argv[0]))
RAIZ = sys.argv[1]
MARCA = 'Recompilaciones (2026-10-05): UWP — disc before mods'

VIEJO = '''    {
        /* Netplay must stay vanilla: launcher commit_netplay clears the plan,
         * but a following offline-style commit would re-resolve enabled mods
         * from disk. Skip commit entirely when this session is netplay. */
        std::string mod_error;'''

NUEVO = '''#if defined(PSX_UWP)
    /* ''' + MARCA + '''. Mods are validated here, but the disc is only
     * resolved further down (resolve_disc_for_runtime). On the console game.toml cannot carry the disc path —
     * it lives in the package's LocalState — so resolve it from the disc.cfg sidecar first; otherwise every
     * package that targets a disc digest fails with "does not target this game/image". */
    if (resolved_disc.empty() || !std::filesystem::exists(resolved_disc)) {
        std::filesystem::path uwp_disc = read_cached_path(argv[0], "disc.cfg");
        if (!uwp_disc.empty()) {
            uwp_disc = normalize_disc_path_for_launch(uwp_disc);
            if (std::filesystem::exists(uwp_disc)) {
                resolved_disc = uwp_disc;
                std::fprintf(stdout, "psxrecomp: UWP — disc for mods: %s\\n",
                             resolved_disc.string().c_str());
            }
        }
    }
#endif
    {
        /* Netplay must stay vanilla: launcher commit_netplay clears the plan,
         * but a following offline-style commit would re-resolve enabled mods
         * from disk. Skip commit entirely when this session is netplay. */
        std::string mod_error;'''


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
    print('main.cpp: en la consola, el disco se resuelve antes de comprobar los mods')


if __name__ == '__main__':
    main()
