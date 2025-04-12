# proyscan/dependency_analysis/analyzer.py
import logging
from typing import List, Optional, Set, Dict

# Importar todos los parsers
from .python_parser import analizar_python
from .regex_parser import analizar_regex
from .html_parser import analizar_html
from .css_parser import analizar_css
from .java_parser import analizar_java
from .vue_parser import analizar_vue

from ..models import DependencyInfo

logger = logging.getLogger(__name__)


def analizar_dependencias(
    contenido: List[str],
    lenguaje: str,
    ruta_archivo: str,
    archivos_proyecto: Set[str],
    dir_proyecto: str
) -> Optional[List[DependencyInfo]]:
    logger.debug(f"Analizador principal llamado para: {ruta_archivo} (Lenguaje: {lenguaje})")

    if lenguaje == 'python':
        return analizar_python(contenido, ruta_archivo, archivos_proyecto)
    elif lenguaje == 'html':
        return analizar_html(contenido, ruta_archivo, archivos_proyecto)
    elif lenguaje in ['css', 'scss', 'sass', 'less']:
        return analizar_css(contenido, ruta_archivo, archivos_proyecto)
    elif lenguaje == 'java':
        return analizar_java(contenido, ruta_archivo, archivos_proyecto)
    # --- LLAMAR AL PARSER DE VUE ---
    elif lenguaje == 'vue':
        return analizar_vue(contenido, ruta_archivo, archivos_proyecto, dir_proyecto)
    # ------------------------------
    elif lenguaje in [ # Solo quedan JS/TS/PHP/JSX/TSX aquí
        'javascript', 'typescript', 'jsx', 'tsx',
        'php',
        ]:
        logger.debug(f"Usando parser Regex para lenguaje: {lenguaje}")
        return analizar_regex(contenido, lenguaje, ruta_archivo, archivos_proyecto, dir_proyecto)
    else:
        logger.debug(f"Análisis de dependencias no implementado o no aplicable para lenguaje: {lenguaje}")
        return None