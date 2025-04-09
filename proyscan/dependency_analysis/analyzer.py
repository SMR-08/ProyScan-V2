# proyscan/dependency_analysis/analyzer.py
from typing import List, Optional, Set, Dict

# Importar parsers específicos
from .python_parser import analizar_python
from .regex_parser import analizar_regex # Lo mantenemos para JS y PHP por ahora
from .html_parser import analizar_html   # Nuevo parser HTML
from .css_parser import analizar_css     # Nuevo parser CSS
# Importar el modelo
from ..models import DependencyInfo

def analizar_dependencias(
    contenido: List[str],
    lenguaje: str,
    ruta_archivo: str,
    archivos_proyecto: Set[str],
    dir_proyecto: str
) -> Optional[List[DependencyInfo]]:
    """
    Función principal para analizar dependencias de un archivo.
    Selecciona el método adecuado según el lenguaje.
    """

    if lenguaje == 'python':
        return analizar_python(contenido, ruta_archivo, archivos_proyecto)
    # --- Usar parsers específicos para HTML y CSS ---
    elif lenguaje == 'html':
        return analizar_html(contenido, ruta_archivo, archivos_proyecto)
    elif lenguaje == 'css':
        return analizar_css(contenido, ruta_archivo, archivos_proyecto)
    # ----------------------------------------------
    # --- Mantener Regex para JS y PHP por ahora ---
    elif lenguaje in ['javascript', 'php']:
        return analizar_regex(contenido, lenguaje, ruta_archivo, archivos_proyecto, dir_proyecto)
    # ----------------------------------------------
    else:
        # Lenguaje no soportado
        return None