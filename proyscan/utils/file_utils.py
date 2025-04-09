# proyscan/utils/file_utils.py
import codecs
import chardet
import logging # Importar
from typing import Tuple, List, Optional

from ..config import MAX_TAMANO_BYTES_TEXTO, MAX_TAMANO_MB_TEXTO

# Obtener logger
logger = logging.getLogger(__name__) # Usa 'proyscan.utils.file_utils'

ReadResult = Tuple[str, Optional[str], Optional[List[str]] | str]

def leer_lineas_texto(ruta_completa: str, tamano_bytes: int) -> ReadResult:
    """
    Intenta leer el contenido como texto y devuelve lista de líneas.
    """
    logger.debug(f"Intentando leer archivo: {ruta_completa} (Tamaño: {tamano_bytes} bytes)") # DEBUG
    if tamano_bytes == 0:
        logger.debug("Archivo vacío.") # DEBUG
        return "ok", "empty", []
    if tamano_bytes > MAX_TAMANO_BYTES_TEXTO:
        msg = f"Tamaño ({tamano_bytes / 1024 / 1024:.2f} MB) excede límite ({MAX_TAMANO_MB_TEXTO} MB)"
        logger.warning(f"{msg} en archivo {ruta_completa}") # WARNING
        return "too_large", None, msg

    codificacion_detectada: Optional[str] = None
    mensaje_error: Optional[str] = None

    # Detección de codificación
    try:
        with open(ruta_completa, 'rb') as fb:
            fragmento = fb.read(min(tamano_bytes, 64 * 1024))
            resultado = chardet.detect(fragmento)
            codificacion_detectada = resultado['encoding']
            confianza = resultado['confidence']
            logger.debug(f"Chardet detectó: {codificacion_detectada} (Confianza: {confianza:.2f})") # DEBUG
            if codificacion_detectada is None or confianza < 0.6:
                logger.debug("Confianza baja o sin detección, forzando fallback.") # DEBUG
                codificacion_detectada = None
    except Exception as e:
        mensaje_error = f"Error detectando codificación: {e}"
        logger.warning(f"{mensaje_error} en archivo {ruta_completa}") # WARNING

    # Lista de codificaciones a intentar
    codificaciones_a_probar = ([codificacion_detectada] if codificacion_detectada else []) + ['utf-8', 'cp1252', 'latin-1']
    codificaciones_unicas: List[str] = []
    vistas = set()
    for enc in codificaciones_a_probar:
        if enc and enc not in vistas:
            codificaciones_unicas.append(enc)
            vistas.add(enc)
    logger.debug(f"Codificaciones a intentar: {codificaciones_unicas}") # DEBUG

    lectura_exitosa = False
    codificacion_usada: Optional[str] = None
    contenido_completo: Optional[str] = None

    # Intento de lectura
    for enc in codificaciones_unicas:
        logger.debug(f"Intentando leer con codificación: {enc}") # DEBUG
        try:
            effective_enc = 'utf-8-sig' if enc == 'utf-8' else enc
            with codecs.open(ruta_completa, 'r', encoding=effective_enc, errors='strict') as f:
                contenido_completo = f.read()
            logger.debug(f"Lectura exitosa con {enc}") # DEBUG
            lectura_exitosa = True
            codificacion_usada = enc
            mensaje_error = None
            break
        except UnicodeDecodeError:
            logger.debug(f"Fallo de decodificación (UnicodeDecodeError) con {enc}") # DEBUG
            mensaje_error = f"Fallo al decodificar con {', '.join(codificaciones_unicas)}"
            continue
        except Exception as e:
            mensaje_error = f"Error leyendo archivo: {e}"
            # Usar logger.error para errores de lectura, podría ser importante
            logger.error(f"Error de lectura con {enc} en {ruta_completa}: {e}", exc_info=False) # No necesitamos traceback aquí usualmente
            lectura_exitosa = False
            break

    # Procesamiento del resultado
    if lectura_exitosa and contenido_completo is not None:
        if '\x00' in contenido_completo[:1024]:
             msg_bin = "Archivo decodificado pero contiene bytes nulos, probablemente binario."
             logger.warning(f"{msg_bin} en archivo {ruta_completa}") # WARNING
             return "read_error", codificacion_usada, msg_bin
        lineas = contenido_completo.splitlines()
        logger.debug(f"Lectura y división en líneas completada ({len(lineas)} líneas).") # DEBUG
        return "ok", codificacion_usada, lineas
    else:
        error_final = mensaje_error if mensaje_error else "Error desconocido durante la lectura"
        logger.warning(f"Lectura final fallida para {ruta_completa}. Error: {error_final}") # WARNING
        return "read_error", None, error_final