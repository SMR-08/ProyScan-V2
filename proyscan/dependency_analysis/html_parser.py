# proyscan/dependency_analysis/html_parser.py
import os
import re
import logging # Importar
from typing import List, Set, Optional, Dict
from bs4 import BeautifulSoup, FeatureNotFound

from ..utils.path_utils import resolver_ruta_referencia, normalizar_ruta
from ..models import DependencyInfo

# Obtener logger
logger = logging.getLogger(__name__) # Usa 'proyscan.dependency_analysis.html_parser'

# --- TAG_ATTR_MAP y STYLE_URL_REGEX sin cambios ---
TAG_ATTR_MAP = { 'script': ['src'], 'link': ['href'], 'img': ['src', 'srcset'], 'audio': ['src'], 'video': ['src', 'poster'], 'source': ['src', 'srcset'], 'iframe': ['src'], 'embed': ['src'], 'form': ['action'], 'object': ['data'], }
STYLE_URL_REGEX = re.compile(r"""url\(["']?([^"')]+?)["']?\)""", re.IGNORECASE)

def _extraer_de_srcset(srcset_value: str) -> List[str]:
    # ... (sin cambios, no necesita logging interno) ...
    urls = []
    if not srcset_value: return urls
    parts = srcset_value.split(',')
    for part in parts:
        items = part.strip().split()
        if items: urls.append(items[0])
    return urls

def analizar_html(contenido_lineas: List[str], ruta_archivo_rel: str, archivos_proyecto: Set[str]) -> Optional[List[DependencyInfo]]:
    logger.debug(f"--- Iniciando análisis HTML para {ruta_archivo_rel} ---") # DEBUG
    contenido_completo = "\n".join(contenido_lineas)
    if not contenido_completo.strip():
        logger.debug("Archivo HTML vacío.") # DEBUG
        return []

    dependencias_encontradas_raw: Set[str] = set()
    soup: Optional[BeautifulSoup] = None # Inicializar

    try:
        # Intentar con lxml, luego html.parser
        try:
             soup = BeautifulSoup(contenido_completo, 'lxml')
             logger.debug("HTML parseado con lxml.") # DEBUG
        except FeatureNotFound:
             logger.debug("lxml no encontrado, usando html.parser para HTML.") # DEBUG
             soup = BeautifulSoup(contenido_completo, 'html.parser')
        except Exception as e_parse: # Capturar otros errores de BS
             logger.error(f"Error parseando HTML en {ruta_archivo_rel}", exc_info=True) # ERROR con traceback
             return None
    except Exception as e_general: # Capturar si BS falla de forma inesperada
         logger.error(f"Error inesperado inicializando BeautifulSoup para {ruta_archivo_rel}", exc_info=True)
         return None

    if soup is None: # Doble check por si algo muy raro pasa
         logger.error(f"BeautifulSoup no pudo inicializarse para {ruta_archivo_rel}")
         return None

    # Buscar en tags y atributos definidos
    for tag_name, attrs in TAG_ATTR_MAP.items():
        logger.debug(f"Buscando tags '<{tag_name}>'...") # DEBUG
        try:
             tags_encontrados = soup.find_all(tag_name)
        except Exception as e_find:
             logger.warning(f"Error buscando tags '{tag_name}' en {ruta_archivo_rel}: {e_find}")
             continue # Continuar con el siguiente tag

        logger.debug(f"  Encontrados {len(tags_encontrados)} tags '<{tag_name}>'") # DEBUG
        for i, tag in enumerate(tags_encontrados):
            # print(f"    Tag {i+1}: {tag.name}") # Muy verboso
            if tag_name == 'link':
                rel_attr = tag.get('rel')
                is_stylesheet = False
                if rel_attr:
                    rel_list = rel_attr if isinstance(rel_attr, list) else [rel_attr]
                    if 'stylesheet' in [r.lower() for r in rel_list]:
                         is_stylesheet = True
                if not is_stylesheet:
                     logger.debug(f"    Tag <link> omitido (no es rel='stylesheet')") # DEBUG
                     continue

            for attr_name in attrs:
                value = tag.get(attr_name)
                if value and isinstance(value, str):
                     logger.debug(f"    Encontrado atributo '{attr_name}' con valor='{value[:50]}...'") # DEBUG (cortar valor largo)
                     if attr_name == 'srcset':
                         urls = _extraer_de_srcset(value)
                         logger.debug(f"      -> srcset URLs extraídas: {urls}") # DEBUG
                         for url in urls:
                              if url.strip(): dependencias_encontradas_raw.add(url.strip())
                     else:
                         if value.strip(): dependencias_encontradas_raw.add(value.strip())

    # Buscar url() en atributos 'style'
    logger.debug(f"Buscando url() en atributos 'style'...") # DEBUG
    try:
         tags_con_style = soup.find_all(attrs={"style": True})
    except Exception as e_find_style:
         logger.warning(f"Error buscando tags con atributo 'style' en {ruta_archivo_rel}: {e_find_style}")
         tags_con_style = []

    logger.debug(f"  Encontrados {len(tags_con_style)} tags con atributo 'style'") # DEBUG
    for tag_with_style in tags_con_style:
         style_content = tag_with_style.get('style')
         if isinstance(style_content, str):
             try:
                 urls_in_style = STYLE_URL_REGEX.findall(style_content)
                 if urls_in_style: logger.debug(f"    URLs encontradas en style='{style_content[:50]}...': {urls_in_style}") # DEBUG
                 for url in urls_in_style:
                     if url.strip(): dependencias_encontradas_raw.add(url.strip())
             except Exception as e_regex:
                  logger.warning(f"Error con Regex de estilo en {ruta_archivo_rel}: {e_regex}")


    # --- Resolución y Clasificación (usar logger) ---
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
        # ... (resto de lógica de clasificación igual) ...
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
    logger.debug(f"Dependencias HTML finales clasificadas: {dependencias_clasificadas}") # DEBUG
    return dependencias_clasificadas