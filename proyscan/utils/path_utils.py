# proyscan/utils/path_utils.py
import os
import sys
import re
import logging
from typing import Optional, Set, Tuple, List
from urllib.parse import urlparse

# Importar dependencias del mismo paquete
from ..config import MAPA_LENGUAJES, LENGUAJE_DEFECTO

# Obtener logger
logger = logging.getLogger(__name__)

# --- Definir STDLIBS_COMUNES AQUÍ ARRIBA ---
STDLIBS_COMUNES = {
    'os', 'sys', 'json', 're', 'math', 'datetime', 'time', 'collections',
    'itertools', 'functools', 'pathlib', 'shutil', 'subprocess', 'argparse',
    'logging', 'io', 'typing', 'abc', 'enum', 'random', 'pickle', 'copy',
    'hashlib', 'base64', 'codecs', 'ast'
}
# -----------------------------------------

# --- Funciones existentes ---
def obtener_lenguaje_extension(ruta_archivo: str) -> str:
    _, extension = os.path.splitext(ruta_archivo)
    if not extension: return LENGUAJE_DEFECTO
    ext = extension.lower()
    return MAPA_LENGUAJES.get(ext, LENGUAJE_DEFECTO)

def normalizar_ruta(ruta: str) -> str:
    ruta_limpia = os.path.normpath(ruta).replace(os.sep, '/')
    if ruta.startswith("./") and not ruta_limpia.startswith("./") and not ruta_limpia.startswith("../"):
         if ruta_limpia != '.': ruta_limpia = "./" + ruta_limpia
    if ruta in ('', '.') and ruta_limpia == '.': return ruta
    if ruta.endswith('/') and not ruta_limpia.endswith('/') and len(ruta_limpia) > 1: ruta_limpia += '/'
    return ruta_limpia

def _intentar_ruta_modulo(ruta_base_rel: str, archivos_proyecto: Set[str]) -> Tuple[Optional[str], bool]:
    """
    Intenta encontrar un archivo .py o un paquete __init__.py para una ruta base.
    Devuelve: (ruta_relativa_normalizada | None, es_paquete)
    """
    ruta_py = normalizar_ruta(f"{ruta_base_rel}.py")
    if ruta_py in archivos_proyecto:
        logger.debug(f"_intentar_ruta_modulo encontró archivo: '{ruta_py}'")
        return ruta_py, False

    ruta_init = normalizar_ruta(os.path.join(ruta_base_rel, "__init__.py"))
    if ruta_init in archivos_proyecto:
        logger.debug(f"_intentar_ruta_modulo encontró paquete via: '{ruta_init}'")
        return ruta_init, True

    logger.debug(f"_intentar_ruta_modulo no encontró ni '{ruta_py}' ni '{ruta_init}' para base '{ruta_base_rel}'")
    return None, False

def resolver_import_python(
    modulo_base: str, # Ej: 'os', '', '..config', 'mi_app.utils' -> El módulo base del from/import
    nombres_importados: List[str], # Ej: ['path'], ['settings'], ['helper'], ['*'] -> Los nombres específicos o '*'
    nivel_relativo: int,
    ruta_archivo_actual_rel: str,
    archivos_proyecto: Set[str]
) -> List[Tuple[str, Optional[str]]]:
    """
    Intenta resolver importaciones Python a rutas relativas del proyecto.
    Devuelve una LISTA de tuplas: [(nombre_original, ruta_resuelta | None), ...]
    Esto permite manejar 'from . import a, b' correctamente.
    """
    logger.debug(f"Resolviendo Import Python: Base='{modulo_base}', Nombres={nombres_importados}, Nivel={nivel_relativo}, Origen='{ruta_archivo_actual_rel}'")

    rutas_resueltas: List[Tuple[str, Optional[str]]] = []

    # --- Calcular Directorio Base Relativo (igual que antes) ---
    directorio_base_rel = ''
    if nivel_relativo > 0:
        directorio_actual = os.path.dirname(ruta_archivo_actual_rel) if os.path.dirname(ruta_archivo_actual_rel) else '.'
        niveles_subir = nivel_relativo - 1
        directorio_base_rel = directorio_actual
        for _ in range(niveles_subir):
            parent_dir = os.path.dirname(directorio_base_rel)
            if parent_dir == directorio_base_rel and nivel_relativo > 1:
                logger.warning(f"Import relativo nivel {nivel_relativo} desde '{ruta_archivo_actual_rel}' parece exceder la raíz.")
                # No podemos resolver ninguno de los nombres si la base es inválida
                for nombre in nombres_importados:
                     nombre_original = f"{'.' * nivel_relativo}{modulo_base}.{nombre}" if modulo_base else f"{'.' * nivel_relativo}{nombre}"
                     rutas_resueltas.append((nombre_original, None))
                return rutas_resueltas
            directorio_base_rel = parent_dir if parent_dir else ''
    # Para imports absolutos (nivel 0), el directorio base relativo es la raíz ('')
    # ---------------------------------------------------------

    # --- Lógica Principal de Resolución ---
    # 1. Si es import absoluto de algo tipo 'os' o 'mi_app.utils' (modulo_base tiene valor)
    if nivel_relativo == 0 and modulo_base:
        partes_modulo = modulo_base.split('.')
        ruta_tentativa_base = os.path.join(*partes_modulo)
        ruta_base_norm = normalizar_ruta(ruta_tentativa_base)
        ruta_encontrada, _ = _intentar_ruta_modulo(ruta_base_norm, archivos_proyecto)
        # Todos los nombres importados dependen de este módulo base
        for nombre in nombres_importados:
             nombre_original = f"{modulo_base}.{nombre}" if nombre != '*' else modulo_base
             rutas_resueltas.append((nombre_original, ruta_encontrada)) # Puede ser None si no se encontró internamente
        logger.debug(f"  Absoluto: Base='{ruta_base_norm}', RutaEncontrada='{ruta_encontrada}' -> {rutas_resueltas}")

    # 2. Si es import relativo tipo 'from .modulo import a' o 'from ..config import b' (modulo_base tiene valor)
    elif nivel_relativo > 0 and modulo_base:
        partes_modulo = modulo_base.split('.')
        ruta_tentativa_base = os.path.join(directorio_base_rel, *partes_modulo) if directorio_base_rel else os.path.join(*partes_modulo)
        ruta_base_norm = normalizar_ruta(ruta_tentativa_base)
        ruta_encontrada, _ = _intentar_ruta_modulo(ruta_base_norm, archivos_proyecto)
        # Todos los nombres importados dependen de este módulo base relativo
        for nombre in nombres_importados:
            nombre_original = f"{'.' * nivel_relativo}{modulo_base}.{nombre}" if nombre != '*' else f"{'.' * nivel_relativo}{modulo_base}"
            rutas_resueltas.append((nombre_original, ruta_encontrada))
        logger.debug(f"  Relativo con Mod: Base='{ruta_base_norm}', RutaEncontrada='{ruta_encontrada}' -> {rutas_resueltas}")

    # 3. Si es import relativo tipo 'from . import a, b' (modulo_base es '', nivel > 0)
    elif nivel_relativo > 0 and not modulo_base:
        # ¡Aquí necesitamos resolver CADA nombre_importado relativo al directorio_base_rel!
        for nombre in nombres_importados:
            if nombre == '*': # 'from . import *' es difícil de resolver estáticamente
                 logger.warning(f"No se puede resolver 'from . import *' en {ruta_archivo_actual_rel}")
                 rutas_resueltas.append((f"{'.' * nivel_relativo}*", None))
                 continue
            ruta_tentativa_nombre = os.path.join(directorio_base_rel, nombre) if directorio_base_rel else nombre
            ruta_nombre_norm = normalizar_ruta(ruta_tentativa_nombre)
            ruta_encontrada, _ = _intentar_ruta_modulo(ruta_nombre_norm, archivos_proyecto)
            nombre_original = f"{'.' * nivel_relativo}{nombre}"
            rutas_resueltas.append((nombre_original, ruta_encontrada))
        logger.debug(f"  Relativo sin Mod: BaseDir='{directorio_base_rel}', Resoluciones='{rutas_resueltas}'")

    # 4. Caso no esperado (debería cubrir todos los imports/from válidos)
    else:
        logger.error(f"Caso de importación no manejado: Mod='{modulo_base}', Nivel={nivel_relativo}, Nombres={nombres_importados}")
        for nombre in nombres_importados:
            rutas_resueltas.append((f"{modulo_base}.{nombre}" if modulo_base else nombre, None))

    return rutas_resueltas

# --- es_stdlib y resolver_ruta_referencia sin cambios ---
def es_stdlib(nombre_modulo: str) -> bool:
    primer_componente = nombre_modulo.split('.')[0]
    return primer_componente in STDLIBS_COMUNES

def resolver_ruta_referencia(ruta_referencia: str, ruta_archivo_origen_rel: str) -> Tuple[str, Optional[str]]:
    ref = ruta_referencia.strip(); logger.debug(f"Resolviendo Referencia Web/Genérica: Ref='{ref}', Origen='{ruta_archivo_origen_rel}'");
    if not ref: return 'desconocida', None
    try:
        parsed_url = urlparse(ref);
        if parsed_url.scheme in ('http', 'https', 'ftp', 'ftps', 'data'): logger.debug("  -> Tipo: url"); return 'url', ref
    except ValueError: pass
    if not any(c in ref for c in './\\'): logger.debug("  -> Tipo: externa (sin separadores)"); return 'externa', ref
    ruta_resuelta_abs: Optional[str] = None; tipo_ruta = 'desconocida'
    dir_origen = os.path.dirname(ruta_archivo_origen_rel);
    if not dir_origen and ruta_archivo_origen_rel: dir_origen = '.'
    elif not dir_origen and not ruta_archivo_origen_rel: dir_origen = '.'
    if ref.startswith('/'): tipo_ruta = 'absoluta'; ruta_resuelta_abs = normalizar_ruta(ref[1:])
    elif ref.startswith('.'): tipo_ruta = 'relativa'; ruta_combinada = os.path.join(dir_origen, ref); ruta_resuelta_abs = normalizar_ruta(ruta_combinada)
    else: tipo_ruta = 'relativa'; ruta_combinada = os.path.join(dir_origen, ref); ruta_resuelta_abs = normalizar_ruta(ruta_combinada)
    if ruta_resuelta_abs: ruta_resuelta_abs = ruta_resuelta_abs.split('?')[0].split('#')[0]
    logger.debug(f"  -> Tipo: {tipo_ruta}, Ruta Resuelta (pre-check): '{ruta_resuelta_abs}'")
    return tipo_ruta, ruta_resuelta_abs