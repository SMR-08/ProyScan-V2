# proyscan/utils/file_utils.py
import codecs
import chardet # Asegúrate de que esté en requirements.txt
from typing import Tuple, List, Optional # Para type hints
from ..config import MAX_TAMANO_BYTES_TEXTO, MAX_TAMANO_MB_TEXTO # Import relativo

# Tipo para el retorno: estado, codificación, contenido/error
ReadResult = Tuple[str, Optional[str], Optional[List[str]] | str]

def leer_lineas_texto(ruta_completa: str, tamano_bytes: int) -> ReadResult:
    """
    Intenta leer el contenido como texto y devuelve lista de líneas.
    Retorna: (estado, codificacion, lineas_o_mensaje_error)
    """
    if tamano_bytes == 0:
        return "ok", "empty", []
    if tamano_bytes > MAX_TAMANO_BYTES_TEXTO:
        msg = f"Tamaño ({tamano_bytes / 1024 / 1024:.2f} MB) excede límite ({MAX_TAMANO_MB_TEXTO} MB)"
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
            if codificacion_detectada is None or confianza < 0.6:
                codificacion_detectada = None
    except Exception as e:
        mensaje_error = f"Error detectando codificación: {e}"

    # Lista de codificaciones a intentar
    codificaciones_a_probar = ([codificacion_detectada] if codificacion_detectada else []) + ['utf-8', 'cp1252', 'latin-1']
    codificaciones_unicas: List[str] = []
    vistas = set()
    for enc in codificaciones_a_probar:
        if enc and enc not in vistas:
            codificaciones_unicas.append(enc)
            vistas.add(enc)

    lectura_exitosa = False
    codificacion_usada: Optional[str] = None
    contenido_completo: Optional[str] = None

    # Intento de lectura
    for enc in codificaciones_unicas:
        try:
            # Usamos utf-8-sig para manejar BOM si está presente en utf-8
            effective_enc = 'utf-8-sig' if enc == 'utf-8' else enc
            with codecs.open(ruta_completa, 'r', encoding=effective_enc, errors='strict') as f:
                contenido_completo = f.read()
            lectura_exitosa = True
            codificacion_usada = enc # Reportamos 'utf-8', no 'utf-8-sig'
            mensaje_error = None
            break
        except UnicodeDecodeError:
            mensaje_error = f"Fallo al decodificar con {', '.join(codificaciones_unicas)}"
            continue
        except Exception as e:
            mensaje_error = f"Error leyendo archivo: {e}"
            lectura_exitosa = False
            break

    # Procesamiento del resultado
    if lectura_exitosa and contenido_completo is not None:
        if '\x00' in contenido_completo[:1024]:
             return "read_error", codificacion_usada, "Archivo decodificado pero contiene bytes nulos, probablemente binario."
        lineas = contenido_completo.splitlines()
        return "ok", codificacion_usada, lineas
    else:
        # Asegurarse de que mensaje_error no sea None si la lectura falló
        error_final = mensaje_error if mensaje_error else "Error desconocido durante la lectura"
        return "read_error", None, error_final