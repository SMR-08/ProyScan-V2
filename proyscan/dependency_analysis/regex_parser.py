# proyscan/dependency_analysis/regex_parser.py
import re
import os
import logging # Importar
from typing import List, Set, Optional, Dict, Tuple

from ..utils.path_utils import resolver_ruta_referencia, normalizar_ruta
from ..models import DependencyInfo

# Obtener logger
logger = logging.getLogger(__name__) # Usa 'proyscan.dependency_analysis.regex_parser'

# --- PATTERNS sin cambios ---
PATTERNS = {
    'html': [ # Mantenemos HTML aquí como fallback si BeautifulSoup falla, aunque no debería usarse
        re.compile(r"""<(?:script|img|audio|video|iframe|source|embed)\s+[^>]*?src\s*=\s*["']([^"']+)["'][^>]*?>""", re.IGNORECASE | re.DOTALL),
        re.compile(r"""<link\s+[^>]*?href\s*=\s*["']([^"']+)["'][^>]*?rel\s*=\s*["']stylesheet["'][^>]*?>""", re.IGNORECASE | re.DOTALL),
        re.compile(r"""<a\s+[^>]*?href\s*=\s*["']([^"']+)["'][^>]*?>""", re.IGNORECASE | re.DOTALL),
        re.compile(r"""<form\s+[^>]*?action\s*=\s*["']([^"']+)["'][^>]*?>""", re.IGNORECASE | re.DOTALL),
        re.compile(r"""style\s*=\s*["'][^"']*?url\(["']?([^"')]+?)["']?\)[^"']*?["']""", re.IGNORECASE | re.DOTALL),
    ],
    'css': [ # Mantenemos CSS aquí como fallback si tinycss2 falla
        re.compile(r"""@import\s+(?:url\()?["']([^"'\)]+)["']\)?\s*;?""", re.IGNORECASE),
        re.compile(r"""url\(["']?([^"')]+?)["']?\)""", re.IGNORECASE),
    ],
    'javascript': [
        re.compile(r"""import(?:["'\s]*(?:[\w*{}\n\r\s,]+from\s*)?)(["'])([^"'\n\r]+?)\1\s*;?""", re.MULTILINE),
        re.compile(r"""require\s*\(\s*(["'])([^"'\n\r]+?)\1\s*\)\s*;?"""),
        re.compile(r"""importScripts\s*\(\s*(["'])([^"'\n\r]+?)\1\s*\)\s*;?"""),
        re.compile(r"""new\s+Worker\s*\(\s*(["'])([^"'\n\r]+?)\1\s*\)"""),
        re.compile(r"""fetch\s*\(\s*(["'])([^"'\n\r]+?)\1\s*(?:,|\))""", re.MULTILINE),
    ],
    'php': [
        re.compile(r"""(?:include|require|include_once|require_once)\s+(?:(?:__DIR__|\$[_a-zA-Z0-9]+)\s*\.\s*)?(["'])([^"']+\.php)\1\s*;""", re.IGNORECASE),
    ]
}


def analizar_regex(
    contenido_lineas: List[str],
    lenguaje: str,
    ruta_archivo_rel: str,
    archivos_proyecto: Set[str],
    dir_proyecto_raiz: str
) -> Optional[List[DependencyInfo]]:
    """
    Analiza dependencias usando Regex para lenguajes web comunes. (Con Logging)
    """
    logger.debug(f"--- Iniciando análisis Regex para {ruta_archivo_rel} (Lenguaje: {lenguaje}) ---") # DEBUG
    if lenguaje not in PATTERNS:
        logger.warning(f"Lenguaje '{lenguaje}' no soportado por el parser Regex.") # WARNING
        return None

    contenido_completo = "\n".join(contenido_lineas)
    if not contenido_completo.strip():
        logger.debug("Archivo vacío.") # DEBUG
        return []

    dependencias_encontradas_raw: Set[str] = set()

    for pattern in PATTERNS[lenguaje]:
        logger.debug(f"Aplicando patrón Regex: {pattern.pattern}") # DEBUG
        try:
            matches = pattern.findall(contenido_completo)
            if matches: logger.debug(f"  -> Coincidencias encontradas: {matches}") # DEBUG
            for match in matches:
                referencia = match[-1] if isinstance(match, tuple) and match else match
                if isinstance(referencia, str) and referencia.strip():
                     dependencias_encontradas_raw.add(referencia.strip())
        except Exception as e:
             logger.warning(f"Error aplicando Regex {pattern.pattern} en {ruta_archivo_rel}: {e}")


    # --- Resolución y Clasificación (con logging) ---
    dependencias_clasificadas: List[DependencyInfo] = []
    rutas_procesadas = set()
    logger.debug(f"Dependencias crudas encontradas: {dependencias_encontradas_raw}") # DEBUG

    for ref in dependencias_encontradas_raw:
        if ref == '#' or ref.startswith(('javascript:', 'mailto:', 'tel:', 'data:')):
            logger.debug(f"Omitiendo referencia no procesable: '{ref}'") # DEBUG
            continue

        logger.debug(f"Resolviendo referencia cruda: '{ref}'") # DEBUG
        tipo_ref, ruta_resuelta_o_original = resolver_ruta_referencia(ref, ruta_archivo_rel)
        logger.debug(f"  -> Tipo Ref: '{tipo_ref}', Ruta/Original: '{ruta_resuelta_o_original}'") # DEBUG
        # ... (resto de lógica de clasificación igual, con logging añadido) ...
        dep_info: Optional[DependencyInfo] = None
        key_to_check = ruta_resuelta_o_original
        if not ruta_resuelta_o_original: continue
        if tipo_ref == 'url': dep_info = DependencyInfo(tipo='url', path=ruta_resuelta_o_original)
        elif tipo_ref == 'externa': dep_info = DependencyInfo(tipo='biblioteca', path=ruta_resuelta_o_original)
        elif tipo_ref in ['absoluta', 'relativa']:
            ruta_norm = normalizar_ruta(ruta_resuelta_o_original)
            key_to_check = ruta_norm
            logger.debug(f"  -> Ruta normalizada interna/rota: '{ruta_norm}'") # DEBUG
            if ruta_norm in archivos_proyecto:
                 if ruta_norm not in rutas_procesadas:
                      dep_info = DependencyInfo(tipo='interna', path=ruta_norm)
                      logger.debug("    -> Clasificado como: INTERNA") # DEBUG
            else:
                 if ruta_norm not in rutas_procesadas:
                      dep_info = DependencyInfo(tipo='interna_rota', path=ruta_norm)
                      logger.debug("    -> Clasificado como: INTERNA_ROTA") # DEBUG
        else:
             logger.debug(f"  -> Tipo referencia no manejado para clasificación: '{tipo_ref}'") # DEBUG
        if dep_info and key_to_check not in rutas_procesadas:
             dependencias_clasificadas.append(dep_info)
             rutas_procesadas.add(key_to_check)
        elif dep_info:
             logger.debug(f"  -> Duplicado omitido: '{key_to_check}'") # DEBUG

    dependencias_clasificadas.sort(key=lambda x: (x['tipo'], x['path']))
    logger.debug(f"Dependencias Regex finales clasificadas: {dependencias_clasificadas}") # DEBUG
    return dependencias_clasificadas