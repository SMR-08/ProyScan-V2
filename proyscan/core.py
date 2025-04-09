# proyscan/core.py
import os
import json
from typing import List, Set, Dict, Any

# Importar módulos del paquete ProyScan
from .config import (
    DIR_PROYECTO, ARCHIVO_IGNORAR, ARCHIVO_ESTRUCTURA, ARCHIVO_CONTENIDO,
    EXTENSIONES_BINARIAS, ANALIZAR_DEPENDENCIAS
)
from .ignore_handler import cargar_patrones_ignorar, debe_ignorar
from .utils.file_utils import leer_lineas_texto
from .utils.path_utils import obtener_lenguaje_extension, normalizar_ruta
from .tree_generator import generar_arbol_texto
# Importar el analizador de dependencias (aunque sea placeholder)
from .dependency_analysis.analyzer import analizar_dependencias
# Importar modelos de datos
from .models import FileObject, Metadata, OutputJson

def ejecutar_escaneo(directorio_raiz: str, nombre_script_principal: str):
    """
    Función principal que ejecuta todo el proceso de escaneo y generación.
    """
    print(f"Iniciando escaneo en: {directorio_raiz}")

    # Cargar patrones a ignorar
    ruta_ignore = os.path.join(directorio_raiz, ARCHIVO_IGNORAR)
    patrones_ignorar = cargar_patrones_ignorar(ruta_ignore)

    lista_final_archivos: List[FileObject] = []
    items_ignorados_arbol: Set[str] = set() # Rutas relativas normalizadas a ignorar en el árbol
    archivos_del_proyecto: Set[str] = set() # Rutas relativas normalizadas de archivos VÁLIDOS

    # --- Primera pasada: Identificar todos los archivos válidos del proyecto ---
    # Esto es necesario para clasificar dependencias internas correctamente
    print("Fase 1: Identificando archivos del proyecto...")
    for raiz, directorios, archivos in os.walk(directorio_raiz, topdown=True):
         # Filtrar directorios ignorados ANTES de descender (eficiencia)
        for i in range(len(directorios) - 1, -1, -1):
            nombre_dir = directorios[i]
            ruta_rel_dir = os.path.relpath(os.path.join(raiz, nombre_dir), directorio_raiz)
            ignorar_dir, _ = debe_ignorar(ruta_rel_dir, True, patrones_ignorar, nombre_script_principal)
            if ignorar_dir:
                # Añadir al set para el árbol (con '/')
                items_ignorados_arbol.add(normalizar_ruta(ruta_rel_dir) + '/')
                del directorios[i]

        # Registrar archivos no ignorados
        for nombre_archivo in archivos:
            ruta_rel_archivo = os.path.relpath(os.path.join(raiz, nombre_archivo), directorio_raiz)
            ignorar_archivo, _ = debe_ignorar(ruta_rel_archivo, False, patrones_ignorar, nombre_script_principal)
            if not ignorar_archivo:
                archivos_del_proyecto.add(normalizar_ruta(ruta_rel_archivo))
            else:
                 items_ignorados_arbol.add(normalizar_ruta(ruta_rel_archivo)) # Añadir ignorados al set del árbol también

    print(f"Fase 1: {len(archivos_del_proyecto)} archivos identificados para procesamiento.")

    # --- Segunda pasada: Procesar cada archivo válido ---
    print("\nFase 2: Procesando archivos y extrayendo información...")
    # Reutilizamos el set 'archivos_del_proyecto' para iterar solo los válidos
    for ruta_relativa_norm in sorted(list(archivos_del_proyecto)):
        ruta_completa = os.path.join(directorio_raiz, ruta_relativa_norm.replace('/', os.sep))
        print(f"  - Procesando: {ruta_relativa_norm}")

        # Crear estructura de datos inicial
        metadata: Metadata = {
            "path": ruta_relativa_norm,
            "size_bytes": None, "status": "unknown", "encoding": None,
            "language": None, "line_count": None, "dependencias": None # Inicializar dependencias
        }
        file_object: FileObject = {
            "metadata": metadata,
            "content_lines": None,
            "error_message": None
        }

        try:
            tamano_archivo = os.path.getsize(ruta_completa)
            metadata["size_bytes"] = tamano_archivo
            extension = os.path.splitext(ruta_relativa_norm)[1]
            lenguaje = obtener_lenguaje_extension(ruta_relativa_norm)
            metadata["language"] = lenguaje

            # Comprobar si es binario por extensión
            if extension.lower() in EXTENSIONES_BINARIAS:
                print(f"      * Binario por extensión ({extension})")
                metadata["status"] = "binary"
                file_object["error_message"] = f"Contenido omitido (extensión binaria: {extension})"
            else:
                # Intentar leer como texto
                estado, codificacion, lineas_o_error = leer_lineas_texto(ruta_completa, tamano_archivo)
                metadata["status"] = estado
                metadata["encoding"] = codificacion

                if estado == "ok":
                    lineas_contenido = lineas_o_error # Sabemos que es List[str]
                    file_object["content_lines"] = lineas_contenido
                    metadata["line_count"] = len(lineas_contenido)
                    # --- Llamada al análisis de dependencias (Fase 1+) ---
                    if ANALIZAR_DEPENDENCIAS and lineas_contenido is not None:
                         # Pasar contenido, lenguaje, ruta, set de archivos, dir raíz
                         lista_dependencias = analizar_dependencias(
                             lineas_contenido,
                             lenguaje,
                             ruta_relativa_norm,
                             archivos_del_proyecto,
                             directorio_raiz
                         )
                         # Incluso si devuelve None o [], lo asignamos
                         metadata["dependencias"] = lista_dependencias
                    # ------------------------------------------------------
                elif estado in ["read_error", "too_large"]:
                    # Sabemos que lineas_o_error es str (mensaje de error)
                    file_object["error_message"] = lineas_o_error
                    print(f"      * Advertencia: {estado} - {lineas_o_error}")
                # Nota: 'access_error' se captura en el except

        except OSError as e:
            print(f"      * Error de acceso/lectura: {e}")
            metadata["status"] = "access_error"
            file_object["error_message"] = str(e)
        except Exception as e:
            # Captura genérica para errores inesperados durante el procesamiento
            print(f"      * Error inesperado procesando {ruta_relativa_norm}: {e}")
            metadata["status"] = "processing_error"
            file_object["error_message"] = str(e)
            # Considerar añadir traceback a los logs si es necesario
            # import traceback
            # file_object["error_message"] += f"\n{traceback.format_exc()}"

        lista_final_archivos.append(file_object)

    # --- Generación de Archivos de Salida ---
    print("\nFase 3: Generando archivos de salida...")

    # 1. Archivo de Estructura
    ruta_salida_estructura = os.path.join(directorio_raiz, ARCHIVO_ESTRUCTURA)
    try:
        print(f"Generando {ARCHIVO_ESTRUCTURA}...")
        salida_arbol = generar_arbol_texto(directorio_raiz, items_ignorados_arbol)
        with open(ruta_salida_estructura, 'w', encoding='utf-8') as f:
            f.write(salida_arbol)
        print(f"Estructura guardada en {ARCHIVO_ESTRUCTURA}")
    except Exception as e:
        print(f"Error al generar {ARCHIVO_ESTRUCTURA}: {e}")

    # 2. Archivo JSON de Contenido/Metadatos
    ruta_salida_contenido = os.path.join(directorio_raiz, ARCHIVO_CONTENIDO)
    datos_json_final: OutputJson = {"archivos": lista_final_archivos}
    try:
        print(f"Generando {ARCHIVO_CONTENIDO}...")
        with open(ruta_salida_contenido, 'w', encoding='utf-8') as f:
            # Usamos default=str por si acaso algún objeto no serializable se cuela,
            # aunque con TypedDicts debería ser seguro.
            json.dump(datos_json_final, f, ensure_ascii=False, indent=4, default=str)
        print(f"Archivo JSON guardado en {ARCHIVO_CONTENIDO}")
    except Exception as e:
        print(f"Error al escribir {ARCHIVO_CONTENIDO}: {e}")

    print("\n¡Proceso completado!")