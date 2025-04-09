# proyscan/core.py
import os
import json
from typing import List, Set, Dict, Any, Optional

# ... (importaciones sin cambios) ...
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


# --- Actualizar firma de la función ---
def ejecutar_escaneo(
    directorio_objetivo: str,
    nombre_script_ignorar: Optional[str],
    directorio_salida_escaneo: str # Nuevo parámetro
):
    """
    Función principal que ejecuta todo el proceso de escaneo y generación.

    Args:
        directorio_objetivo: Ruta absoluta al directorio que se va a escanear.
        nombre_script_ignorar: Nombre base del script principal a ignorar.
        directorio_salida_escaneo: Ruta absoluta al directorio específico donde
                                    se guardarán los resultados de este escaneo.
    """
    print(f"Iniciando escaneo en: {directorio_objetivo}")
    print(f"Directorio de salida para este escaneo: {directorio_salida_escaneo}")

    # --- Carga de .ignore y Fase 1 (Identificación) sin cambios ---
    ruta_ignore = os.path.join(directorio_objetivo, ARCHIVO_IGNORAR)
    patrones_ignorar = cargar_patrones_ignorar(ruta_ignore)
    # ... (resto de Fase 1 sin cambios, calcula archivos_del_proyecto y items_ignorados_arbol) ...
    lista_final_archivos: List[FileObject] = []
    items_ignorados_arbol: Set[str] = set()
    archivos_del_proyecto: Set[str] = set()
    print("Fase 1: Identificando archivos del proyecto...")
    for raiz, directorios, archivos in os.walk(directorio_objetivo, topdown=True):
        raiz_relativa = os.path.relpath(raiz, directorio_objetivo)
        if raiz == directorio_objetivo: raiz_relativa = '.'
        for i in range(len(directorios) - 1, -1, -1):
            nombre_dir = directorios[i]
            ruta_rel_dir = os.path.relpath(os.path.join(raiz, nombre_dir), directorio_objetivo)
            ignorar_dir, _ = debe_ignorar(ruta_rel_dir, True, patrones_ignorar, nombre_script_ignorar)
            if ignorar_dir:
                items_ignorados_arbol.add(normalizar_ruta(ruta_rel_dir) + '/')
                del directorios[i]
        for nombre_archivo in archivos:
            ruta_rel_archivo = os.path.relpath(os.path.join(raiz, nombre_archivo), directorio_objetivo)
            ignorar_archivo, _ = debe_ignorar(ruta_rel_archivo, False, patrones_ignorar, nombre_script_ignorar)
            ruta_norm = normalizar_ruta(ruta_rel_archivo)
            if not ignorar_archivo:
                if ruta_norm != '.': archivos_del_proyecto.add(ruta_norm)
            else:
                if ruta_norm != '.': items_ignorados_arbol.add(ruta_norm)
    print(f"Fase 1: {len(archivos_del_proyecto)} archivos identificados para procesamiento.")


    # --- Fase 2 (Procesamiento) sin cambios en la lógica interna ---
    print("\nFase 2: Procesando archivos y extrayendo información...")
    for ruta_relativa_norm in sorted(list(archivos_del_proyecto)):
        ruta_completa = os.path.join(directorio_objetivo, ruta_relativa_norm.replace('/', os.sep))
        # ... (toda la lógica de leer, analizar dependencias, etc., sigue igual) ...
        # ... porque opera sobre ruta_completa y ruta_relativa_norm ...
        print(f"  - Procesando: {ruta_relativa_norm}")
        metadata: Metadata = {
             "path": ruta_relativa_norm,
             "size_bytes": None, "status": "unknown", "encoding": None,
             "language": None, "line_count": None, "dependencias": None
        }
        file_object: FileObject = {
             "metadata": metadata, "content_lines": None, "error_message": None
        }
        try:
             tamano_archivo = os.path.getsize(ruta_completa)
             metadata["size_bytes"] = tamano_archivo
             lenguaje = obtener_lenguaje_extension(ruta_relativa_norm)
             metadata["language"] = lenguaje
             extension = os.path.splitext(ruta_relativa_norm)[1]

             if extension.lower() in EXTENSIONES_BINARIAS:
                 metadata["status"] = "binary"
                 file_object["error_message"] = f"Contenido omitido (extensión binaria: {extension})"
             else:
                 estado, codificacion, lineas_o_error = leer_lineas_texto(ruta_completa, tamano_archivo)
                 metadata["status"] = estado
                 metadata["encoding"] = codificacion

                 if estado == "ok":
                     lineas_contenido = lineas_o_error
                     file_object["content_lines"] = lineas_contenido
                     metadata["line_count"] = len(lineas_contenido)
                     if ANALIZAR_DEPENDENCIAS and lineas_contenido is not None:
                          lista_dependencias = analizar_dependencias(
                              lineas_contenido, lenguaje, ruta_relativa_norm,
                              archivos_del_proyecto, directorio_objetivo
                          )
                          metadata["dependencias"] = lista_dependencias
                 elif estado in ["read_error", "too_large"]:
                     file_object["error_message"] = lineas_o_error
                     print(f"      * Advertencia: {estado} - {lineas_o_error}")

        except OSError as e:
             metadata["status"] = "access_error"
             file_object["error_message"] = str(e)
             print(f"      * Error de acceso/lectura: {e}")
        except Exception as e:
             metadata["status"] = "processing_error"
             file_object["error_message"] = str(e)
             print(f"      * Error inesperado procesando {ruta_relativa_norm}: {e}")

        lista_final_archivos.append(file_object)


    # --- Fase 3: Generación de Archivos de Salida (Usando directorio_salida_escaneo) ---
    print("\nFase 3: Generando archivos de salida...")

    # --- Usar el directorio de salida específico ---
    ruta_salida_estructura = os.path.join(directorio_salida_escaneo, ARCHIVO_ESTRUCTURA)
    ruta_salida_contenido = os.path.join(directorio_salida_escaneo, ARCHIVO_CONTENIDO)

    # 1. Archivo de Estructura
    try:
        print(f"Generando {ARCHIVO_ESTRUCTURA}...")
        # Generar árbol basado en el directorio OBJETIVO
        salida_arbol = generar_arbol_texto(directorio_objetivo, items_ignorados_arbol)
        # Guardar en el directorio de SALIDA
        with open(ruta_salida_estructura, 'w', encoding='utf-8') as f:
            f.write(salida_arbol)
        print(f"Estructura guardada en: {ruta_salida_estructura}")
    except Exception as e:
        print(f"Error al generar {ARCHIVO_ESTRUCTURA}: {e}")

    # 2. Archivo JSON
    datos_json_final: OutputJson = {"archivos": lista_final_archivos}
    try:
        print(f"Generando {ARCHIVO_CONTENIDO}...")
        # Guardar en el directorio de SALIDA
        with open(ruta_salida_contenido, 'w', encoding='utf-8') as f:
            json.dump(datos_json_final, f, ensure_ascii=False, indent=4, default=str)
        print(f"Archivo JSON guardado en: {ruta_salida_contenido}")
    except Exception as e:
        print(f"Error al escribir {ARCHIVO_CONTENIDO}: {e}")

    print("\n¡Proceso completado!")