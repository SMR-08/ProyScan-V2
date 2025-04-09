# proyscan.py (Script principal para ejecutar desde la línea de comandos)
import sys
import os

# Añadir el directorio padre al sys.path para poder importar el paquete 'proyscan'
# Esto es útil si ejecutas 'python proyscan.py' desde la raíz
current_dir = os.path.dirname(os.path.abspath(__file__))
# sys.path.insert(0, current_dir) # Descomentar si tienes problemas de importación

# Importar la función principal y constantes necesarias
try:
    from proyscan.core import ejecutar_escaneo
    from proyscan.config import DIR_PROYECTO
except ImportError as e:
    print("Error: No se pudo importar el paquete 'proyscan'.")
    print("Asegúrate de que estás ejecutando el script desde el directorio raíz del proyecto", file=sys.stderr)
    print(f"Detalle del error: {e}", file=sys.stderr)
    sys.exit(1)


def verificar_dependencias():
    """Verifica si las dependencias externas están instaladas."""
    try:
        import chardet
        # Si se añaden más dependencias externas, verificarlas aquí
    except ImportError:
        print("ERROR: Dependencia externa 'chardet' no encontrada.", file=sys.stderr)
        print("Por favor, instala las dependencias ejecutando:", file=sys.stderr)
        print("pip install -r requirements.txt", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    print("--- ProyScan ---")
    verificar_dependencias()

    # Determinar el nombre del script para la lógica de ignorar
    script_name = os.path.basename(__file__)

    # Ejecutar el escaneo usando el directorio del proyecto detectado en config
    # y pasando el nombre de este script para que se auto-ignore.
    try:
        ejecutar_escaneo(DIR_PROYECTO, script_name)
    except Exception as e:
        print(f"\nERROR INESPERADO DURANTE LA EJECUCIÓN:", file=sys.stderr)
        # Imprimir traceback para depuración
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # input("Presiona Enter para salir...") # Opcional