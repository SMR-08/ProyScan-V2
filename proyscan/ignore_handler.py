# proyscan/ignore_handler.py
import os
from typing import Set, Tuple, Optional
from .config import ARCHIVO_IGNORAR, ARCHIVO_ESTRUCTURA, ARCHIVO_CONTENIDO # Import relativo

def cargar_patrones_ignorar(ruta_archivo_ignore: str) -> Set[str]:
    """Carga los patrones normalizados desde el archivo .ignore."""
    patrones: Set[str] = set()
    if os.path.exists(ruta_archivo_ignore):
        print(f"Cargando patrones de exclusión desde {os.path.basename(ruta_archivo_ignore)}...")
        try:
            with open(ruta_archivo_ignore, 'r', encoding='utf-8') as f:
                for linea in f:
                    linea_limpia = linea.strip()
                    if linea_limpia and not linea_limpia.startswith('#'):
                        es_patron_dir = linea_limpia.endswith('/')
                        patron_normalizado = linea_limpia.strip('/')
                        if es_patron_dir: patron_normalizado += '/'
                        patrones.add(patron_normalizado)
                        # Quitar el print detallado para evitar verbosidad excesiva
                        # print(f"  - Ignorando patrón: {linea_limpia} (Normalizado: {patron_normalizado})")
        except Exception as e:
            print(f"Advertencia: No se pudo leer {os.path.basename(ruta_archivo_ignore)}. Error: {e}")
    else:
        print(f"Advertencia: No se encontró {os.path.basename(ruta_archivo_ignore)}. No se excluirá nada automáticamente.")
    # print("-" * 20) # Opcional: separador visual
    return patrones

def debe_ignorar(ruta_relativa: str, es_directorio: bool, patrones: Set[str], nombre_script_principal: Optional[str]) -> Tuple[bool, Optional[str]]:
    """Comprueba si la ruta relativa coincide con algún patrón de ignorar."""
    ruta_normalizada = os.path.normpath(ruta_relativa).replace(os.sep, '/')
    if ruta_normalizada == '.': ruta_normalizada = '' # Evitar '.' como ruta

    nombre_base = os.path.basename(ruta_normalizada) if ruta_normalizada else ''

    # Ignorar archivos propios del script y salida
    if nombre_script_principal and nombre_base == nombre_script_principal: return True, "script"
    if nombre_base == ARCHIVO_ESTRUCTURA: return True, "salida_estructura"
    if nombre_base == ARCHIVO_CONTENIDO: return True, "salida_contenido"
    if nombre_base == ARCHIVO_IGNORAR: return True, "archivo_ignorar"

    # Preparar ruta para comparación
    ruta_comparacion = ruta_normalizada
    # Añadir '/' a directorios para comparación si no es la raíz y no la tiene ya
    if es_directorio and ruta_normalizada and not ruta_normalizada.endswith('/'):
        ruta_comparacion += '/'

    # Comprobar contra los patrones
    for patron in patrones:
        es_patron_dir = patron.endswith('/')
        base_patron = patron.rstrip('/')

        # 1. Coincidencia exacta
        if ruta_comparacion == patron:
            return True, f"coincidencia_exacta ({patron})"

        # 2. Coincidencia de nombre base (solo si el patrón no tiene '/')
        if '/' not in base_patron:
            nombre_base_actual = os.path.basename(ruta_normalizada) # Obtener solo el nombre final
            if nombre_base_actual: # Asegurar que no sea vacío (caso raíz)
                if es_patron_dir and es_directorio and nombre_base_actual == base_patron:
                    return True, f"coincidencia_base_dir ({patron})"
                if not es_patron_dir and not es_directorio and nombre_base_actual == base_patron:
                    return True, f"coincidencia_base_archivo ({patron})"

        # 3. Coincidencia de extensión (solo archivos, patrón sin '/')
        if not es_directorio and not es_patron_dir and '/' not in patron:
            if patron.startswith('.') and ruta_normalizada.endswith(patron):
                 return True, f"coincidencia_extension ({patron})"
            if patron.startswith('*.'):
                extension_patron = patron[1:]
                if ruta_normalizada.endswith(extension_patron):
                    return True, f"coincidencia_comodin_ext ({patron})"

        # 4. Coincidencia de directorio padre (patrón termina en '/')
        # Asegurarse de que ruta_comparacion no sea solo '/' para evitar matches accidentales
        if es_patron_dir and ruta_comparacion.startswith(patron) and len(ruta_comparacion) > len(patron):
             return True, f"coincidencia_dir_padre ({patron})"

    return False, None # No ignorar