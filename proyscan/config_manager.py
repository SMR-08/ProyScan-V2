# proyscan/config_manager.py
import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__) # Usa 'proyscan.config_manager'

# Determinar la ruta del archivo de configuración
# Usar el directorio home del usuario es lo más estándar
CONFIG_DIR_NAME = ".proyscan"
CONFIG_FILE_NAME = "config.json"
DEFAULT_OUTPUT_DIR_NAME = "ProyScan_Resultados" # Nombre de la carpeta por defecto

def obtener_ruta_config() -> str:
    """Obtiene la ruta completa al archivo de configuración."""
    home_dir = os.path.expanduser("~")
    config_dir = os.path.join(home_dir, CONFIG_DIR_NAME)
    return os.path.join(config_dir, CONFIG_FILE_NAME)

def obtener_ruta_salida_predeterminada_global() -> str:
    """Obtiene la ruta al directorio de salida predeterminado global."""
    # Por simplicidad, lo ponemos dentro del mismo dir de config .proyscan
    # Alternativa: podría ser un directorio configurable o './ProyScan_Resultados'
    home_dir = os.path.expanduser("~")
    config_dir = os.path.join(home_dir, CONFIG_DIR_NAME)
    return os.path.join(config_dir, DEFAULT_OUTPUT_DIR_NAME)


def cargar_config() -> Dict[str, Any]:
    """Carga la configuración desde el archivo JSON."""
    ruta_config = obtener_ruta_config()
    config = {}
    if os.path.exists(ruta_config):
        try:
            with open(ruta_config, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.debug(f"Configuración cargada desde: {ruta_config}")
        except json.JSONDecodeError:
            logger.error(f"Error al decodificar el archivo de configuración: {ruta_config}. Se usará configuración vacía.")
        except Exception as e:
            logger.error(f"Error inesperado al cargar la configuración desde {ruta_config}: {e}", exc_info=True)
    else:
        logger.debug(f"Archivo de configuración no encontrado en {ruta_config}. Se creará uno nuevo si se guarda.")

    # Asegurar valores predeterminados si no existen en el archivo cargado
    # Usamos un directorio global predeterminado ahora
    # config.setdefault("default_output_dir", None) # Ya no usamos None, sino ruta global
    config.setdefault("last_target_dir", None)
    config.setdefault("default_debug_mode", False)
    return config

def guardar_config(config: Dict[str, Any]):
    """Guarda la configuración en el archivo JSON."""
    ruta_config = obtener_ruta_config()
    config_dir = os.path.dirname(ruta_config)

    try:
        # Asegurar que el directorio de configuración exista
        os.makedirs(config_dir, exist_ok=True)
        with open(ruta_config, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
        logger.debug(f"Configuración guardada en: {ruta_config}")
    except Exception as e:
        logger.error(f"Error al guardar la configuración en {ruta_config}: {e}", exc_info=True)