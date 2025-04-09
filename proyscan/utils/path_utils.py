# proyscan/utils/path_utils.py
import os
from ..config import MAPA_LENGUAJES, LENGUAJE_DEFECTO # Import relativo dentro del paquete

def obtener_lenguaje_extension(ruta_archivo: str) -> str:
    """Determina el lenguaje/tipo basado en la extensión del archivo."""
    _, extension = os.path.splitext(ruta_archivo)
    if not extension:
        return LENGUAJE_DEFECTO
    ext = extension.lower()
    # El mapa ya tiene las extensiones con punto
    return MAPA_LENGUAJES.get(ext, LENGUAJE_DEFECTO)

def normalizar_ruta(ruta: str) -> str:
    """Normaliza una ruta usando '/' y eliminando redundancias."""
    return os.path.normpath(ruta).replace(os.sep, '/')

# --- Funciones futuras para resolución de dependencias ---
def resolver_ruta_dependencia(ruta_referenciada: str, ruta_archivo_origen: str, dir_proyecto_raiz: str) -> str | None:
    """
    Intenta resolver una ruta referenciada desde un archivo origen.
    Devuelve la ruta normalizada relativa al proyecto raíz, o None si no es resoluble fácilmente.
    (IMPLEMENTACIÓN FUTURA - Placeholder para Fase 1+)
    """
    # Lógica placeholder - esto se implementará en fases posteriores
    print(f"[DEBUG Placeholder] Intentando resolver: '{ruta_referenciada}' desde '{ruta_archivo_origen}'")

    # Manejo básico de rutas relativas (ejemplo muy simple)
    if ruta_referenciada.startswith('.'):
        dir_origen = os.path.dirname(ruta_archivo_origen)
        ruta_absoluta_tentativa = os.path.join(dir_proyecto_raiz, dir_origen, ruta_referenciada)
        ruta_normalizada_abs = os.path.normpath(ruta_absoluta_tentativa)
        # Convertir de nuevo a relativa al proyecto
        ruta_relativa_resuelta = os.path.relpath(ruta_normalizada_abs, dir_proyecto_raiz)
        return normalizar_ruta(ruta_relativa_resuelta)
    # Podría manejar rutas absolutas del proyecto que empiezan sin '/' o '.'
    # Podría identificar URLs o nombres de paquetes (externos)
    # Por ahora, devuelve None para casos no manejados
    return None