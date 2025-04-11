# proyscan/core.py
import os
import json
import logging # Importar logging
from typing import List, Set, Dict, Any, Optional

# ... (otras importaciones sin cambios) ...
from .config import (
    ARCHIVO_IGNORAR, ARCHIVO_ESTRUCTURA, ARCHIVO_CONTENIDO,
    EXTENSIONES_BINARIAS, ANALIZAR_DEPENDENCIAS
)
from .ignore_handler import cargar_patrones_ignorar, debe_ignorar
from .utils.file_utils import leer_lineas_texto
from .utils.path_utils import obtener_lenguaje_extension, normalizar_ruta
from .tree_generator import generar_arbol_texto
from .dependency_analysis.analyzer import analizar_dependencias
from .models import FileObject, Metadata, OutputJson

# Obtener un logger para este módulo
logger = logging.getLogger(__name__) # Usa 'proyscan.core'

# --- Actualizar firma y añadir configuración de logging ---
def ejecutar_escaneo(
    directorio_objetivo: str,
    nombre_script_ignorar: Optional[str],
    directorio_salida_escaneo: str,
    debug_mode: bool # Nuevo parámetro
):
    """
    Función principal que ejecuta todo el proceso de escaneo y generación.
    """
    # --- Configurar Logging Global basado en modo debug ---
    log_level = logging.DEBUG if debug_mode else logging.INFO
    log_format = '%(asctime)s - %(name)-25s - %(levelname)-8s - %(message)s'
    # Reconfigurar logging (basicConfig solo funciona bien la primera vez)
    # Forzar reconfiguración si ya existe un handler (útil si se llama varias veces)
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(level=log_level, format=log_format) # Configura el logger raíz
    # ----------------------------------------------------

    logger.info(f"Iniciando escaneo en: {directorio_objetivo}")
    logger.info(f"Directorio de salida para este escaneo: {directorio_salida_escaneo}")
    if debug_mode: logger.debug("Modo Debug HABILITADO.")

    # --- Carga de .ignore (usar logger) ---
    ruta_ignore = os.path.join(directorio_objetivo, ARCHIVO_IGNORAR)
    # La función cargar_patrones_ignorar ya usa print, la modificaremos
    patrones_ignorar = cargar_patrones_ignorar(ruta_ignore) # Modificar esta función luego

    lista_final_archivos: List[FileObject] = []
    items_ignorados_arbol: Set[str] = set()
    archivos_del_proyecto: Set[str] = set()

    # --- Fase 1 (usar logger) ---
    logger.info("Fase 1: Identificando archivos del proyecto...")
    # ... (lógica de os.walk sin cambios) ...
    for raiz, directorios, archivos in os.walk(directorio_objetivo, topdown=True):
        raiz_relativa = os.path.relpath(raiz, directorio_objetivo)
        if raiz == directorio_objetivo: raiz_relativa = '.'
        logger.debug(f"Escaneando directorio: {raiz_relativa}") # DEBUG
        # Filtrar directorios
        for i in range(len(directorios) - 1, -1, -1):
            nombre_dir = directorios[i]
            ruta_rel_dir = os.path.relpath(os.path.join(raiz, nombre_dir), directorio_objetivo)
            ignorar_dir, razon_dir = debe_ignorar(ruta_rel_dir, True, patrones_ignorar, nombre_script_ignorar)
            if ignorar_dir:
                ruta_norm_dir = normalizar_ruta(ruta_rel_dir) + '/'
                logger.debug(f"Ignorando Directorio: {ruta_norm_dir} (Razón: {razon_dir})") # DEBUG
                items_ignorados_arbol.add(ruta_norm_dir)
                del directorios[i]
        # Registrar archivos
        for nombre_archivo in archivos:
            ruta_completa = os.path.join(raiz, nombre_archivo)
            try:
                 # --- Calcular ruta relativa ---
                 ruta_rel_archivo = os.path.relpath(ruta_completa, directorio_objetivo)
                 logger.debug(f"  Archivo encontrado: '{ruta_rel_archivo}'") # NUEVO DEBUG

                 # --- Llamar a debe_ignorar ---
                 ignorar_archivo, razon_archivo = debe_ignorar(ruta_rel_archivo, False, patrones_ignorar, nombre_script_ignorar)
                 ruta_norm = normalizar_ruta(ruta_rel_archivo)

                 if not ignorar_archivo:
                     if ruta_norm != '.':
                          archivos_del_proyecto.add(ruta_norm)
                          # --- Log de qué se añade ---
                          logger.debug(f"    -> Añadido a archivos_del_proyecto: '{ruta_norm}'") # NUEVO DEBUG
                 else:
                     if ruta_norm != '.':
                          # Log existente
                          logger.debug(f"    -> Ignorando Archivo (no se añade a procesar): {ruta_norm} (Razón: {razon_archivo})")
                          items_ignorados_arbol.add(ruta_norm)
            except Exception as e_relpath:
                 # Error calculando ruta relativa (raro pero posible)
                 logger.error(f"Error calculando ruta relativa para {ruta_completa}: {e_relpath}")

    logger.info(f"Fase 1: {len(archivos_del_proyecto)} archivos identificados para procesamiento.")
    logger.debug(f"Archivos a procesar (set): {archivos_del_proyecto}") # NUEVO DEBUG
    logger.debug(f"Items a ignorar en árbol (set): {items_ignorados_arbol}") # NUEVO DEBUG
    # --- Fase 2 (usar logger) ---
    logger.info("Fase 2: Procesando archivos y extrayendo información...")
    for ruta_relativa_norm in sorted(list(archivos_del_proyecto)):
        ruta_completa = os.path.join(directorio_objetivo, ruta_relativa_norm.replace('/', os.sep))
        logger.info(f"  - Procesando: {ruta_relativa_norm}") # INFO es suficiente aquí

        metadata: Metadata = { # ... (inicialización igual) ...
            "path": ruta_relativa_norm,"size_bytes": None, "status": "unknown", "encoding": None,
            "language": None, "line_count": None, "dependencias": None }
        file_object: FileObject = { # ... (inicialización igual) ...
            "metadata": metadata, "content_lines": None, "error_message": None }

        try:
            # ... (lógica de obtener tamaño, lenguaje, etc. igual) ...
            tamano_archivo = os.path.getsize(ruta_completa)
            metadata["size_bytes"] = tamano_archivo
            lenguaje = obtener_lenguaje_extension(ruta_relativa_norm)
            metadata["language"] = lenguaje
            extension = os.path.splitext(ruta_relativa_norm)[1]

            if extension.lower() in EXTENSIONES_BINARIAS:
                logger.debug(f"      * Binario por extensión ({extension})") # DEBUG
                metadata["status"] = "binary"
                file_object["error_message"] = f"Contenido omitido (extensión binaria: {extension})"
            else:
                # ... (llamada a leer_lineas_texto igual) ...
                estado, codificacion, lineas_o_error = leer_lineas_texto(ruta_completa, tamano_archivo)
                metadata["status"] = estado
                metadata["encoding"] = codificacion

                if estado == "ok":
                    lineas_contenido = lineas_o_error
                    file_object["content_lines"] = lineas_contenido
                    metadata["line_count"] = len(lineas_contenido)

                    if ANALIZAR_DEPENDENCIAS and lineas_contenido is not None:
                         # La función analizar_dependencias y sus subparsers usarán sus propios loggers
                         lista_dependencias = analizar_dependencias(
                             lineas_contenido, lenguaje, ruta_relativa_norm,
                             archivos_del_proyecto, directorio_objetivo
                         )
                         metadata["dependencias"] = lista_dependencias
                elif estado in ["read_error", "too_large"]:
                     # Usar logger.warning para advertencias visibles
                     logger.warning(f"      * Estado: {estado} en {ruta_relativa_norm} - {lineas_o_error}")
                     file_object["error_message"] = lineas_o_error


        except OSError as e:
             # Usar logger.error para errores de acceso
             logger.error(f"      * Error de acceso/lectura en {ruta_relativa_norm}: {e}")
             metadata["status"] = "access_error"
             file_object["error_message"] = str(e)
        except Exception as e:
             # Usar logger.exception para errores inesperados (incluye traceback)
             logger.exception(f"      * Error inesperado procesando {ruta_relativa_norm}")
             metadata["status"] = "processing_error"
             file_object["error_message"] = str(e) # El traceback se verá en la consola/log

        lista_final_archivos.append(file_object)

    # --- Fase 3 (usar logger) ---
    logger.info("Fase 3: Generando archivos de salida...")
    ruta_salida_estructura = os.path.join(directorio_salida_escaneo, ARCHIVO_ESTRUCTURA)
    ruta_salida_contenido = os.path.join(directorio_salida_escaneo, ARCHIVO_CONTENIDO)

    # 1. Archivo de Estructura
    try:
        logger.info(f"Generando {ARCHIVO_ESTRUCTURA}...")
        salida_arbol = generar_arbol_texto(directorio_objetivo, items_ignorados_arbol)
        with open(ruta_salida_estructura, 'w', encoding='utf-8') as f: f.write(salida_arbol)
        logger.info(f"Estructura guardada en: {ruta_salida_estructura}")
    except Exception as e:
        logger.exception(f"Error al generar {ARCHIVO_ESTRUCTURA}") # logger.exception incluye traceback

    # 2. Archivo JSON
    datos_json_final: OutputJson = {"files": lista_final_archivos}
    try:
        logger.info(f"Generando {ARCHIVO_CONTENIDO}...")
        with open(ruta_salida_contenido, 'w', encoding='utf-8') as f:
            json.dump(datos_json_final, f, ensure_ascii=False, indent=4, default=str)
        logger.info(f"Archivo JSON guardado en: {ruta_salida_contenido}")
    except Exception as e:
        logger.exception(f"Error al escribir {ARCHIVO_CONTENIDO}")

    logger.info("¡Proceso completado!")