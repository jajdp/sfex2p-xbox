# -*- coding: utf-8 -*-
"""Lo que comparten los parches del perfil UWP: leer, comprobar, sustituir y escribir.

Cada `parche_*.py` de esta carpeta hace lo mismo con anclas distintas, así que la mecánica vive
aquí una sola vez:

    import parchear

    MARCA = 'sfex2p-xbox: ...'
    CAMBIOS = [(ancla, reemplazo), ...]

    def main():
        raiz = parchear.raiz()
        parchear.informe(parchear.aplicar(parchear.runtime(raiz, 'src', 'main.cpp'),
                                          CAMBIOS, MARCA, 'main.cpp: ...'))

Las tres reglas que cumple todo parche de este repositorio, y que son el motivo de que `apply_uwp.py`
pueda detenerse a medias sin dejar un árbol inservible:

- **Todo o nada.** Cada ancla tiene que aparecer exactamente una vez; si una sola no cuadra, no se
  escribe nada en ese archivo y el script muere con el recuento.
- **Idempotente.** La marca queda escrita dentro del archivo, así que pasarlo dos veces no cambia
  nada y lo dice.
- **Escritura atómica y sin tocar el formato.** Se escribe un `.tmp` al lado y se reemplaza de una
  vez, conservando los finales de línea y el BOM que el archivo ya tenía.

Los comentarios que los parches escriben DENTRO del árbol del juego van en inglés, como el resto
del runtime, y en ASCII: MSVC lee un archivo sin BOM con la página de códigos del sistema, y un
acento puede absorber el carácter siguiente. Los comentarios de los scripts van en español.
"""
import os
import sys

__all__ = ['raiz', 'runtime', 'leer', 'escribir', 'aplicar', 'informe']


def raiz(ayuda='<ruta de la raiz del proyecto del juego>'):
    """La raíz del proyecto del juego, tomada del primer argumento que no sea una opción."""
    libres = [a for a in sys.argv[1:] if not a.startswith('-')]
    if not libres:
        sys.exit('uso: %s %s' % (os.path.basename(sys.argv[0]), ayuda))
    return libres[0]


def runtime(raiz_juego, *partes):
    """Una ruta dentro del framework: runtime('…', 'src', 'main.cpp')."""
    return os.path.join(raiz_juego, 'psxrecomp', 'runtime', *partes)


def leer(ruta, codificacion='utf-8'):
    """Devuelve (texto con '\\n', final de línea original). Con 'utf-8-sig' conserva el BOM."""
    with open(ruta, 'rb') as f:
        crudo = f.read().decode(codificacion)
    return crudo.replace('\r\n', '\n'), ('\r\n' if '\r\n' in crudo else '\n')


def escribir(ruta, texto, eol, codificacion='utf-8'):
    """Escribe de una vez: un .tmp al lado y un reemplazo atómico."""
    tmp = ruta + '.tmp'
    with open(tmp, 'w', encoding=codificacion, newline='') as f:
        f.write(texto.replace('\n', eol))
    os.replace(tmp, ruta)


def aplicar(ruta, cambios, marca, hecho=None, codificacion='utf-8'):
    """Aplica los cambios a un archivo. Devuelve el texto de lo hecho, o None si la marca ya estaba.

    `cambios` es una lista de pares (ancla, reemplazo). Cada ancla tiene que aparecer exactamente
    una vez: si no, muere sin escribir nada. `hecho` es lo que se informa al terminar; por defecto,
    el nombre del archivo.
    """
    nombre = os.path.basename(ruta)
    texto, eol = leer(ruta, codificacion)
    if marca in texto:
        return None
    for ancla, reemplazo in cambios:
        veces = texto.count(ancla)
        if veces != 1:
            sys.exit('%s: %d apariciones del ancla %r (el árbol no es el que este parche espera)'
                     % (nombre, veces, ancla[:60]))
        texto = texto.replace(ancla, reemplazo)
    escribir(ruta, texto, eol, codificacion)
    return hecho or nombre


def informe(*hechos, nada='el parche ya estaba'):
    """Imprime lo que se hizo, o que ya estaba puesto. Cada `hecho` puede ser None."""
    puestos = [h for h in hechos if h]
    print('; '.join(puestos) if puestos else nada)
