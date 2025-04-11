# proyscan/dependency_analysis/css_parser.py
import os
import logging # Importar logging
from typing import List, Set, Optional, Dict
import tinycss2 # Importar tinycss2

# Importar utilidades y modelos
from ..utils.path_utils import resolver_ruta_referencia, normalizar_ruta
from ..models import DependencyInfo

# Obtener logger
logger = logging.getLogger(__name__) # Usa 'proyscan.dependency_analysis.css_parser'


def analizar_css(
    contenido_lineas: List[str],
    ruta_archivo_rel: str,
    archivos_proyecto: Set[str],
    # dir_proyecto_raiz: str # No necesario directamente aquí
) -> Optional[List[DependencyInfo]]:
    """
    Analiza dependencias en archivos CSS usando tinycss2. (Versión Corregida v2 con Logging)
    """
    logger.debug(f"--- Iniciando análisis CSS para {ruta_archivo_rel} ---") # DEBUG
    contenido_completo = "\n".join(contenido_lineas)
    if not contenido_completo.strip():
        logger.debug("Archivo CSS vacío.") # DEBUG
        return []

    dependencias_encontradas_raw: Set[str] = set()
    rules = []

    try:
        # Parsear la hoja de estilo. skip_comments=True es bueno.
        rules = tinycss2.parse_stylesheet(contenido_completo, skip_comments=True)
        logger.debug(f"Parseo CSS inicial OK. {len(rules)} tokens principales.") # DEBUG

        for i, token in enumerate(rules):
            token_type = getattr(token, 'type', 'N/A')
            # logger.debug(f"Procesando token CSS {i}: type={token_type}") # DEBUG (Muy verboso)

            # --- Buscar @import ---
            if token_type == 'at-rule':
                rule_name_attr = getattr(token, 'name', None)
                if rule_name_attr and isinstance(rule_name_attr, str):
                    rule_name_lower = rule_name_attr.lower()
                    if rule_name_lower == 'import':
                        logger.debug("Encontrado @import.") # DEBUG
                        import_value: Optional[str] = None
                        prelude = getattr(token, 'prelude', [])
                        for node in prelude:
                            node_type = getattr(node, 'type', 'N/A')
                            if node_type == 'string' or node_type == 'url':
                                import_value = getattr(node, 'value', None)
                                if import_value:
                                    logger.debug(f"    -> Valor @import extraído: '{import_value}'") # DEBUG
                                    dependencias_encontradas_raw.add(import_value.strip())
                                    break

            # --- Buscar funciones url() ---
            tokens_a_buscar_url = []
            prelude = getattr(token, 'prelude', [])
            content = getattr(token, 'content', None)
            tokens_a_buscar_url.extend(prelude)

            if content:
                 if token_type == 'qualified-rule':
                      if isinstance(content, list):
                           tokens_a_buscar_url.extend(content)
                 elif token_type == 'at-rule':
                      try:
                           if hasattr(content, '__iter__'):
                                declarations = tinycss2.parse_declaration_list(content, skip_comments=True)
                                for decl in declarations:
                                     if getattr(decl, 'type', '') == 'declaration':
                                          value_tokens = getattr(decl, 'value', [])
                                          tokens_a_buscar_url.extend(value_tokens)
                           # else: logger.debug(f"  Content de AtRule no es iterable: {type(content)}") # DEBUG
                      except Exception as e_decl:
                           logger.warning(f"Error parseando declaraciones en AtRule '{getattr(token, 'name', 'N/A')}' en {ruta_archivo_rel}: {e_decl}")


            # Iterar en la lista recolectada para encontrar 'url('
            for node in tokens_a_buscar_url:
                 node_type = getattr(node, 'type', '')
                 func_name_attr = getattr(node, 'name', None)
                 func_name_lower = func_name_attr.lower() if isinstance(func_name_attr, str) else None

                 if node_type == 'function' and func_name_lower == 'url':
                     logger.debug("Encontrada función url().") # DEBUG
                     url_value: Optional[str] = None
                     arguments = getattr(node, 'arguments', [])
                     # logger.debug(f"  Argumentos url(): {[arg.type + ':' + repr(getattr(arg,'value','N/A')) for arg in arguments]}") # DEBUG (Muy verboso)
                     for arg_node in arguments:
                          arg_type = getattr(arg_node, 'type', '')
                          if arg_type == 'whitespace': continue
                          if arg_type in ('string', 'url', 'ident'):
                               url_value = getattr(arg_node, 'value', None)
                               if url_value:
                                    logger.debug(f"    -> Valor url() extraído: '{url_value}'") # DEBUG
                                    dependencias_encontradas_raw.add(url_value.strip())
                                    break
                     # if not url_value: logger.debug("  No se encontró valor útil en argumentos de url().") # DEBUG


    except Exception as e_parse:
        logger.error(f"--- ERROR CRÍTICO DURANTE PARSEO CSS ({type(e_parse).__name__}) en {ruta_archivo_rel} ---", exc_info=True) # ERROR con traceback
        return None

    # --- Resolución y Clasificación ---
    dependencias_clasificadas: List[DependencyInfo] = []
    rutas_procesadas = set()
    logger.debug(f"Dependencias crudas encontradas: {dependencias_encontradas_raw}") # DEBUG

    for ref in dependencias_encontradas_raw:
        if ref == '#' or ref.startswith(('javascript:', 'mailto:', 'tel:', 'data:')):
            logger.debug(f"Omitiendo referencia no procesable: '{ref}'") # DEBUG
            continue

        logger.debug(f"Resolviendo referencia cruda: '{ref}'") # DEBUG
        type_ref, ruta_resuelta_o_original = resolver_ruta_referencia(ref, ruta_archivo_rel)
        logger.debug(f"  -> type Ref: '{type_ref}', Ruta/Original: '{ruta_resuelta_o_original}'") # DEBUG
        dep_info: Optional[DependencyInfo] = None
        key_to_check = ruta_resuelta_o_original

        if not ruta_resuelta_o_original: continue

        if type_ref == 'url': dep_info = DependencyInfo(type='url', path=ruta_resuelta_o_original)
        elif type_ref == 'external': dep_info = DependencyInfo(type='external', path=ruta_resuelta_o_original)
        elif type_ref in ['absoluta', 'relativa']:
            ruta_norm = normalizar_ruta(ruta_resuelta_o_original)
            key_to_check = ruta_norm
            logger.debug(f"  -> Ruta normalizada interna/rota: '{ruta_norm}'") # DEBUG
            if ruta_norm in archivos_proyecto:
                 if ruta_norm not in rutas_procesadas:
                      dep_info = DependencyInfo(type='internal', path=ruta_norm)
                      logger.debug("    -> Clasificado como: INTERNAL") # DEBUG
            else:
                 if ruta_norm not in rutas_procesadas:
                      dep_info = DependencyInfo(type='internal_broken', path=ruta_norm)
                      logger.debug("    -> Clasificado como: INTERNAL_BROKEN") # DEBUG
        else:
             logger.debug(f"  -> type referencia no manejado para clasificación: '{type_ref}'") # DEBUG

        if dep_info and key_to_check not in rutas_procesadas:
             dependencias_clasificadas.append(dep_info)
             rutas_procesadas.add(key_to_check)
        elif dep_info:
             logger.debug(f"  -> Duplicado omitido: '{key_to_check}'") # DEBUG

    dependencias_clasificadas.sort(key=lambda x: (x['type'], x['path']))
    logger.debug(f"Dependencias CSS finales clasificadas: {dependencias_clasificadas}") # DEBUG

    return dependencias_clasificadas