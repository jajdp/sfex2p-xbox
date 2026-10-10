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
import parchear

MARCA = 'Recompilaciones (2026-10-05): the console data folder'

VIEJO = '''static std::filesystem::path exe_dir_from_argv(const char* argv0) {
    namespace fs = std::filesystem;
    std::error_code ec;
    fs::path exe_dir;
#ifdef _WIN32'''

NUEVO = '''#if defined(PSX_UWP)
/* ''' + MARCA + '''.
 * On the console the executable's directory is the package's install folder, which is read-only, so the anchor
 * becomes the app's data folder (LocalState): that is where the disc and the BIOS are uploaded, and it is
 * writable. It is derived from the package's Temp directory ("...\\AC\\Temp", two levels up), the same way the
 * UWP entry point does it, so that the Windows Runtime does not have to be up yet. */
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
    parchear.informe(parchear.aplicar(
        parchear.runtime(parchear.raiz(), 'src', 'main.cpp'),
        [(VIEJO, NUEVO)], MARCA, 'main.cpp: el ancla del runtime pasa a LocalState en la consola'))


if __name__ == '__main__':
    main()
