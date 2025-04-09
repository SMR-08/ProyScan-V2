# proyscan/utils/path_utils.py
import os
import sys
from typing import Optional, Set
from ..config import MAPA_LENGUAJES, LENGUAJE_DEFECTO # Import relativo dentro del paquete

# --- Funciones existentes ---
def obtener_lenguaje_extension(ruta_archivo: str) -> str:
    """Determina el lenguaje/tipo basado en la extensión del archivo."""
    _, extension = os.path.splitext(ruta_archivo)
    if not extension:
        return LENGUAJE_DEFECTO
    ext = extension.lower()
    return MAPA_LENGUAJES.get(ext, LENGUAJE_DEFECTO)

def normalizar_ruta(ruta: str) -> str:
    """Normaliza una ruta usando '/' y eliminando redundancias."""
    # Usar os.path.abspath si es necesario para resolver '..' correctamente
    # antes de normalizar, pero tener cuidado si la base no es real.
    # normpath solo simplifica, no valida existencia.
    ruta_limpia = os.path.normpath(ruta).replace(os.sep, '/')
    # Asegurarse de que no empiece con '/' si era relativa originalmente
    if not ruta.startswith('/') and ruta_limpia.startswith('/'):
         ruta_limpia = ruta_limpia[1:]
    return ruta_limpia

# --- Nuevas Funciones para Resolución de Módulos Python ---

def _intentar_ruta_modulo(ruta_base_rel: str, archivos_proyecto: Set[str]) -> Optional[str]:
    """
    Intenta encontrar un archivo .py o un paquete __init__.py para una ruta base.
    Devuelve la ruta relativa normalizada del archivo/paquete encontrado, o None.
    """
    # 1. Intentar como archivo .py
    ruta_py = f"{ruta_base_rel}.py"
    if ruta_py in archivos_proyecto:
        return ruta_py

    # 2. Intentar como paquete (directorio con __init__.py)
    ruta_init = normalizar_ruta(f"{ruta_base_rel}/__init__.py")
    if ruta_init in archivos_proyecto:
        # Devolvemos la ruta al __init__.py como representación del paquete
        return ruta_init

    return None

def resolver_import_python(
    modulo_importado: str, # Ej: 'os', '.utils', '..config.settings', 'mi_app.helpers'
    nivel_relativo: int,    # 0 para absoluto, 1 para '.', 2 para '..'
    ruta_archivo_actual_rel: str, # Ej: 'src/mi_app/views.py'
    archivos_proyecto: Set[str],
    # dir_proyecto_raiz: str # No necesario si trabajamos con relativas y archivos_proyecto
) -> Optional[str]:
    """
    Intenta resolver un nombre de módulo Python a una ruta de archivo/paquete
    relativa al proyecto. Devuelve la ruta normalizada o None si no se encuentra
    internamente o es claramente externo.
    """
    # print(f"[DEBUG Resolver] Mod: '{modulo_importado}', Nivel: {nivel_relativo}, Origen: '{ruta_archivo_actual_rel}'")

    # --- Caso 1: Importación Relativa (nivel_relativo > 0) ---
    if nivel_relativo > 0:
        directorio_actual = os.path.dirname(ruta_archivo_actual_rel)
        # Subir niveles según nivel_relativo
        niveles_subir = nivel_relativo - 1 # '.' es nivel 1 (0 subir), '..' es nivel 2 (1 subir)
        directorio_base_rel = directorio_actual
        for _ in range(niveles_subir):
            directorio_base_rel = os.path.dirname(directorio_base_rel)
            if not directorio_base_rel: # Hemos subido más allá de la raíz
                 # print(f"[DEBUG Resolver] Error: Subida relativa excede la raíz.")
                 return None # Import relativo inválido

        # Combinar con el nombre del módulo (si existe)
        # Si es 'from . import x', modulo_importado es None o ''
        # Si es 'from .modulo import x', modulo_importado es 'modulo'
        partes_modulo = modulo_importado.split('.') if modulo_importado else []
        ruta_tentativa_base = os.path.join(directorio_base_rel, *partes_modulo)
        ruta_base_norm = normalizar_ruta(ruta_tentativa_base)

        # Intentar encontrar .py o __init__.py
        ruta_encontrada = _intentar_ruta_modulo(ruta_base_norm, archivos_proyecto)
        # print(f"[DEBUG Resolver Relativo] Base: '{ruta_base_norm}', Encontrada: '{ruta_encontrada}'")
        return ruta_encontrada # Puede ser None si no se encuentra

    # --- Caso 2: Importación Absoluta (nivel_relativo == 0) ---
    else:
        # Simplificación: Asumimos que las importaciones absolutas que contienen '.'
        # se refieren a la estructura del proyecto directamente desde la raíz.
        # Ej: 'mi_app.utils.helpers' -> 'mi_app/utils/helpers'
        partes_modulo = modulo_importado.split('.')
        ruta_tentativa_base = os.path.join(*partes_modulo) # Se une desde la raíz implícita
        ruta_base_norm = normalizar_ruta(ruta_tentativa_base)

        # Intentar encontrar .py o __init__.py
        ruta_encontrada = _intentar_ruta_modulo(ruta_base_norm, archivos_proyecto)
        # print(f"[DEBUG Resolver Absoluto] Base: '{ruta_base_norm}', Encontrada: '{ruta_encontrada}'")
        return ruta_encontrada # Puede ser None si no es interno o stdlib simple

# No necesitamos la función resolver_ruta_dependencia genérica por ahora
# ya que nos enfocamos en Python.

# Lista simplificada de módulos stdlib comunes (más robusto sería usar sys.stdlib_module_names si Python >= 3.10)
# O mantener una lista más extensa precalculada.
STDLIBS_COMUNES = {
    'os', 'sys', 'json', 're', 'math', 'datetime', 'time', 'collections',
    'itertools', 'functools', 'pathlib', 'shutil', 'subprocess', 'argparse',
    'logging', 'io', 'typing', 'abc', 'enum', 'random', 'pickle', 'copy',
    'hashlib', 'base64', 'codecs', 'ast'
    # Añadir más según sea necesario o usar método más completo
}

def es_stdlib(nombre_modulo: str) -> bool:
    """Comprueba si un nombre de módulo (primer nivel) pertenece a la stdlib."""
    # Solo comprobamos el primer componente (ej: 'os' en 'os.path')
    primer_componente = nombre_modulo.split('.')[0]
    return primer_componente in STDLIBS_COMUNES