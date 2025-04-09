# proyscan/dependency_analysis/analyzer.py
from typing import List, Optional, Set, Dict

# Importar parsers específicos
from .python_parser import analizar_python
from .regex_parser import analizar_regex # Importar el nuevo parser Regex
# Importar el modelo
from ..models import DependencyInfo

def analizar_dependencias(
    contenido: List[str],
    lenguaje: str,
    ruta_archivo: str,
    archivos_proyecto: Set[str],
    dir_proyecto: str # Necesario para el regex_parser
) -> Optional[List[DependencyInfo]]:
    """
    Función principal para analizar dependencias de un archivo.
    Selecciona el método adecuado según el lenguaje.
    """

    if lenguaje == 'python':
        # Llamar al parser específico de Python
        return analizar_python(contenido, ruta_archivo, archivos_proyecto)

    # --- LLAMADA AL PARSER REGEX PARA LENGUAJES WEB ---
    elif lenguaje in ['html', 'css', 'javascript', 'php']:
        # Pasar dir_proyecto que puede ser necesario para resolver rutas absolutas '/'
        return analizar_regex(contenido, lenguaje, ruta_archivo, archivos_proyecto, dir_proyecto)
    # -------------------------------------------------

    else:
        # Lenguaje no soportado para análisis de dependencias
        # print(f"      * Análisis de dependencias no soportado para '{lenguaje}'.")
        return None