# proyscan.py
import sys
import os
import argparse
import string
import random
import logging # Importar logging aquí también

# Importar la función principal
try:
    from proyscan.core import ejecutar_escaneo
except ImportError as e:
    # ... (Manejo de error de importación sin cambios) ...
    current_dir_for_import = os.path.dirname(os.path.abspath(__file__))
    if current_dir_for_import not in sys.path:
         sys.path.insert(0, current_dir_for_import)
    try:
        from proyscan.core import ejecutar_escaneo
    except ImportError:
        print("Error: No se pudo importar el paquete 'proyscan'.", file=sys.stderr)
        print("Asegúrate de que el paquete 'proyscan' está accesible desde:", current_dir_for_import, file=sys.stderr)
        print(f"Detalle del error: {e}", file=sys.stderr)
        sys.exit(1)


def verificar_dependencias():
    """Verifica dependencias externas."""
    try:
        import chardet
    except ImportError:
        print("ERROR: Dependencia externa 'chardet' no encontrada.", file=sys.stderr)
        print("Instala las dependencias: pip install -r requirements.txt", file=sys.stderr)
        sys.exit(1)

def generar_id_aleatorio(longitud=6):
    """Genera ID aleatorio."""
    caracteres = string.ascii_letters
    return ''.join(random.choice(caracteres) for _ in range(longitud))

def main():
    # Configurar un logger básico inicial para mensajes ANTES de parsear args
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    logger_main = logging.getLogger('proyscan.main') # Logger específico para este script
    logger_main.info("--- ProyScan ---")

    verificar_dependencias()

    # --- Configurar Argument Parser ---
    parser = argparse.ArgumentParser(
        description="Escanea un directorio para generar estructura y contenido en JSON.",
        epilog="Ejemplo: python proyscan.py /ruta/proyecto -o /ruta/salida --debug"
    )
    parser.add_argument(
        "target_directory",
        metavar="DIRECTORIO_OBJETIVO", type=str,
        help="Ruta al directorio que se desea escanear."
    )
    parser.add_argument(
        "-o", "--output", metavar="DIRECTORIO_SALIDA", type=str, default=None,
        help="Directorio donde guardar resultados (def: ProyScan_Resultados en dir. actual)."
    )
    # --- Argumento Debug ---
    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Habilitar salida de depuración detallada (nivel DEBUG)."
    )

    args = parser.parse_args()
    debug_mode_enabled = args.debug # Guardar el estado del flag debug

    # --- Validar Directorio Objetivo ---
    target_dir = args.target_directory
    if not os.path.exists(target_dir):
        logger_main.error(f"El directorio objetivo no existe: {target_dir}")
        sys.exit(1)
    if not os.path.isdir(target_dir):
        logger_main.error(f"La ruta especificada no es un directorio: {target_dir}")
        sys.exit(1)
    target_dir_abs = os.path.abspath(target_dir)
    nombre_base_proyecto = os.path.basename(target_dir_abs)
    logger_main.info(f"Directorio objetivo a escanear: {target_dir_abs}")

    # --- Determinar y Crear Directorio de Salida ---
    if args.output:
        output_base_dir = os.path.abspath(args.output)
        logger_main.info(f"Directorio base de salida especificado: {output_base_dir}")
    else:
        script_execution_dir = os.getcwd()
        output_base_dir = os.path.join(script_execution_dir, "ProyScan_Resultados")
        logger_main.info(f"Usando directorio de salida predeterminado: {output_base_dir}")

    try:
        os.makedirs(output_base_dir, exist_ok=True)
    except OSError as e:
        logger_main.error(f"No se pudo crear el directorio base de salida {output_base_dir}: {e}")
        sys.exit(1)

    id_escaneo = generar_id_aleatorio()
    nombre_subdir_escaneo = f"{nombre_base_proyecto}-{id_escaneo}"
    output_dir_escaneo_actual = os.path.join(output_base_dir, nombre_subdir_escaneo)

    try:
        os.makedirs(output_dir_escaneo_actual)
        logger_main.info(f"Resultados se guardarán en: {output_dir_escaneo_actual}")
    except OSError as e:
        logger_main.error(f"No se pudo crear el subdirectorio de escaneo {output_dir_escaneo_actual}: {e}")
        sys.exit(1)

    # --- Ejecutar Escaneo ---
    script_name = os.path.basename(__file__)
    try:
        # Pasar el flag debug a la función principal del core
        ejecutar_escaneo(target_dir_abs, script_name, output_dir_escaneo_actual, debug_mode_enabled)
    except Exception as e:
        logger_main.critical("ERROR INESPERADO DURANTE LA EJECUCIÓN:", exc_info=True) # exc_info=True añade traceback
        sys.exit(1)

if __name__ == "__main__":
    main()