# proyscan/dependency_analysis/java_parser.py
import logging
from typing import List, Set, Optional, Dict

# Intentar importar javalang
try:
    import javalang
    from javalang.tokenizer import LexerError
    from javalang.parser import JavaSyntaxError
    JAVALANG_AVAILABLE = True
except ImportError:
    JAVALANG_AVAILABLE = False
    # Definir clases dummy para que el resto del código no falle si no está instalado
    class LexerError(Exception): pass
    class JavaSyntaxError(Exception): pass

# Importar modelos y utilidades
from ..models import DependencyInfo
from ..utils.path_utils import es_stdlib # Podríamos necesitar una versión Java de esto

logger = logging.getLogger(__name__) # Usa 'proyscan.dependency_analysis.java_parser'

# Definir paquetes estándar de Java (lista más extensa)
JAVA_STDLIB_PREFIXES = (
    'java.', 'javax.', 'jdk.', 'com.sun.', 'org.w3c.', 'org.xml.', 'org.omg.'
)

def es_java_stdlib(nombre_paquete_completo: str) -> bool:
    """Comprueba si un nombre de paquete/clase Java pertenece a la stdlib."""
    return nombre_paquete_completo.startswith(JAVA_STDLIB_PREFIXES)

def clasificar_dependencia_java(import_path: str) -> DependencyInfo:
    """Clasifica una dependencia Java encontrada."""
    if es_java_stdlib(import_path):
        logger.debug(f"  -> Clasificado como Java STDLIB: '{import_path}'")
        return DependencyInfo(type='stdlib', path=import_path)
    else:
        # Con javalang (análisis estático sin classpath), no podemos saber
        # si 'com.mycompany.util.Calculator' es interno o una biblioteca externa.
        # Por defecto, lo clasificamos como 'library'.
        # Una mejora futura podría intentar mapear esto a archivos si la estructura sigue convenciones.
        logger.debug(f"  -> Clasificado como Java LIBRARY (o interno no resoluble): '{import_path}'")
        return DependencyInfo(type='library', path=import_path)


def analizar_java(
    contenido_lineas: List[str],
    ruta_archivo_rel: str,
    archivos_proyecto: Set[str] # No usado activamente aquí, pero mantenido por consistencia
) -> Optional[List[DependencyInfo]]:
    """
    Analiza dependencias 'import' en archivos Java usando javalang.
    """
    if not JAVALANG_AVAILABLE:
        logger.error("La biblioteca 'javalang' no está instalada. No se puede analizar Java.")
        # Devolver None indica fallo, lista vacía indica que no se encontraron deps
        return None

    logger.debug(f"--- Iniciando análisis Java (javalang) para {ruta_archivo_rel} ---")
    contenido_completo = "\n".join(contenido_lineas)
    if not contenido_completo.strip():
        logger.debug("Archivo Java vacío.")
        return []

    dependencias_clasificadas: List[DependencyInfo] = []
    imports_encontrados: Set[str] = set() # Usar set para evitar duplicados crudos

    try:
        # Parsear el código fuente Java
        tree = javalang.parse.parse(contenido_completo)

        # Filtrar para encontrar nodos de importación
        # Usamos filter() que devuelve un generador de (path_in_tree, node)
        for _, node in tree.filter(javalang.tree.Import):
            # node.path contiene el string completo del import (ej: 'java.util.ArrayList')
            import_path = getattr(node, 'path', None)
            if import_path and isinstance(import_path, str):
                logger.debug(f"  -> Import crudo encontrado: '{import_path}'")
                imports_encontrados.add(import_path) # Añadir al set

    # Manejar errores específicos de javalang y errores generales
    except (LexerError, JavaSyntaxError) as e_parse:
        logger.warning(f"Error de sintaxis/lexer Java en {ruta_archivo_rel}: {e_parse}. No se analizan dependencias.")
        return None # Indicar fallo en el análisis de este archivo
    except Exception as e_general:
        logger.error(f"Error inesperado analizando Java en {ruta_archivo_rel}", exc_info=True)
        return None

    # Clasificar los imports únicos encontrados
    for import_path in sorted(list(imports_encontrados)):
         dependencia = clasificar_dependencia_java(import_path)
         dependencias_clasificadas.append(dependencia)

    # La ordenación final ya la hace obtener_dependencias si se quisiera
    # dependencias_clasificadas.sort(key=lambda x: (x['type'], x['path']))
    logger.debug(f"Dependencias Java finales clasificadas: {dependencias_clasificadas}")
    return dependencias_clasificadas