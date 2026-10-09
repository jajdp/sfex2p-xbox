# -*- coding: utf-8 -*-
# Diagnóstico temporal: por qué un paquete de mods «does not target this game/image» en la consola.
# Imprime, al comprobar los mods, la ruta del disco que recibe el runtime, la huella que calcula y el error de
# cálculo si lo hubo. Se quita con --quitar cuando ya no hace falta.
# Uso: diag_mods.py <raíz del proyecto del juego>
import os
import sys

args = [a for a in sys.argv[1:] if not a.startswith('--')]
QUITAR = '--quitar' in sys.argv
if not args:
    sys.exit('uso: %s <ruta de la raiz del proyecto del juego>' % os.path.basename(sys.argv[0]))
RAIZ = args[0]
MARCA = 'Recompilaciones: diagnóstico de mods'

VIEJO = '''    if (disc_path != s.disc_path) {
        std::string hash_error;
        std::string digest;
        if (!sha256_file(disc_path, digest, &hash_error)) digest.clear();
        s.disc_path = disc_path;
        s.disc_sha256 = std::move(digest);
    }'''

NUEVO = '''    if (disc_path != s.disc_path) {
        std::string hash_error;
        std::string digest;
        if (!sha256_file(disc_path, digest, &hash_error)) digest.clear();
        /* ''' + MARCA + ''' */
        std::fprintf(stdout, "psxrecomp: [diag] disco=%s sha=%s err=%s exe_sha=%s\\n",
                     disc_path.string().c_str(),
                     digest.empty() ? "(vacia)" : digest.c_str(),
                     hash_error.empty() ? "(ninguno)" : hash_error.c_str(),
                     s.exe_sha256.empty() ? "(vacia)" : s.exe_sha256.c_str());
        s.disc_path = disc_path;
        s.disc_sha256 = std::move(digest);
    }'''


def main():
    ruta = os.path.join(RAIZ, 'psxrecomp', 'runtime', 'src', 'mod_runtime.cpp')
    with open(ruta, 'rb') as f:
        crudo = f.read().decode('utf-8')
    eol = '\r\n' if '\r\n' in crudo else '\n'
    t = crudo.replace('\r\n', '\n')
    puesto = MARCA in t
    if QUITAR:
        if not puesto:
            print('el diagnóstico no estaba')
            return
        if t.count(NUEVO) != 1:
            raise SystemExit('mod_runtime.cpp: no encuentro el bloque del diagnóstico')
        t = t.replace(NUEVO, VIEJO)
        mensaje = 'mod_runtime.cpp: diagnóstico quitado'
    else:
        if puesto:
            print('el diagnóstico ya estaba')
            return
        if t.count(VIEJO) != 1:
            raise SystemExit('mod_runtime.cpp: %d apariciones del ancla' % t.count(VIEJO))
        t = t.replace(VIEJO, NUEVO)
        mensaje = 'mod_runtime.cpp: diagnóstico puesto'
    with open(ruta + '.tmp', 'w', encoding='utf-8', newline='') as f:
        f.write(t.replace('\n', eol))
    os.replace(ruta + '.tmp', ruta)
    print(mensaje)


if __name__ == '__main__':
    main()
