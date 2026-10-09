# -*- coding: utf-8 -*-
# La carpeta de datos del juego en la consola.
#
# Este framework ancla TODOS sus archivos —game.toml, el disco, la BIOS, settings.toml, las tarjetas de memoria,
# las cachés y los registros— en el directorio del EJECUTABLE, y lo dice por escrito: «Deliberately NEVER the
# current working directory» (`exe_dir_from_argv`, main.cpp). En UWP ese directorio es la carpeta de instalación
# del paquete, que es de SOLO LECTURA: el juego no encontraría el disco (que se sube aparte) y no podría escribir
# ni una línea de registro.
#
# El parche hace que, compilando para la consola, esa función devuelva la carpeta de datos de la aplicación:
#     …\Packages\<identidad>\LocalState\PSXRecomp\SLUS-01105\
# que es donde el Device Portal deja la BIOS, el disco y la configuración, y es escribible. LocalState se saca del
# Temp del paquete («…\AC\Temp», dos niveles arriba), el mismo truco de la entrada UWP: así no hace falta inicializar
# la Windows Runtime antes que SDL. La subcarpeta se puede cambiar con -DPSX_UWP_DATA_DIR al configurar.
#
# Idempotente y todo o nada; escritura atómica.
# Uso: parche_uwp_rutas.py <raíz del proyecto del juego>
import os
import sys

if len(sys.argv) < 2:
    sys.exit('uso: %s <ruta de la raiz del proyecto del juego>' % os.path.basename(sys.argv[0]))
RAIZ = sys.argv[1]
MARCA = 'Recompilaciones (2026-10-05): la carpeta de datos de la consola'

VIEJO = '''static std::filesystem::path exe_dir_from_argv(const char* argv0) {
    namespace fs = std::filesystem;
    std::error_code ec;
    fs::path exe_dir;
#ifdef _WIN32'''

NUEVO = '''#if defined(PSX_UWP)
/* ''' + MARCA + '''.
 * En la consola el directorio del ejecutable es la carpeta de instalación del paquete, de solo lectura, así que
 * el ancla pasa a ser la carpeta de datos de la aplicación (LocalState), que es donde se suben el disco y la
 * BIOS y donde se puede escribir. Se saca del Temp del paquete («…\\AC\\Temp» → dos niveles arriba), igual que
 * en la entrada UWP, para no depender de la Windows Runtime. */
#ifndef PSX_UWP_DATA_DIR
#define PSX_UWP_DATA_DIR L"PSXRecomp\\\\SLUS-01105"
#endif
static std::filesystem::path psx_uwp_data_root() {
    namespace fs = std::filesystem;
    static const fs::path raiz = []() -> fs::path {
        wchar_t tmp[MAX_PATH] = {};
        const DWORD n = GetTempPathW(MAX_PATH, tmp);
        if (n == 0 || n >= MAX_PATH) return fs::path(".");
        std::wstring t(tmp, n);
        while (!t.empty() && (t.back() == L'\\\\' || t.back() == L'/')) t.pop_back();
        for (int i = 0; i < 2; ++i) {
            const size_t p = t.find_last_of(L"\\\\/");
            if (p == std::wstring::npos) return fs::path(".");
            t.resize(p);
        }
        fs::path r = fs::path(t) / L"LocalState" / PSX_UWP_DATA_DIR;
        std::error_code ec;
        fs::create_directories(r, ec);
        return r;
    }();
    return raiz;
}
#endif  /* PSX_UWP */

static std::filesystem::path exe_dir_from_argv(const char* argv0) {
    namespace fs = std::filesystem;
    std::error_code ec;
    fs::path exe_dir;
#if defined(PSX_UWP)
    (void)argv0;
    (void)ec;
    return psx_uwp_data_root();
#endif
#ifdef _WIN32'''


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
    print('main.cpp: el ancla del runtime pasa a LocalState en la consola')


if __name__ == '__main__':
    main()
