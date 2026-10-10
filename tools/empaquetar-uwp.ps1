<#
  Arma el paquete UWP (.msix) del juego para la Xbox en modo desarrollador, con el ejecutable que deja
  configurar-uwp.ps1, la definición de package\ de este repositorio (identidad y mosaicos), los archivos
  de configuración que siembran LocalState en el primer arranque y los paquetes de mods del árbol.

  Rehace resources.pri con makepri —sin el bloque <packaging> de la configuración por defecto, que parte
  el PRI por escala—, empaqueta con makeappx y firma con TU certificado.

  El disco y la BIOS NO van dentro: se suben al LocalState de la consola (docs\INSTALL.es.md).

  Uso (pwsh 7):
    pwsh -File empaquetar-uwp.ps1 -Build <compilación> -Juego <árbol> -Salida <carpeta> `
         -Certificado <huella SHA-1 del certificado en Cert:\CurrentUser\My> [-Version 1.0.0.0] `
         [-Mod <carpeta de un paquete de mods>] [-VCLibs <Microsoft.VCLibs.x64.14.00.appx>] `
         [-Conservar]

  -Version cambia la version solo en la copia que va al paquete; el manifiesto de package\ es
  del repositorio y no se modifica. -Conservar deja en %TEMP% la carpeta de trabajo, que por
  defecto se borra porque lleva dentro el ejecutable del juego.

  -Certificado es la huella (thumbprint) de TU certificado de firma, el mismo cuyo CN tiene que coincidir
  con el Publisher del manifiesto. Cómo crear uno autofirmado: docs\INSTALL.es.md §3.
#>
param(
    [Parameter(Mandatory)][string]$Build,
    [Parameter(Mandatory)][string]$Juego,
    [Parameter(Mandatory)][string]$Salida,
    [Parameter(Mandatory)][string]$Certificado,
    [string]$Version = '',
    [string]$Ejecutable = 'Street_Fighter_EX2_Plus.exe',
    [string[]]$Mod = @(),
    [string]$VCLibs = '',
    [string]$Sdk = '',
    [switch]$Conservar
)
$ErrorActionPreference = 'Stop'

$repo = Split-Path $PSScriptRoot                                   # la raíz de este repositorio
$def = Join-Path $repo 'package'                                   # manifiesto y mosaicos

# El SDK de Windows: la versión más nueva que haya, salvo que se pase -Sdk.
if (-not $Sdk) {
    $bin = Join-Path ${env:ProgramFiles(x86)} 'Windows Kits\10\bin'
    if (Test-Path -LiteralPath $bin) {
        $Sdk = Get-ChildItem -LiteralPath $bin -Directory -Filter '10.*' |
               Sort-Object Name -Descending |
               ForEach-Object { Join-Path $_.FullName 'x64' } |
               Where-Object { Test-Path (Join-Path $_ 'makeappx.exe') } |
               Select-Object -First 1
    }
}
if (-not $Sdk -or -not (Test-Path -LiteralPath (Join-Path $Sdk 'makeappx.exe'))) {
    throw 'no encuentro el SDK de Windows 10/11 (makeappx, makepri, signtool): pasa -Sdk con la carpeta x64 de su bin'
}

$exe = Join-Path $Build $Ejecutable
if (-not (Test-Path -LiteralPath $exe)) { throw "falta el ejecutable de la consola: $exe (configurar-uwp.ps1 -Compilar)" }

# El arte no viaja en este repositorio: lo pone quien empaqueta (docs\ASSETS.md).
$manRuta = Join-Path $def 'Package.appxmanifest'
$man = [IO.File]::ReadAllText($manRuta)
$exigidos = [regex]::Matches($man, 'Assets[\\/]([A-Za-z0-9._\-]+\.png)') |
            ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique
$faltan = $exigidos | Where-Object { -not (Test-Path -LiteralPath (Join-Path $def "Assets\$_")) }
if ($faltan) {
    throw ("faltan mosaicos en package\Assets\: {0}. Este repositorio no distribuye arte del juego; " +
           "pon los tuyos con las medidas de docs\ASSETS.md" -f ($faltan -join ', '))
}

# -Version solo cambia la copia que va al paquete: el manifiesto de package\ es del repositorio y
# no se toca, para que empaquetar no deje el arbol modificado ni herede la version a quien lo use
# despues. La copia se escribe mas abajo, como AppxManifest.xml, desde esta variable.
if ($Version) {
    $man = [regex]::Replace($man, '(<Identity[^>]*\bVersion=")[0-9.]+(")', "`${1}$Version`${2}")
}
if ($man -notmatch '<Identity Name="([^"]+)"[\s\S]*?Version="([0-9.]+)"') { throw 'no encuentro la identidad en el manifiesto' }
$familia, $version = $Matches[1], $Matches[2]

# Aviso temprano: si el CN del certificado no es el Publisher del manifiesto, signtool falla al final.
if ($man -match 'Publisher="([^"]+)"') {
    $publisher = $Matches[1]
    $cert = Get-ChildItem -LiteralPath "Cert:\CurrentUser\My\$Certificado" -ErrorAction SilentlyContinue
    if (-not $cert) { throw "no encuentro el certificado $Certificado en Cert:\CurrentUser\My" }
    if ($cert.Subject -ne $publisher) {
        throw ("el Publisher del manifiesto ($publisher) no es el del certificado ($($cert.Subject)): " +
               'la consola rechaza el paquete. Pon tu CN en package\Package.appxmanifest')
    }
}

# 1. el contenido del paquete
$trabajo = Join-Path $env:TEMP ('uwp-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
$cont = Join-Path $trabajo 'contenido'
New-Item -ItemType Directory -Force (Join-Path $cont 'Assets') | Out-Null
Copy-Item -LiteralPath $exe -Destination $cont
# El manifiesto del paquete sale de $man, que es donde -Version ya aplico el cambio.
[IO.File]::WriteAllText((Join-Path $cont 'AppxManifest.xml'), $man)
Get-ChildItem -LiteralPath (Join-Path $def 'Assets') -File -Filter *.png | Copy-Item -Destination (Join-Path $cont 'Assets') -Force

# configuración inicial (el primer arranque la copia a LocalState)
foreach ($n in 'game.toml', 'settings.toml', 'input.ini', 'keybinds.ini') {
    $r = Join-Path $Juego $n
    if (Test-Path -LiteralPath $r) { Copy-Item -LiteralPath $r -Destination $cont }
}
# El disco: en la consola NO es el del game.toml (ahí está la ruta del PC de quien generó el proyecto). Lo
# señala disc.cfg, que escribe la entrada UWP con la ruta real del LocalState. Hay que quitar la clave: el
# runtime arranca igual sin ella, pero si se deja, es ESA ruta la que le pasa al sistema de mods, y entonces
# ningún paquete con huella de disco llega a aplicarse («package does not target this game/image»).
$gt = Join-Path $cont 'game.toml'
if (Test-Path -LiteralPath $gt) {
    $txt = [IO.File]::ReadAllText($gt)
    $txt = [regex]::Replace($txt, '(?m)^(\s*disc\s*=\s*".*"\s*)$',
        "# (Xbox) el disco lo señala disc.cfg, que escribe la entrada UWP con la ruta del LocalState:`r`n#`$1")
    [IO.File]::WriteAllText($gt, $txt)
}

# los mods: los del árbol del juego, más los que se pasen con -Mod
$modsDst = Join-Path $cont 'mods\packages'
New-Item -ItemType Directory -Force $modsDst | Out-Null
$modsOrigen = Join-Path $Juego 'mods\packages'
if (Test-Path -LiteralPath $modsOrigen) {
    Get-ChildItem -LiteralPath $modsOrigen -Directory | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $modsDst -Recurse -Force
    }
}
foreach ($m in $Mod) {
    if (-not (Test-Path -LiteralPath $m)) { throw "no encuentro el paquete de mods: $m" }
    Copy-Item -LiteralPath $m -Destination $modsDst -Recurse -Force
}
# la BIOS libre que trae el runtime (tu SCPH-1001 retail va al LocalState, no aqui)
$bios = Join-Path $Build 'bios'
if (Test-Path -LiteralPath $bios) { Copy-Item -LiteralPath $bios -Destination $cont -Recurse -Force }

# Las herramientas del SDK dicen en su salida POR QUE fallaron, asi que no se descarta: se guarda
# y se muestra con el error. Un `| Out-Null` aqui deja un «makepri fallo» sin una pista.
function Invoke-Sdk {
    param([string]$Exe, [string[]]$Argumentos, [string]$Que)
    $salida = & "$Sdk\$Exe" @Argumentos 2>&1
    if ($LASTEXITCODE) { throw ("$Que falló (código $LASTEXITCODE):`n" + ($salida -join "`n")) }
}

# 2. resources.pri con el nombre de esta identidad
$pri = Join-Path $trabajo 'priconfig.xml'
Invoke-Sdk 'makepri.exe' @('createconfig', '/cf', $pri, '/dq', 'en-US', '/o') 'makepri createconfig'
[xml]$cfg = Get-Content -LiteralPath $pri
foreach ($n in @($cfg.SelectNodes('//packaging'))) { [void]$n.ParentNode.RemoveChild($n) }
$cfg.Save($pri)
Invoke-Sdk 'makepri.exe' @('new', '/pr', $cont, '/cf', $pri, '/of', (Join-Path $cont 'resources.pri'), '/o') 'makepri new'

# 3. empaquetar y firmar
New-Item -ItemType Directory -Force (Join-Path $Salida 'Dependencies') | Out-Null
$msix = Join-Path $Salida "${familia}_${version}_x64.msix"
Invoke-Sdk 'makeappx.exe' @('pack', '/o', '/d', $cont, '/p', $msix) 'makeappx pack'
Invoke-Sdk 'signtool.exe' @('sign', '/fd', 'SHA256', '/sha1', $Certificado, '/s', 'My', $msix) 'signtool'
if ($VCLibs -and (Test-Path -LiteralPath $VCLibs)) {
    Copy-Item -LiteralPath $VCLibs -Destination (Join-Path $Salida 'Dependencies') -Force
}

'paquete: {0} ({1:N0} B, SHA-256 {2})' -f $msix, (Get-Item -LiteralPath $msix).Length, (Get-FileHash -LiteralPath $msix).Hash
'ejecutable: {0:N0} B, SHA-256 {1}' -f (Get-Item -LiteralPath $exe).Length, (Get-FileHash -LiteralPath $exe).Hash
'mods: ' + ((Get-ChildItem -LiteralPath $modsDst -Directory | ForEach-Object { $_.Name }) -join ', ')

# La carpeta de trabajo lleva dentro el ejecutable del juego y los mods: no se deja en %TEMP%
# salvo que se pida con -Conservar para inspeccionar lo que se empaqueto.
if ($Conservar) {
    "trabajo (conservado): $trabajo"
} else {
    [IO.Directory]::Delete($trabajo, $true)
}
