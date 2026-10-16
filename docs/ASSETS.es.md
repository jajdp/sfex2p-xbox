# Los mosaicos del paquete

*(English: [ASSETS.md](ASSETS.md))*

Un paquete UWP necesita once imágenes. **Este repositorio no trae ninguna**: las del port real
están recortadas del propio material artístico del juego, que es de Capcom, y eso es exactamente lo
que [`NOTICE.es.md`](../NOTICE.es.md) promete no distribuir. Las pones tú.

`tools/empaquetar-uwp.ps1` lee los nombres directamente de `package/Package.appxmanifest` y se
detiene antes de empaquetar si falta alguna, diciendo cuáles no encontró.

## Qué poner en `package/Assets/`

| Archivo | Medida |
|---|---|
| `SplashScreen.png` | 620 × 300 |
| `SplashScreen.scale-200.png` | 1240 × 600 |
| `Square150x150Logo.png` | 150 × 150 |
| `Square150x150Logo.scale-200.png` | 300 × 300 |
| `Square44x44Logo.png` | 44 × 44 |
| `Square44x44Logo.scale-200.png` | 88 × 88 |
| `Square44x44Logo.targetsize-24_altform-unplated.png` | 24 × 24 |
| `StoreLogo.png` | 50 × 50 |
| `StoreLogo.scale-200.png` | 100 × 100 |
| `LockScreenLogo.png` | 24 × 24 |
| `LockScreenLogo.scale-200.png` | 48 × 48 |

PNG de 32 bits con alfa. Las medidas no son una recomendación: un mosaico del tamaño equivocado
hace que `makepri` produzca un índice de recursos que la consola no acepta.

## La forma más rápida de tener algo que funcione

Valen once imágenes lisas cualesquiera de esas medidas exactas: a la consola solo le hace falta que
existan y que tengan la forma correcta. Con ImageMagick, si lo tienes, salen las once de una vez.

Las once de una vez, con las medidas de la tabla:

> **Dónde se escribe:** en **PowerShell** —pulsa la tecla **Windows**, escribe `powershell` y
> pulsa **Enter**—, en una ventana **normal**: no hace falta «ejecutar como administrador»,
> desde la carpeta de este repositorio.

```powershell
$tiles = @{
  'SplashScreen.png'                                   = '620x300'
  'SplashScreen.scale-200.png'                         = '1240x600'
  'Square150x150Logo.png'                              = '150x150'
  'Square150x150Logo.scale-200.png'                    = '300x300'
  'Square44x44Logo.png'                                = '44x44'
  'Square44x44Logo.scale-200.png'                      = '88x88'
  'Square44x44Logo.targetsize-24_altform-unplated.png' = '24x24'
  'StoreLogo.png'                                      = '50x50'
  'StoreLogo.scale-200.png'                            = '100x100'
  'LockScreenLogo.png'                                 = '24x24'
  'LockScreenLogo.scale-200.png'                       = '48x48'
}
foreach ($t in $tiles.GetEnumerator()) {
  magick -size $t.Value xc:"#1b1b1f" (Join-Path 'package\Assets' $t.Key)
}
```

Cámbialas por arte de verdad cuando quieras: nada más de la compilación depende de ellas.

## Si llegas a hacer material artístico

Que sea tuyo. Las capturas, los logos, el arte de los personajes y las fuentes del juego son de sus
dueños, y un paquete que los lleve dentro es un paquete que no puedes compartir.
