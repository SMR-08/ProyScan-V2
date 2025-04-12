# proyscan/dependency_analysis/vue_parser.py
import logging
import os # Necesario para os.path.join
from typing import List, Set, Optional, Dict, Tuple # Añadir Tuple

# Intentar importar BeautifulSoup
try:
    from bs4 import BeautifulSoup, FeatureNotFound
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    # Clases Dummy si BS4 no está
    class BeautifulSoup: pass
    class FeatureNotFound(Exception): pass

# Importar otros parsers y utilidades
from .html_parser import analizar_html # Para analizar <template>
from .css_parser import analizar_css # Para analizar <style>
from .regex_parser import analizar_regex # Para analizar <script>
# Importar utils es crucial aquí para resolver rutas relativas del src de style
from ..utils.path_utils import resolver_ruta_referencia, normalizar_ruta
from ..models import DependencyInfo

logger = logging.getLogger(__name__) # Usa 'proyscan.dependency_analysis.vue_parser'

def analizar_vue(
    contenido_lineas: List[str],
    ruta_archivo_rel: str,
    archivos_proyecto: Set[str],
    dir_proyecto_raiz: str # Necesario para pasar a regex_parser
) -> Optional[List[DependencyInfo]]:
    """
    Analiza dependencias en archivos .vue (SFC) usando un enfoque multi-etapa.
    (Versión con soporte para <style src="...">)
    """
    if not BS4_AVAILABLE:
        logger.error("La biblioteca 'BeautifulSoup4' no está instalada (o falta 'lxml'). No se puede analizar Vue.")
        return None

    logger.debug(f"--- Iniciando análisis Vue (Multi-Etapa) para {ruta_archivo_rel} ---")
    contenido_completo = "\n".join(contenido_lineas)
    if not contenido_completo.strip(): return []

    # Usamos un set de tuplas (tipo, path) para evitar duplicados
    dependencias_unicas_set: Set[Tuple[str, str]] = set()

    try:
        # Parsear con BS4
        try: soup = BeautifulSoup(contenido_completo, 'lxml')
        except FeatureNotFound: soup = BeautifulSoup(contenido_completo, 'html.parser')
        except Exception as e_bs: logger.error(f"Error BS4 parseando {ruta_archivo_rel}", exc_info=True); return None

        # 1. Analizar bloque <script>
        script_tag = soup.find('script')
        if script_tag and script_tag.string:
            logger.debug("Analizando bloque <script>...")
            script_content = script_tag.string.splitlines()
            script_lang_attr = script_tag.get('lang', 'javascript') # Default a JS
            # Mapear lang a nuestros tipos conocidos
            script_lang = 'typescript' if 'ts' in script_lang_attr else 'javascript'
            deps_script = analizar_regex(script_content, script_lang, ruta_archivo_rel, archivos_proyecto, dir_proyecto_raiz)
            if deps_script:
                for dep in deps_script: dependencias_unicas_set.add((dep['type'], dep['path']))
                logger.debug(f"  -> Dependencias <script> (Regex): {[d['path'] for d in deps_script]}")

        # 2. Analizar bloques <style>
        for i, style_tag in enumerate(soup.find_all('style')):
            # 2a. Analizar contenido interno con css_parser
            if style_tag.string:
                logger.debug(f"Analizando contenido <style> #{i+1} con css_parser...")
                style_content = style_tag.string.splitlines()
                style_lang = style_tag.get('lang', 'css') # Podríamos usar esto en el futuro
                deps_style_content = analizar_css(style_content, ruta_archivo_rel, archivos_proyecto)
                if deps_style_content:
                    for dep in deps_style_content: dependencias_unicas_set.add((dep['type'], dep['path']))
                    logger.debug(f"  -> Dependencias contenido <style> #{i+1}: {[d['path'] for d in deps_style_content]}")

            # --- 2b. Analizar atributo 'src' en <style> ---
            style_src = style_tag.get('src')
            if style_src and isinstance(style_src, str) and style_src.strip():
                ref = style_src.strip()
                logger.debug(f"Analizando src='{ref}' en <style> #{i+1}...")
                # Resolver y clasificar esta referencia
                tipo_ref, ruta_resuelta_o_original = resolver_ruta_referencia(ref, ruta_archivo_rel)
                key_to_check = ruta_resuelta_o_original
                dep_info_style_src: Optional[DependencyInfo] = None

                if not ruta_resuelta_o_original: continue

                if tipo_ref == 'url':
                     dep_info_style_src = DependencyInfo(type='url', path=ruta_resuelta_o_original)
                elif tipo_ref == 'externa': # Poco probable para src de style
                     dep_info_style_src = DependencyInfo(type='external', path=ruta_resuelta_o_original)
                elif tipo_ref in ['absoluta', 'relativa']:
                    ruta_norm = normalizar_ruta(ruta_resuelta_o_original)
                    key_to_check = ruta_norm
                    if ruta_norm in archivos_proyecto:
                         dep_info_style_src = DependencyInfo(type='internal', path=ruta_norm)
                    else:
                         dep_info_style_src = DependencyInfo(type='internal_broken', path=ruta_norm)

                if dep_info_style_src:
                     logger.debug(f"  -> Dependencia <style src>: {dep_info_style_src}")
                     dependencias_unicas_set.add((dep_info_style_src['type'], dep_info_style_src['path']))
            # --- Fin análisis 'src' ---

        # 3. Analizar bloque <template> (usando html_parser)
        template_tag = soup.find('template')
        if template_tag:
             logger.debug("Analizando bloque <template> con html_parser...")
             # Asegurarse de obtener solo el contenido como string
             template_content_str = template_tag.decode_contents() # Mejor que .string o .text
             if template_content_str:
                  deps_template = analizar_html(template_content_str.splitlines(), ruta_archivo_rel, archivos_proyecto)
                  if deps_template:
                      for dep in deps_template: dependencias_unicas_set.add((dep['type'], dep['path']))
                      logger.debug(f"  -> Dependencias <template>: {[d['path'] for d in deps_template]}")

    except Exception as e:
        logger.error(f"Error procesando archivo Vue {ruta_archivo_rel}", exc_info=True)
        return None

    # Convertir set de tuplas de nuevo a lista de dicts
    todas_las_dependencias = [DependencyInfo(type=t, path=p) for t, p in dependencias_unicas_set]
    todas_las_dependencias.sort(key=lambda x: (x['type'], x['path']))
    logger.debug(f"Dependencias Vue finales clasificadas: {todas_las_dependencias}")
    return todas_las_dependencias