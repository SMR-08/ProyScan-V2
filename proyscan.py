# proyscan.py
import sys
import os
import argparse
import string # Para generar caracteres aleatorios
import random # Para elegir caracteres aleatorios

# Importar la función principal
try:
    from proyscan.core import ejecutar_escaneo
except ImportError as e:
    current_dir_for_import = os.path.dirname(os.path.abspath(__file__))
    if current_dir_for_import not in sys.path:
         sys.path.insert(0, current_dir_for_import)
    try:
        from proyscan.core import ejecutar_escaneo
    except ImportError:
        print("Error: No se pudo importar el paquete 'proyscan'.", file=sys.stderr)
        # ... (resto del manejo de error de importación) ...
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
    """Genera una cadena aleatoria de letras ASCII."""
    caracteres = string.ascii_letters # a-z, A-Z
    return ''.join(random.choice(caracteres) for _ in range(longitud))

def main():
    print("--- ProyScan ---")
    verificar_dependencias()

    # --- Configurar Argument Parser ---
    parser = argparse.ArgumentParser(
        description="Escanea un directorio para generar estructura y contenido en JSON.",
        epilog="Ejemplo: python proyscan.py /ruta/al/proyecto -o /ruta/salida"
    )
    parser.add_argument(
        "target_directory",
        metavar="DIRECTORIO_OBJETIVO",
        type=str,
        help="Ruta al directorio que se desea escanear."
    )
    # --- Nuevo Argumento Opcional ---
    parser.add_argument(
        "-o", "--output",
        metavar="DIRECTORIO_SALIDA",
        type=str,
        default=None, # El valor por defecto se calculará más adelante
        help="Directorio donde se guardarán los resultados. Si no se especifica, "
             "se creará 'ProyScan_Resultados' en el directorio actual."
    )

    args = parser.parse_args()

    # --- Validar Directorio Objetivo ---
    target_dir = args.target_directory
    if not os.path.exists(target_dir):
        print(f"Error: El directorio objetivo no existe: {target_dir}", file=sys.stderr)
        sys.exit(1)
    if not os.path.isdir(target_dir):
        print(f"Error: La ruta especificada no es un directorio: {target_dir}", file=sys.stderr)
        sys.exit(1)
    target_dir_abs = os.path.abspath(target_dir)
    nombre_base_proyecto = os.path.basename(target_dir_abs) # Nombre de la carpeta escaneada

    # --- Determinar y Crear Directorio de Salida ---
    if args.output:
        # Usar directorio especificado por el usuario
        output_base_dir = os.path.abspath(args.output)
        print(f"Directorio base de salida especificado: {output_base_dir}")
    else:
        # Usar directorio predeterminado ('ProyScan_Resultados' en el directorio actual)
        # Directorio actual donde se ejecuta proyscan.py
        script_execution_dir = os.getcwd()
        output_base_dir = os.path.join(script_execution_dir, "ProyScan_Resultados")
        print(f"Usando directorio de salida predeterminado: {output_base_dir}")

    # Crear directorio base de salida si no existe
    try:
        os.makedirs(output_base_dir, exist_ok=True)
    except OSError as e:
        print(f"Error: No se pudo crear el directorio base de salida {output_base_dir}: {e}", file=sys.stderr)
        sys.exit(1)

    # Crear subdirectorio único para este escaneo
    id_escaneo = generar_id_aleatorio()
    nombre_subdir_escaneo = f"{nombre_base_proyecto}-{id_escaneo}"
    output_dir_escaneo_actual = os.path.join(output_base_dir, nombre_subdir_escaneo)

    try:
        # Intentar crear el subdirectorio único
        os.makedirs(output_dir_escaneo_actual)
        print(f"Resultados se guardarán en: {output_dir_escaneo_actual}")
    except OSError as e:
        print(f"Error: No se pudo crear el subdirectorio de escaneo {output_dir_escaneo_actual}: {e}", file=sys.stderr)
        # Podríamos intentar generar otro ID, pero por simplicidad salimos
        sys.exit(1)

    # --- Ejecutar Escaneo ---
    script_name = os.path.basename(__file__)
    try:
        # Pasamos el directorio objetivo y el directorio de salida específico para este escaneo
        ejecutar_escaneo(target_dir_abs, script_name, output_dir_escaneo_actual)
    except Exception as e:
        print(f"\nERROR INESPERADO DURANTE LA EJECUCIÓN:", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()