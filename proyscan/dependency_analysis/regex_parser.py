# proyscan/dependency_analysis/regex_parser.py
import re
import os
import logging
from typing import List, Set, Optional, Dict, Tuple

# Importar utilidades y modelos
from ..utils.path_utils import resolver_ruta_referencia, normalizar_ruta
from ..models import DependencyInfo

# Obtener logger
logger = logging.getLogger(__name__) # Usa 'proyscan.dependency_analysis.regex_parser'

# --- Definición de Patrones Regex (Sin Java, Sin Vue) ---

PATTERNS_BASE = {
    'html': [
        re.compile(r"""<(?:script|img|audio|video|iframe|source|embed)\s+[^>]*?src\s*=\s*["']([^"']+)["'][^>]*?>""", re.I | re.S),
        re.compile(r"""<link\s+[^>]*?href\s*=\s*["']([^"']+)["'][^>]*?rel\s*=\s*["']stylesheet["'][^>]*?>""", re.I | re.S),
        re.compile(r"""<a\s+[^>]*?href\s*=\s*["']([^"']+)["'][^>]*?>""", re.I | re.S),
        re.compile(r"""<form\s+[^>]*?action\s*=\s*["']([^"']+)["'][^>]*?>""", re.I | re.S),
        re.compile(r"""style\s*=\s*["'][^"']*?url\(["']?([^"')]+?)["']?\)[^"']*?["']""", re.I | re.S),
    ],
    'css': [
        re.compile(r"""@import\s+(?:url\()?["']([^"'\)]+)["']\)?\s*;?""", re.I),
        re.compile(r"""url\(["']?([^"')]+?)["']?\)""", re.I),
    ],
    'javascript': [
        re.compile(r"""import(?:["'\s]*(?:[\w*{}\n\r\s,]+from\s*)?)(["'])([^"'\n\r]+?)\1\s*;?""", re.M),
        re.compile(r"""require\s*\(\s*(["'])([^"'\n\r]+?)\1\s*\)\s*;?"""),
        re.compile(r"""importScripts\s*\(\s*(["'])([^"'\n\r]+?)\1\s*\)\s*;?"""),
        re.compile(r"""new\s+Worker\s*\(\s*(["'])([^"'\n\r]+?)\1\s*\)"""),
        re.compile(r"""fetch\s*\(\s*(["'])([^"'\n\r]+?)\1\s*(?:,|\))""", re.M),
    ],
    'php': [
        re.compile(r"""(?:include|require|include_once|require_once)\s+(?:(?:__DIR__|\$[_a-zA-Z0-9]+)\s*\.\s*)?(["'])([^"']+\.php)\1\s*;""", re.I),
    ],
    'typescript': [
        # Patrón mejorado para capturar 'from', 'require', etc. correctamente
        re.compile(r"""(?:import|require|from)\s*(?:.*?\sfrom\s*)?(["'])([^"'\n\r]+?)\1""", re.M),
        # Patrón específico para import type
        re.compile(r"""import\s+type\s+.*?from\s*(["'])([^"'\n\r]+?)\1""", re.M),
        re.compile(r"""importScripts\s*\(\s*(["'])([^"'\n\r]+?)\1\s*\)\s*;?"""),
        re.compile(r"""new\s+Worker\s*\(\s*(["'])([^"'\n\r]+?)\1\s*\)"""),
        re.compile(r"""fetch\s*\(\s*(["'])([^"'\n\r]+?)\1\s*(?:,|\))""", re.M),
        re.compile(r"""///\s*<reference\s+path\s*=\s*["']([^"']+)["']\s*/>""", re.I)
    ],
}

# Copiar patrones a los lenguajes derivados
PATTERNS = PATTERNS_BASE.copy()
PATTERNS['scss'] = PATTERNS['css'][:]
PATTERNS['sass'] = PATTERNS['css'][:]
PATTERNS['less'] = PATTERNS['css'][:]
PATTERNS['jsx'] = PATTERNS['javascript'][:] # Usar patrones JS para JSX
PATTERNS['tsx'] = PATTERNS['typescript'][:] # Usar patrones TS para TSX
# ---------------------------------------------------------


def analizar_regex(
    contenido_lineas: List[str],
    lenguaje: str,
    ruta_archivo_rel: str,
    archivos_proyecto: Set[str],
    dir_proyecto_raiz: str
) -> Optional[List[DependencyInfo]]:
    """
    Analiza dependencias usando Regex para JS, TS, PHP.
    """
    logger.debug(f"--- Iniciando análisis Regex para {ruta_archivo_rel} (Lenguaje: {lenguaje}) ---")
    if lenguaje not in PATTERNS:
        logger.debug(f"Lenguaje '{lenguaje}' no tiene patrones Regex definidos.")
        return None

    contenido_completo = "\n".join(contenido_lineas)
    if not contenido_completo.strip(): return []

    dependencias_encontradas_raw: Set[str] = set()
    for pattern in PATTERNS[lenguaje]:
        logger.debug(f"Aplicando Regex: {pattern.pattern}")
        try:
            matches = pattern.findall(contenido_completo)
            if matches: logger.debug(f"  -> Coincidencias encontradas: {matches}")
            for match in matches:
                # Ajustar extracción si el patrón tiene múltiples grupos
                if isinstance(match, tuple):
                    # Priorizar el último grupo que no sea comilla, si no, el último
                    referencia = next((g for g in reversed(match) if g not in ('"', "'") and g is not None), match[-1] if match else None)
                elif isinstance(match, str):
                    referencia = match
                else:
                    referencia = None

                if isinstance(referencia, str) and referencia.strip():
                     dependencias_encontradas_raw.add(referencia.strip())
                     logger.debug(f"    -> Añadida dependencia cruda: '{referencia.strip()}'")
        except Exception as e: logger.warning(f"Error Regex {pattern.pattern} en {ruta_archivo_rel}: {e}")

    # --- Resolución y Clasificación (Ajustada para JS/TS) ---
    dependencias_clasificadas: List[DependencyInfo] = []
    rutas_procesadas = set()
    logger.debug(f"Dependencias crudas encontradas ({lenguaje}): {dependencias_encontradas_raw}")

    for ref in dependencias_encontradas_raw:
        if ref == '#' or ref.startswith(('javascript:', 'mailto:', 'tel:', 'data:')): continue

        tipo_ref, ruta_resuelta_o_original = resolver_ruta_referencia(ref, ruta_archivo_rel)
        dep_info: Optional[DependencyInfo] = None
        key_to_check = ruta_resuelta_o_original

        if not ruta_resuelta_o_original: continue

        if tipo_ref == 'url':
            dep_info = DependencyInfo(type='url', path=ruta_resuelta_o_original)
        elif tipo_ref == 'externa':
             # Para JS/TS/PHP, 'externa' significa biblioteca o paquete no resoluble
             logger.debug(f"  -> Clasificado como LIBRARY: '{ruta_resuelta_o_original}'")
             dep_info = DependencyInfo(type='library', path=ruta_resuelta_o_original)
        elif tipo_ref in ['absoluta', 'relativa']:
            ruta_norm = normalizar_ruta(ruta_resuelta_o_original)
            key_to_check = ruta_norm
            logger.debug(f"  -> Ruta normalizada interna/rota: '{ruta_norm}'")
            if ruta_norm in archivos_proyecto:
                 if ruta_norm not in rutas_procesadas:
                      dep_info = DependencyInfo(type='internal', path=ruta_norm)
                      logger.debug("    -> Clasificado como: INTERNAL")
            else:
                 # --- AJUSTE TS/JS ---
                 # Si la referencia original terminaba en .js o .ts pero no se encontró,
                 # es más probable que sea una referencia rota que una biblioteca.
                 # Mantenemos 'internal_broken' para estos casos.
                 # Para otros casos (ej: fetch a '/api/info'), también es 'internal_broken'.
                 # --------------------
                 if ruta_norm not in rutas_procesadas:
                      dep_info = DependencyInfo(type='internal_broken', path=ruta_norm)
                      logger.debug("    -> Clasificado como: INTERNAL_BROKEN")
        else:
             logger.debug(f"  -> Tipo referencia no manejado para clasificación: '{tipo_ref}'")

        # Añadir si no es duplicado y se creó dep_info
        if dep_info and key_to_check not in rutas_procesadas:
             dependencias_clasificadas.append(dep_info)
             rutas_procesadas.add(key_to_check)
        elif dep_info:
             logger.debug(f"  -> Duplicado omitido: '{key_to_check}'")

    dependencias_clasificadas.sort(key=lambda x: (x['type'], x['path']))
    logger.debug(f"Dependencias Regex finales clasificadas ({lenguaje}): {dependencias_clasificadas}")
    return dependencias_clasificadas