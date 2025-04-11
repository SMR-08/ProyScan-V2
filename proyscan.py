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
    from proyscan.core import ejecutar_escaneo
    from proyscan.cli import run_interactive_cli # Importar la función de la CLI
except ImportError as e:
    current_dir_for_import = os.path.dirname(os.path.abspath(__file__))
    if current_dir_for_import not in sys.path:
         sys.path.insert(0, current_dir_for_import)
    try:
        from proyscan.core import ejecutar_escaneo
        from proyscan.cli import run_interactive_cli
        # from proyscan.config_manager import cargar_config
    except ImportError:
        print("Error: No se pudo importar el paquete 'proyscan'.", file=sys.stderr)
        print("Asegúrate de que el paquete 'proyscan' está accesible desde:", current_dir_for_import, file=sys.stderr)
        print(f"Detalle del error: {e}", file=sys.stderr)
        sys.exit(1)

def verificar_dependencias():
    """Verifica dependencias externas."""
    try:
        import chardet
        import rich # Verificar nuevas dependencias
        import questionary
    except ImportError as e_dep:
        missing_dep = str(e_dep).split("'")[-2] # Extraer nombre del módulo que falta
        print(f"ERROR: Dependencia externa '{missing_dep}' no encontrada.", file=sys.stderr)
        print("Por favor, instala las dependencias ejecutando:", file=sys.stderr)
        print("pip install -r requirements.txt", file=sys.stderr)
        sys.exit(1)

def generar_id_aleatorio(longitud=6):
    """Genera ID aleatorio."""
    caracteres = string.ascii_letters
    return ''.join(random.choice(caracteres) for _ in range(longitud))

def main():
    # Configurar un logger básico inicial para mensajes ANTES de parsear args
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    logger_launcher = logging.getLogger('proyscan.launcher')

    verificar_dependencias()

    # --- Configurar Argument Parser ---
    parser = argparse.ArgumentParser(
        description="ProyScan: Escanea proyectos y analiza dependencias.",
        add_help=False # Desactivar ayuda automática para manejarla nosotros (o en CLI)
    )
    # Argumento posicional OPCIONAL ahora (si se da, entra en modo no interactivo)
    parser.add_argument(
        "target_directory",
        metavar="DIRECTORIO_OBJETIVO",
        type=str,
        nargs='?', # Hace que sea opcional (0 o 1 argumento)
        default=None,
        help="Ruta al directorio a escanear (activa modo no interactivo)."
    )
    parser.add_argument(
        "-o", "--output", metavar="DIRECTORIO_SALIDA", type=str, default=None,
        help="Directorio de salida (solo modo no interactivo)."
    )
    parser.add_argument(
        "-d", "--debug", action="store_true",
        help="Habilitar salida de depuración detallada."
    )
    # Argumento de ayuda manual
    parser.add_argument(
         '-h', '--help', action='help', default=argparse.SUPPRESS,
         help='Muestra este mensaje de ayuda y sale.'
    )

    args = parser.parse_args()
    debug_mode_enabled = args.debug # Guardar el estado del flag debug

    if args.target_directory:
        # --- MODO NO INTERACTIVO ---
        logger_launcher.info("Ejecutando en modo no interactivo...")

        target_dir = args.target_directory
        if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
            logger_launcher.error(f"Directorio objetivo inválido: {target_dir}")
            sys.exit(1)
        target_dir_abs = os.path.abspath(target_dir)
        nombre_base_proyecto = os.path.basename(target_dir_abs)

        # Cargar configuración para directorio de salida predeterminado
        # config = cargar_config()
        # default_output_base = config.get("default_output_dir")
        default_output_base = os.path.join(os.getcwd(), "ProyScan_Resultados") # Temporal

        output_base_dir = os.path.abspath(args.output) if args.output else default_output_base

        try:
            os.makedirs(output_base_dir, exist_ok=True)
        except OSError as e:
            logger_launcher.error(f"No se pudo crear directorio base de salida {output_base_dir}: {e}")
            sys.exit(1)

        id_escaneo = generar_id_aleatorio()
        nombre_subdir_escaneo = f"{nombre_base_proyecto}-{id_escaneo}"
        output_dir_escaneo_actual = os.path.join(output_base_dir, nombre_subdir_escaneo)

        try:
            os.makedirs(output_dir_escaneo_actual)
            logger_launcher.info(f"Salida se guardará en: {output_dir_escaneo_actual}")
        except OSError as e:
            logger_launcher.error(f"No se pudo crear subdirectorio de escaneo {output_dir_escaneo_actual}: {e}")
            sys.exit(1)

        script_name = os.path.basename(__file__)
        try:
            # Llamar directamente al core
            ejecutar_escaneo(target_dir_abs, script_name, output_dir_escaneo_actual, debug_mode_enabled)
        except Exception as e:
            logger_launcher.critical("ERROR INESPERADO DURANTE LA EJECUCIÓN:", exc_info=True)
            sys.exit(1)

    else:
        # --- MODO INTERACTIVO ---
        # La configuración de logging se hará DENTRO de ejecutar_escaneo basado en la opción elegida
        logger_launcher.info("Iniciando modo interactivo...")
        # Simplemente llamamos a la función principal de la CLI
        run_interactive_cli()


if __name__ == "__main__":
    main()