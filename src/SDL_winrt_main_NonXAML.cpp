/*
    SDL_winrt_main_NonXAML.cpp, placed in the public domain by David Ludwig  3/13/14
*/

#include "SDL_main.h"
#include "SDL_hints.h"
#include <cstdio>
#include <cwchar>
#include <string>
#include <vector>
#include <windows.h>
#include <wrl.h>

/* At least one file in any SDL/WinRT app appears to require compilation
   with C++/CX, otherwise a Windows Metadata file won't get created, and
   an APPX0702 build error can appear shortly after linking.

   The following set of preprocessor code forces this file to be compiled
   as C++/CX, which appears to cause Visual C++ 2012's build tools to
   create this .winmd file, and will help allow builds of SDL/WinRT apps
   to proceed without error.

   If other files in an app's project enable C++/CX compilation, then it might
   be possible for SDL_winrt_main_NonXAML.cpp to be compiled without /ZW,
   for Visual C++'s build tools to create a winmd file, and for the app to
   build without APPX0702 errors.  In this case, if
   SDL_WINRT_METADATA_FILE_AVAILABLE is defined as a C/C++ macro, then
   the #error (to force C++/CX compilation) will be disabled.

   Please note that /ZW can be specified on a file-by-file basis.  To do this,
   right click on the file in Visual C++, click Properties, then change the
   setting through the dialog that comes up.
*/
#ifndef SDL_WINRT_METADATA_FILE_AVAILABLE
#ifndef __cplusplus_winrt
#error SDL_winrt_main_NonXAML.cpp must be compiled with /ZW, otherwise build errors due to missing .winmd files can occur.
#endif
#endif

/* Prevent MSVC++ from warning about threading models when defining our
   custom WinMain.  The threading model will instead be set via a direct
   call to Windows::Foundation::Initialize (rather than via an attributed
   function).

   To note, this warning (C4447) does not seem to come up unless this file
   is compiled with C++/CX enabled (via the /ZW compiler flag).
*/
#ifdef _MSC_VER
#pragma warning(disable : 4447)
#endif

/* Make sure the function to initialize the Windows Runtime gets linked in. */
#ifdef _MSC_VER
#pragma comment(lib, "runtimeobject.lib")
#endif

// --- Recompilaciones (2026-10-03): reanudar tras la terminación -------------------------------------
// En el modo desarrollador la consola termina el juego en segundo plano y, al volver de Home, lo relanza
// con PreviousExecutionState = Terminated (3). El runtime (main.cpp, «resume after termination») restaura
// entonces la máquina que guardó al ocultarse la ventana; con cualquier otro estado la descarta.
extern "C" int g_psx_prev_exec_state;

namespace {

int estado_previo()
{
    // La activación de este arranque; -1 si no se puede leer.
    try {
        auto a = Windows::ApplicationModel::AppInstance::GetActivatedEventArgs();
        if (a != nullptr) return static_cast<int>(a->PreviousExecutionState);
    } catch (Platform::Exception^) {
    }
    return -1;
}

int SDL_main_with_core_exit(int argc, char* argv[])
{
    // v2 (0.2.9.0): en la consola AppInstance da nulo; el estado lo anota SDL al recibir la activación
    // (SDL_WinRTApp::OnAppActivated, parche de SDL de este mismo script). Aquí solo se usa si AppInstance responde.
    {
        const int e = estado_previo();
        if (e >= 0) g_psx_prev_exec_state = e;
    }
    const int result = SDL_main(argc, argv);

    // Returning from SDL_main is not sufficient to dismiss the app reliably
    // on Xbox. Flush the LocalState log and explicitly end the UWP lifecycle.
    std::fflush(nullptr);
    Windows::ApplicationModel::Core::CoreApplication::Exit();
    return result;
}

// --- Recompilaciones (2026-10-02 / 2026-10-05) ------------------------------------------------------
// LA CARPETA DE DATOS. El runtime ancla todos sus archivos en el directorio del ejecutable, que aquí es la
// carpeta de instalación del paquete y es de SOLO LECTURA; el parche `parche_uwp_rutas.py` lo cambia por
// esta misma carpeta de LocalState (main.cpp, psx_uwp_data_root). Aquí se prepara antes de arrancar:
//   1. se crean sus subcarpetas (disc, bios, saves, logs);
//   2. se siembra lo que trae el paquete —game.toml, mods, la BIOS libre…—, porque el runtime ya no mira
//      la carpeta de instalación;
//   3. se escriben `bios.cfg` y `disc.cfg`, los dos punteros que el runtime lee para saber dónde están la
//      BIOS y el disco, con RUTAS ABSOLUTAS (una relativa se resolvería contra el directorio de trabajo,
//      que no es este);
//   4. se une el disco, que el Device Portal no deja subir entero.
// LocalState se saca del Temp del paquete («Packages\<PFN>\AC\Temp», dos niveles arriba): así no hace falta
// la Windows Runtime antes de SDL_WinRTRunApp.
// El disco entero (447 MB) da 500 al subirlo por el portal, que pasa por D:\DevelopmentFiles. Se sube partido
// en «<nombre>.parte1», «<nombre>.parte2»… dentro de disc\ y aquí se une una sola vez (las partes se quedan).
// Receta de la entrada UWP de Melee (Decompilaciones, 2026-10-01) y del port de SF EX Plus Alpha.

const wchar_t* const SERIE = L"SLUS-01105";   // el identificador del juego (game.toml [game] id)

std::wstring raiz_juego()
{
    wchar_t tmp[MAX_PATH] = {};
    const DWORD n = GetTempPathW(MAX_PATH, tmp);
    std::wstring t(tmp, n);
    if (!t.empty() && (t.back() == L'\\' || t.back() == L'/')) t.pop_back();
    for (int i = 0; i < 2; ++i) {
        const size_t p = t.find_last_of(L"\\/");
        if (p != std::wstring::npos) t.resize(p);
    }
    return t + L"\\LocalState\\PSXRecomp\\" + SERIE + L"\\";
}

std::wstring carpeta_instalacion()
{
    wchar_t buf[MAX_PATH * 4] = {};
    const DWORD n = GetModuleFileNameW(nullptr, buf, (DWORD)(sizeof buf / sizeof buf[0]));
    std::wstring p(buf, n);
    const size_t c = p.find_last_of(L"\\/");
    return (c == std::wstring::npos) ? std::wstring() : p.substr(0, c + 1);
}

void anota(const std::wstring& raiz, const char* texto)
{
    FILE* f = nullptr;
    if (_wfopen_s(&f, (raiz + L"logs\\arranque.txt").c_str(), L"ab") == 0 && f) {
        std::fputs(texto, f);
        std::fputs("\r\n", f);
        std::fclose(f);
    }
}

bool existe(const std::wstring& ruta)
{
    return GetFileAttributesW(ruta.c_str()) != INVALID_FILE_ATTRIBUTES;
}

void crea_carpeta(const std::wstring& ruta)
{
    CreateDirectoryW(ruta.c_str(), nullptr);
}

// Copia recursiva. `solo_si_falta` deja en paz lo que el jugador ya tenga.
void copia_arbol(const std::wstring& origen, const std::wstring& destino, bool solo_si_falta)
{
    crea_carpeta(destino);
    WIN32_FIND_DATAW d = {};
    HANDLE h = FindFirstFileExW((origen + L"*").c_str(), FindExInfoBasic, &d,
                                FindExSearchNameMatch, nullptr, 0);
    if (h == INVALID_HANDLE_VALUE) return;
    do {
        const std::wstring nombre(d.cFileName);
        if (nombre == L"." || nombre == L"..") continue;
        const std::wstring o = origen + nombre;
        const std::wstring t = destino + nombre;
        if (d.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
            copia_arbol(o + L"\\", t + L"\\", solo_si_falta);
        } else if (!solo_si_falta || !existe(t)) {
            CopyFileW(o.c_str(), t.c_str(), FALSE);
        }
    } while (FindNextFileW(h, &d));
    FindClose(h);
}

void escribe_linea(const std::wstring& ruta, const std::wstring& texto)
{
    FILE* f = nullptr;
    if (_wfopen_s(&f, ruta.c_str(), L"wb") != 0 || !f) return;
    // Los punteros se leen como texto estrecho: la ruta no lleva más que ASCII.
    const std::string t(texto.begin(), texto.end());
    std::fputs(t.c_str(), f);
    std::fputs("\r\n", f);
    std::fclose(f);
}

// El primer archivo que case con el patrón, o vacío.
std::wstring primero(const std::wstring& carpeta, const wchar_t* patron)
{
    WIN32_FIND_DATAW d = {};
    HANDLE h = FindFirstFileExW((carpeta + patron).c_str(), FindExInfoBasic, &d,
                                FindExSearchNameMatch, nullptr, 0);
    if (h == INVALID_HANDLE_VALUE) return L"";
    FindClose(h);
    return carpeta + d.cFileName;
}

void une_partes()
{
    const std::wstring raiz = raiz_juego();
    const std::wstring disco = raiz + L"disc\\";
    WIN32_FIND_DATAW d = {};
    HANDLE h = FindFirstFileExW((disco + L"*.parte1").c_str(), FindExInfoBasic, &d, FindExSearchNameMatch, nullptr, 0);
    if (h == INVALID_HANDLE_VALUE) return;
    FindClose(h);
    std::wstring base(d.cFileName);
    base.resize(base.size() - std::wcslen(L".parte1"));
    const std::wstring destino = disco + base;
    if (GetFileAttributesW(destino.c_str()) != INVALID_FILE_ATTRIBUTES) return;  // ya unido
    const std::wstring tmp = destino + L".uniendo";
    FILE* out = nullptr;
    if (_wfopen_s(&out, tmp.c_str(), L"wb") != 0 || !out) {
        anota(raiz, "partes: no se pudo crear el archivo unido");
        return;
    }
    std::vector<char> buf(8u << 20);
    unsigned long long total = 0;
    int partes = 0;
    for (int i = 1;; ++i) {
        FILE* in = nullptr;
        if (_wfopen_s(&in, (destino + L".parte" + std::to_wstring(i)).c_str(), L"rb") != 0 || !in) break;
        size_t leidos;
        while ((leidos = std::fread(buf.data(), 1, buf.size(), in)) > 0) {
            std::fwrite(buf.data(), 1, leidos, out);
            total += leidos;
        }
        std::fclose(in);
        ++partes;
    }
    std::fclose(out);
    char msg[200];
    if (MoveFileExW(tmp.c_str(), destino.c_str(), MOVEFILE_REPLACE_EXISTING))
        std::snprintf(msg, sizeof msg, "partes: %d unidas, %llu bytes", partes, total);
    else
        std::snprintf(msg, sizeof msg, "partes: no se pudo renombrar (error %lu)", GetLastError());
    anota(raiz, msg);
}

void prepara_datos()
{
    const std::wstring raiz = raiz_juego();
    const std::wstring inst = carpeta_instalacion();

    // 1. el esqueleto
    {
        std::wstring acumulado;
        const std::wstring r = raiz.substr(0, raiz.size() - 1);
        for (size_t i = 0; i < r.size(); ++i) {           // crea cada nivel: LocalState\PSXRecomp\<serie>
            acumulado += r[i];
            if (r[i] == L'\\' && i > 2) crea_carpeta(acumulado);
        }
        crea_carpeta(r);
    }
    for (const wchar_t* sub : { L"disc", L"bios", L"saves", L"logs" }) crea_carpeta(raiz + sub);

    if (inst.empty()) { anota(raiz, "datos: no se pudo leer la carpeta de instalación"); return; }

    // 2. lo que trae el paquete. Lo que es del producto se repone en cada arranque (así una versión nueva
    //    llega de verdad); lo que es del jugador —ajustes y mandos— solo si falta.
    for (const wchar_t* n : { L"game.toml", L"game_options.toml", L"psx_game_version.txt" })
        if (existe(inst + n)) CopyFileW((inst + n).c_str(), (raiz + n).c_str(), FALSE);
    for (const wchar_t* n : { L"settings.toml", L"input.ini", L"keybinds.ini" })
        if (existe(inst + n) && !existe(raiz + n)) CopyFileW((inst + n).c_str(), (raiz + n).c_str(), FALSE);
    if (existe(inst + L"mods")) copia_arbol(inst + L"mods\\", raiz + L"mods\\", false);
    if (existe(inst + L"bios")) copia_arbol(inst + L"bios\\", raiz + L"bios\\", true);

    // 3. los punteros a la BIOS y al disco, con ruta absoluta. La BIOS del jugador (SCPH-1001) se sube a
    //    bios\; el disco, a disc\. Si no están todavía, no se escribe nada y el runtime avisará.
    const std::wstring bios = primero(raiz + L"bios\\", L"SCPH*.BIN");
    if (!bios.empty()) escribe_linea(raiz + L"bios.cfg", bios);
    std::wstring cue = primero(raiz + L"disc\\", L"*.cue");
    if (cue.empty()) cue = primero(raiz + L"disc\\", L"*.bin");
    if (!cue.empty()) escribe_linea(raiz + L"disc.cfg", cue);

    char msg[400];
    std::snprintf(msg, sizeof msg, "datos: raiz lista; bios=%s disco=%s",
                  bios.empty() ? "(falta)" : "ok", cue.empty() ? "(falta)" : "ok");
    anota(raiz, msg);
}

// El runtime cuenta lo que hace por la salida estándar, que en la consola no va a ninguna parte: se
// redirige a logs\ para poder leerla con el Device Portal. Sin búfer, porque si la aplicación se cierra
// de golpe lo pendiente se perdería, que es justo lo que hay que diagnosticar.
void redirige_salida()
{
    const std::wstring raiz = raiz_juego();
    FILE* f = nullptr;
    if (_wfreopen_s(&f, (raiz + L"logs\\salida.txt").c_str(), L"w", stdout) == 0 && f)
        setvbuf(stdout, nullptr, _IONBF, 0);
    f = nullptr;
    if (_wfreopen_s(&f, (raiz + L"logs\\errores.txt").c_str(), L"w", stderr) == 0 && f)
        setvbuf(stderr, nullptr, _IONBF, 0);
}

} // namespace

int CALLBACK WinMain(HINSTANCE, HINSTANCE, LPSTR, int)
{
    prepara_datos();
    redirige_salida();
    une_partes();
    prepara_datos();   // tras unir el disco, el puntero ya puede apuntar al archivo unido
    // En la Xbox, B es también el «atrás» del sistema: si nadie lo atiende, cierra la app. Con esta
    // pista SDL lo atiende y la pulsación sigue llegando al juego (receta de Melee, 2026-10-01).
    SDL_SetHint(SDL_HINT_WINRT_HANDLE_BACK_BUTTON, "1");
    return SDL_WinRTRunApp(SDL_main_with_core_exit, NULL);
}

/* Recompilaciones (2026-10-04): la entrada que exige vccorlib al compilar con /ZW. Con el generador de Visual
 * Studio la ponía el propio proyecto; con Ninja hay que escribirla. SDL_main.h renombra «main», así que primero
 * se deshace ese renombrado. */
#ifdef main
#undef main
#endif
[Platform::MTAThread]
int main(Platform::Array<Platform::String ^> ^)
{
    return WinMain(nullptr, nullptr, nullptr, 0);
}
