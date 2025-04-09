# proyscan/utils/path_utils.py
import os
import sys
import re # Importar regex
from typing import Optional, Set, Tuple
from urllib.parse import urlparse # Para detectar URLs

# Importaciones existentes
from ..config import MAPA_LENGUAJES, LENGUAJE_DEFECTO

# --- Funciones existentes (obtener_lenguaje_extension, normalizar_ruta, _intentar_ruta_modulo, resolver_import_python, es_stdlib, STDLIBS_COMUNES) ---
# ... (mantener el código de la Fase 1 para estas funciones) ...
def obtener_lenguaje_extension(ruta_archivo: str) -> str:
    """Determina el lenguaje/tipo basado en la extensión del archivo."""
    _, extension = os.path.splitext(ruta_archivo)
    if not extension:
        return LENGUAJE_DEFECTO
    ext = extension.lower()
    return MAPA_LENGUAJES.get(ext, LENGUAJE_DEFECTO)

def normalizar_ruta(ruta: str) -> str:
    """Normaliza una ruta usando '/' y eliminando redundancias."""
    # normpath simplifica, no valida existencia.
    # Usamos replace para asegurar separadores '/' consistentes
    ruta_limpia = os.path.normpath(ruta).replace(os.sep, '/')
    # normpath en Windows puede quitar el './' inicial, lo reponemos si es necesario
    if ruta.startswith("./") and not ruta_limpia.startswith("./") and not ruta_limpia.startswith("../"):
         if ruta_limpia != '.':
              ruta_limpia = "./" + ruta_limpia

    # normpath puede convertir '' o '.' a '.', lo evitamos si no es el input original
    if ruta in ('', '.') and ruta_limpia == '.':
        return ruta
    # Si la ruta original terminaba en '/', preservarla si no es solo '/'
    if ruta.endswith('/') and not ruta_limpia.endswith('/') and len(ruta_limpia) > 1:
        ruta_limpia += '/'

    return ruta_limpia

def _intentar_ruta_modulo(ruta_base_rel: str, archivos_proyecto: Set[str]) -> Optional[str]:
    """Intenta encontrar .py o __init__.py (sin cambios)"""
    ruta_py = f"{ruta_base_rel}.py"
    if ruta_py in archivos_proyecto: return ruta_py
    ruta_init = normalizar_ruta(f"{ruta_base_rel}/__init__.py")
    if ruta_init in archivos_proyecto: return ruta_init
    return None

def resolver_import_python(modulo_importado: str, nivel_relativo: int, ruta_archivo_actual_rel: str, archivos_proyecto: Set[str]) -> Optional[str]:
    """Resuelve import Python (sin cambios)"""
    if nivel_relativo > 0:
        directorio_actual = os.path.dirname(ruta_archivo_actual_rel) if os.path.dirname(ruta_archivo_actual_rel) else '.'
        niveles_subir = nivel_relativo - 1
        directorio_base_rel = directorio_actual
        for _ in range(niveles_subir):
            directorio_base_rel = os.path.dirname(directorio_base_rel)
            if not directorio_base_rel or directorio_base_rel == '.':
                 # Si subimos demasiado, os.dirname puede devolver '' o '.', ajustamos a raíz o None
                 directorio_base_rel = '' # Asumimos raíz relativa
                 break # Salir si subimos más allá de la raíz aparente
            # Manejar caso donde dirname devuelve '.' en lugar de '' para la raíz
            if directorio_base_rel == '.': directorio_base_rel = ''


        partes_modulo = modulo_importado.split('.') if modulo_importado else []
        # Usamos os.path.join pero empezamos desde la base relativa calculada
        ruta_tentativa_base = os.path.join(directorio_base_rel, *partes_modulo) if directorio_base_rel else os.path.join(*partes_modulo)
        ruta_base_norm = normalizar_ruta(ruta_tentativa_base)
        return _intentar_ruta_modulo(ruta_base_norm, archivos_proyecto)
    else:
        partes_modulo = modulo_importado.split('.')
        ruta_tentativa_base = os.path.join(*partes_modulo)
        ruta_base_norm = normalizar_ruta(ruta_tentativa_base)
        return _intentar_ruta_modulo(ruta_base_norm, archivos_proyecto)

STDLIBS_COMUNES = {
    'os', 'sys', 'json', 're', 'math', 'datetime', 'time', 'collections',
    'itertools', 'functools', 'pathlib', 'shutil', 'subprocess', 'argparse',
    'logging', 'io', 'typing', 'abc', 'enum', 'random', 'pickle', 'copy',
    'hashlib', 'base64', 'codecs', 'ast'
}
def es_stdlib(nombre_modulo: str) -> bool:
    """Comprueba si es stdlib (sin cambios)"""
    primer_componente = nombre_modulo.split('.')[0]
    return primer_componente in STDLIBS_COMUNES


# --- Nueva Función Genérica para Resolver Referencias Web/Generales ---

def resolver_ruta_referencia(
    ruta_referencia: str,       # La cadena encontrada (ej: '../style.css', '/img/logo.png', 'https://a.com/b.js')
    ruta_archivo_origen_rel: str, # Ruta relativa del archivo donde se encontró la referencia
    # dir_proyecto_raiz: str,   # No estrictamente necesario si trabajamos con relativas
    # archivos_proyecto: Set[str] # La comprobación de existencia se hace fuera
) -> Tuple[str, Optional[str]]:
    """
    Intenta resolver una ruta de referencia encontrada en web/otros archivos.

    Devuelve:
        - tipo: 'url', 'absoluta' (desde raíz proyecto), 'relativa', 'externa' (no-path), 'desconocida'
        - ruta_resuelta_o_original: Ruta normalizada relativa al proyecto si es interna/absoluta,
                                     o la cadena original si es URL/externa, o None si error.
    """
    ref = ruta_referencia.strip()
    if not ref:
        return 'desconocida', None

    # 1. Comprobar si es una URL completa
    try:
        parsed_url = urlparse(ref)
        if parsed_url.scheme in ('http', 'https', 'ftp', 'ftps', 'data'): # Añadir 'data' para data URIs
            return 'url', ref # Devolver URL original
    except ValueError:
        pass # No es una URL parseable

    # 2. Comprobar si parece un nombre de paquete/externo (sin '/', '\', '.')
    #    Esto es heurístico y aplica más a JS/PHP imports/requires.
    if not any(c in ref for c in './\\'):
         # Podría ser un módulo interno en la raíz, pero más probablemente externo
         # Devolvemos 'externa' y el path original para clasificación posterior
         return 'externa', ref

    # 3. Intentar resolver como ruta de archivo (relativa o absoluta desde raíz)
    ruta_resuelta_abs: Optional[str] = None
    tipo_ruta = 'desconocida'

    # Obtener directorio del archivo origen
    dir_origen = os.path.dirname(ruta_archivo_origen_rel)
    # Asegurarse de que dir_origen no sea vacío si el origen está en la raíz
    if not dir_origen and ruta_archivo_origen_rel:
        dir_origen = '.'
    elif not dir_origen and not ruta_archivo_origen_rel:
         # Caso raro: origen es '' (raíz virtual) - no debería pasar con relpath
         dir_origen = '.'


    if ref.startswith('/'):
        # Ruta absoluta desde la raíz del proyecto
        tipo_ruta = 'absoluta'
        # Quitamos el '/' inicial para que join funcione correctamente desde la "raíz"
        ruta_resuelta_abs = normalizar_ruta(ref[1:])
    elif ref.startswith('.'):
        # Ruta relativa
        tipo_ruta = 'relativa'
        ruta_combinada = os.path.join(dir_origen, ref)
        ruta_resuelta_abs = normalizar_ruta(ruta_combinada)
    else:
        # Ruta relativa implícita (desde el directorio actual)
        tipo_ruta = 'relativa'
        ruta_combinada = os.path.join(dir_origen, ref)
        ruta_resuelta_abs = normalizar_ruta(ruta_combinada)

    # Eliminar posibles query strings o hashes de las rutas de archivo
    if ruta_resuelta_abs:
        ruta_resuelta_abs = ruta_resuelta_abs.split('?')[0].split('#')[0]

    # print(f"[DEBUG Resolver Web] Ref: '{ref}', Origen: '{ruta_archivo_origen_rel}', DirO: '{dir_origen}', Tipo: {tipo_ruta}, Resuelta: '{ruta_resuelta_abs}'")

    # Devolvemos el tipo detectado y la ruta normalizada (aún no sabemos si existe)
    return tipo_ruta, ruta_resuelta_abs