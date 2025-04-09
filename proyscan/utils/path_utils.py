# proyscan/utils/path_utils.py
import os
import sys
import re
import logging # Importar
from typing import Optional, Set, Tuple
from urllib.parse import urlparse

from ..config import MAPA_LENGUAJES, LENGUAJE_DEFECTO

# Obtener logger
logger = logging.getLogger(__name__) # Usa 'proyscan.utils.path_utils'

# --- Funciones existentes ---
def obtener_lenguaje_extension(ruta_archivo: str) -> str:
    # ... (sin cambios internos, no necesita logging) ...
    _, extension = os.path.splitext(ruta_archivo)
    if not extension: return LENGUAJE_DEFECTO
    ext = extension.lower()
    return MAPA_LENGUAJES.get(ext, LENGUAJE_DEFECTO)

def normalizar_ruta(ruta: str) -> str:
     # ... (sin cambios internos, no necesita logging) ...
    ruta_limpia = os.path.normpath(ruta).replace(os.sep, '/')
    if ruta.startswith("./") and not ruta_limpia.startswith("./") and not ruta_limpia.startswith("../"):
         if ruta_limpia != '.': ruta_limpia = "./" + ruta_limpia
    if ruta in ('', '.') and ruta_limpia == '.': return ruta
    if ruta.endswith('/') and not ruta_limpia.endswith('/') and len(ruta_limpia) > 1: ruta_limpia += '/'
    return ruta_limpia

def _intentar_ruta_modulo(ruta_base_rel: str, archivos_proyecto: Set[str]) -> Optional[str]:
    # ... (sin cambios internos, pero podemos añadir debug si falla) ...
    ruta_py = f"{ruta_base_rel}.py"
    if ruta_py in archivos_proyecto: return ruta_py
    ruta_init = normalizar_ruta(f"{ruta_base_rel}/__init__.py")
    if ruta_init in archivos_proyecto: return ruta_init
    logger.debug(f"_intentar_ruta_modulo no encontró ni '{ruta_py}' ni '{ruta_init}'") # DEBUG
    return None

def resolver_import_python(modulo_importado: str, nivel_relativo: int, ruta_archivo_actual_rel: str, archivos_proyecto: Set[str]) -> Optional[str]:
    logger.debug(f"Resolviendo Import Python: Mod='{modulo_importado}', Nivel={nivel_relativo}, Origen='{ruta_archivo_actual_rel}'") # DEBUG
    if nivel_relativo > 0:
        # ... (lógica de resolución relativa sin cambios) ...
        directorio_actual = os.path.dirname(ruta_archivo_actual_rel) if os.path.dirname(ruta_archivo_actual_rel) else '.'
        niveles_subir = nivel_relativo - 1
        directorio_base_rel = directorio_actual
        for _ in range(niveles_subir):
            directorio_base_rel = os.path.dirname(directorio_base_rel)
            if not directorio_base_rel or directorio_base_rel == '.':
                 directorio_base_rel = ''
                 break
            if directorio_base_rel == '.': directorio_base_rel = ''
        partes_modulo = modulo_importado.split('.') if modulo_importado else []
        ruta_tentativa_base = os.path.join(directorio_base_rel, *partes_modulo) if directorio_base_rel else os.path.join(*partes_modulo)
        ruta_base_norm = normalizar_ruta(ruta_tentativa_base)
        ruta_encontrada = _intentar_ruta_modulo(ruta_base_norm, archivos_proyecto)
        logger.debug(f"  Resultado relativo: Base='{ruta_base_norm}', Encontrado='{ruta_encontrada}'") # DEBUG
        return ruta_encontrada
    else:
        # ... (lógica de resolución absoluta sin cambios) ...
        partes_modulo = modulo_importado.split('.')
        ruta_tentativa_base = os.path.join(*partes_modulo)
        ruta_base_norm = normalizar_ruta(ruta_tentativa_base)
        ruta_encontrada = _intentar_ruta_modulo(ruta_base_norm, archivos_proyecto)
        logger.debug(f"  Resultado absoluto: Base='{ruta_base_norm}', Encontrado='{ruta_encontrada}'") # DEBUG
        return ruta_encontrada

def es_stdlib(nombre_modulo: str) -> bool:
    primer_componente = nombre_modulo.split('.')[0]
    # logger.debug(f"Comprobando stdlib para: '{primer_componente}' -> {primer_componente in STDLIBS_COMUNES}") # DEBUG (muy verboso)
    return primer_componente in STDLIBS_COMUNES

def resolver_ruta_referencia(ruta_referencia: str, ruta_archivo_origen_rel: str) -> Tuple[str, Optional[str]]:
    ref = ruta_referencia.strip()
    logger.debug(f"Resolviendo Referencia Web/Genérica: Ref='{ref}', Origen='{ruta_archivo_origen_rel}'") # DEBUG
    if not ref: return 'desconocida', None
    # ... (lógica de urlparse sin cambios) ...
    try:
        parsed_url = urlparse(ref)
        if parsed_url.scheme in ('http', 'https', 'ftp', 'ftps', 'data'):
            logger.debug("  -> Tipo: url") # DEBUG
            return 'url', ref
    except ValueError: pass
    # ... (lógica de externa sin cambios) ...
    if not any(c in ref for c in './\\'):
         logger.debug("  -> Tipo: externa (sin separadores)") # DEBUG
         return 'externa', ref
    # ... (lógica de resolución relativa/absoluta sin cambios) ...
    ruta_resuelta_abs: Optional[str] = None
    tipo_ruta = 'desconocida'
    dir_origen = os.path.dirname(ruta_archivo_origen_rel)
    if not dir_origen and ruta_archivo_origen_rel: dir_origen = '.'
    elif not dir_origen and not ruta_archivo_origen_rel: dir_origen = '.'

    if ref.startswith('/'):
        tipo_ruta = 'absoluta'
        ruta_resuelta_abs = normalizar_ruta(ref[1:])
    elif ref.startswith('.'):
        tipo_ruta = 'relativa'
        ruta_combinada = os.path.join(dir_origen, ref)
        ruta_resuelta_abs = normalizar_ruta(ruta_combinada)
    else:
        tipo_ruta = 'relativa'
        ruta_combinada = os.path.join(dir_origen, ref)
        ruta_resuelta_abs = normalizar_ruta(ruta_combinada)

    if ruta_resuelta_abs:
        ruta_resuelta_abs = ruta_resuelta_abs.split('?')[0].split('#')[0]

    logger.debug(f"  -> Tipo: {tipo_ruta}, Ruta Resuelta (pre-check): '{ruta_resuelta_abs}'") # DEBUG
    return tipo_ruta, ruta_resuelta_abs