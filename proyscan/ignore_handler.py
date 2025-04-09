# proyscan/ignore_handler.py
import os
import logging # Importar logging
from typing import Set, Tuple, Optional
from .config import ARCHIVO_IGNORAR, ARCHIVO_ESTRUCTURA, ARCHIVO_CONTENIDO

# Obtener logger
logger = logging.getLogger(__name__) # Usa 'proyscan.ignore_handler'

def cargar_patrones_ignorar(ruta_archivo_ignore: str) -> Set[str]:
    """Carga los patrones normalizados desde el archivo .ignore."""
    patrones: Set[str] = set()
    if os.path.exists(ruta_archivo_ignore):
        # Usar logger.info para mensajes normales
        logger.info(f"Cargando patrones de exclusión desde {os.path.basename(ruta_archivo_ignore)}...")
        try:
            with open(ruta_archivo_ignore, 'r', encoding='utf-8') as f:
                for linea in f:
                    linea_limpia = linea.strip()
                    if linea_limpia and not linea_limpia.startswith('#'):
                        # ... (lógica de normalización igual) ...
                        es_patron_dir = linea_limpia.endswith('/')
                        patron_normalizado = linea_limpia.strip('/')
                        if es_patron_dir: patron_normalizado += '/'
                        patrones.add(patron_normalizado)
                        # Usar logger.debug para detalles finos
                        logger.debug(f"  - Patrón ignore cargado: '{linea_limpia}' (Normalizado: '{patron_normalizado}')")
        except Exception as e:
             # Usar logger.warning para advertencias
            logger.warning(f"No se pudo leer {os.path.basename(ruta_archivo_ignore)}. Error: {e}")
    else:
         # Usar logger.warning
        logger.warning(f"No se encontró {os.path.basename(ruta_archivo_ignore)}. No se excluirá nada automáticamente.")
    return patrones

def debe_ignorar(ruta_relativa: str, es_directorio: bool, patrones: Set[str], nombre_script_principal: Optional[str]) -> Tuple[bool, Optional[str]]:
    """Comprueba si la ruta relativa coincide con algún patrón de ignorar."""
    ruta_normalizada = os.path.normpath(ruta_relativa).replace(os.sep, '/')
    if ruta_normalizada == '.': ruta_normalizada = ''

    nombre_base = os.path.basename(ruta_normalizada) if ruta_normalizada else ''

    # Logs de DEBUG para ver qué se está comprobando
    logger.debug(f"Comprobando ignorar para: '{ruta_normalizada}' (es_dir={es_directorio})")

    if nombre_script_principal and nombre_base == nombre_script_principal:
        logger.debug(f"Ignorado por ser script principal: '{nombre_base}'")
        return True, "script"
    if nombre_base == ARCHIVO_ESTRUCTURA:
        logger.debug(f"Ignorado por ser archivo de estructura: '{nombre_base}'")
        return True, "salida_estructura"
    if nombre_base == ARCHIVO_CONTENIDO:
        logger.debug(f"Ignorado por ser archivo de contenido: '{nombre_base}'")
        return True, "salida_contenido"
    if nombre_base == ARCHIVO_IGNORAR:
        logger.debug(f"Ignorado por ser archivo ignore: '{nombre_base}'")
        return True, "archivo_ignorar"

    ruta_comparacion = ruta_normalizada
    if es_directorio and ruta_normalizada and not ruta_normalizada.endswith('/'):
        ruta_comparacion += '/'

    for patron in patrones:
        es_patron_dir = patron.endswith('/')
        base_patron = patron.rstrip('/')
        logger.debug(f"  Comparando con patrón: '{patron}'") # DEBUG

        # 1. Coincidencia exacta
        if ruta_comparacion == patron:
            logger.debug(f"    -> Coincidencia exacta!")
            return True, f"coincidencia_exacta ({patron})"

        # 2. Coincidencia de nombre base
        if '/' not in base_patron:
            nombre_base_actual = os.path.basename(ruta_normalizada)
            if nombre_base_actual:
                if es_patron_dir and es_directorio and nombre_base_actual == base_patron:
                    logger.debug(f"    -> Coincidencia nombre base directorio!")
                    return True, f"coincidencia_base_dir ({patron})"
                if not es_patron_dir and not es_directorio and nombre_base_actual == base_patron:
                    logger.debug(f"    -> Coincidencia nombre base archivo!")
                    return True, f"coincidencia_base_archivo ({patron})"

        # 3. Coincidencia de extensión
        if not es_directorio and not es_patron_dir and '/' not in patron:
            if patron.startswith('.') and ruta_normalizada.endswith(patron):
                 logger.debug(f"    -> Coincidencia extensión!")
                 return True, f"coincidencia_extension ({patron})"
            if patron.startswith('*.'):
                extension_patron = patron[1:]
                if ruta_normalizada.endswith(extension_patron):
                    logger.debug(f"    -> Coincidencia extensión comodín!")
                    return True, f"coincidencia_comodin_ext ({patron})"

        # 4. Coincidencia de directorio padre
        if es_patron_dir and ruta_comparacion.startswith(patron) and len(ruta_comparacion) > len(patron):
             logger.debug(f"    -> Coincidencia directorio padre!")
             return True, f"coincidencia_dir_padre ({patron})"

    logger.debug(f"No ignorado: '{ruta_normalizada}'") # DEBUG final si no coincide
    return False, None