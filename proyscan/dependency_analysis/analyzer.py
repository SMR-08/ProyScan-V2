# proyscan/dependency_analysis/analyzer.py
from typing import List, Optional, Set, Dict

# Importar el parser específico de Python
from .python_parser import analizar_python
# Importar el modelo
from ..models import DependencyInfo
# (Dejar placeholders para otros parsers si los tienes)
# from .regex_parser import analizar_regex

def analizar_dependencias(
    contenido: List[str],
    lenguaje: str,
    ruta_archivo: str,
    archivos_proyecto: Set[str],
    dir_proyecto: str # Aunque no lo usemos directamente aquí, puede ser útil para otros parsers
) -> Optional[List[DependencyInfo]]:
    """
    Función principal para analizar dependencias de un archivo.
    Selecciona el método adecuado según el lenguaje.
    """
    # print(f"[DEBUG Analyzer] Analizando: {ruta_archivo} (Lenguaje: {lenguaje})") # Menos verboso

    if lenguaje == 'python':
        # Llamar al parser específico de Python
        # No necesitamos dir_proyecto aquí porque trabajamos con rutas relativas y el set
        return analizar_python(contenido, ruta_archivo, archivos_proyecto)

    # --- Placeholder para otros lenguajes (Fase 2+) ---
    # elif lenguaje in ['html', 'css', 'javascript', 'php']:
    #     # return analizar_regex(contenido, lenguaje, ruta_archivo, archivos_proyecto, dir_proyecto)
    #     print(f"      * Análisis de dependencias para '{lenguaje}' aún no implementado.")
    #     return [] # Devolver lista vacía por ahora
    # -------------------------------------------------

    else:
        # Lenguaje no soportado para análisis de dependencias
        # print(f"      * Análisis de dependencias no soportado para '{lenguaje}'.")
        return None # O devolver lista vacía si se prefiere consistencia