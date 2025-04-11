# proyscan/cli.py
import sys
import os
import logging
import random, string
import questionary # Importar questionary
from rich.console import Console # Importar Rich Console
from rich.panel import Panel

# Importar funciones y configuración necesarias de ProyScan
# (Asegúrate de que las importaciones relativas funcionen o ajusta sys.path)
try:
    from .core import ejecutar_escaneo
    # Importar config manager cuando exista
    # from .config_manager import cargar_config, guardar_config
    # Importar otras funciones si es necesario
except ImportError as e:
     # Este error no debería ocurrir si la estructura es correcta y se llama desde proyscan.py
     print(f"Error crítico de importación en cli.py: {e}", file=sys.stderr)
     print("Asegúrate de que la estructura del proyecto es correcta.", file=sys.stderr)
     sys.exit(1)

# Configurar logger para este módulo
logger = logging.getLogger(__name__) # Usa 'proyscan.cli'
console = Console() # Instancia de Rich Console para salida formateada

# --- Funciones de la CLI (se irán implementando) ---

def seleccionar_directorio_proyecto():
    # Placeholder para Fase B/E
    console.print("[cyan]Selección de directorio de proyecto (placeholder)...[/cyan]")
    # Temporalmente pedimos ruta como texto
    ruta = questionary.text(
        "Introduce la ruta al directorio del proyecto:",
        validate=lambda text: True if os.path.isdir(text) else "La ruta debe ser un directorio válido."
    ).unsafe_ask() # unsafe_ask para evitar problemas en algunos terminales/tests
    return os.path.abspath(ruta) if ruta else None

def seleccionar_directorio_salida(predeterminado=None):
    # Placeholder para Fase B
    console.print("[cyan]Selección de directorio de salida (placeholder)...[/cyan]")
    mensaje = "Introduce la ruta para guardar los resultados"
    if predeterminado:
        mensaje += f" (Enter para usar predeterminado: '{predeterminado}')"
    else:
        mensaje += " (Enter para usar './ProyScan_Resultados')"

    ruta = questionary.text(mensaje + ":").unsafe_ask()

    if not ruta and predeterminado:
        return predeterminado # Usa predeterminado si existe y no se introduce nada
    elif not ruta and not predeterminado:
        # Crear predeterminado si no se especifica y no hay config
        predeterminado_calculado = os.path.join(os.getcwd(), "ProyScan_Resultados")
        return predeterminado_calculado
    elif ruta:
        # Validar si es escribible (simplificado: solo vemos si existe o podemos crearlo)
        abs_ruta = os.path.abspath(ruta)
        # No creamos aquí, solo validamos si podemos (más o menos)
        if os.path.exists(abs_ruta) and not os.path.isdir(abs_ruta):
             console.print(f"[red]Error: La ruta de salida '{abs_ruta}' existe pero no es un directorio.[/red]")
             return None # Indicar error
        elif not os.path.exists(abs_ruta):
             try:
                  # Intentar crear directorio padre si no existe
                  os.makedirs(os.path.dirname(abs_ruta) if os.path.dirname(abs_ruta) else '.', exist_ok=True)
                  # Ok, parece escribible
             except Exception:
                  console.print(f"[red]Error: No se puede crear el directorio de salida '{abs_ruta}'. Verifica permisos.[/red]")
                  return None
        return abs_ruta # Devolver ruta absoluta validada (más o menos)
    else: # Caso imposible?
        return None


def configurar_ignore_interactivo():
    # Placeholder para Fase B
    console.print("[yellow]Configuración de .ignore interactivo aún no implementada.[/yellow]")
    return None # Devuelve None para indicar que no se creó .ignore temporal

def preguntar_modo_debug(predeterminado=False):
     # Placeholder para Fase B
     return questionary.confirm("¿Habilitar modo Debug para este escaneo?", default=predeterminado).unsafe_ask()


def ejecutar_flujo_escaneo():
    """Guía al usuario a través del proceso de escaneo."""
    logger.info("Iniciando flujo de escaneo interactivo...")

    # --- Cargar configuración (Fase A.3) ---
    # config = cargar_config()
    # predeterminado_salida = config.get("default_output_dir")
    # ultimo_proyecto = config.get("last_target_dir")
    # debug_predeterminado = config.get("default_debug_mode", False)
    # --- Placeholders mientras no hay config_manager ---
    predeterminado_salida = os.path.join(os.getcwd(), "ProyScan_Resultados") # Temporal
    ultimo_proyecto = None # Temporal
    debug_predeterminado = False # Temporal
    # -------------------------------------------------


    # 1. Seleccionar Proyecto
    ruta_proyecto = seleccionar_directorio_proyecto() # Usará el placeholder por ahora
    if not ruta_proyecto:
        console.print("[red]Escaneo cancelado: No se seleccionó directorio de proyecto.[/red]")
        return

    # --- Guardar última ruta (Fase A.3) ---
    # config["last_target_dir"] = ruta_proyecto
    # guardar_config(config)
    # --------------------------------------

    # 2. Seleccionar Salida
    ruta_salida = seleccionar_directorio_salida(predeterminado_salida) # Placeholder
    if not ruta_salida:
        console.print("[red]Escaneo cancelado: No se seleccionó directorio de salida.[/red]")
        return

    # 3. Configurar .ignore (temporal)
    ruta_ignore_temporal = configurar_ignore_interactivo() # Placeholder

    # 4. Modo Debug
    modo_debug = preguntar_modo_debug(debug_predeterminado) # Placeholder

    # 5. Resumen y Confirmación
    console.print("\n--- Resumen del Escaneo ---", style="bold blue")
    console.print(f"Proyecto a escanear : {ruta_proyecto}")
    console.print(f"Directorio base salida: {ruta_salida}")
    console.print(f"Modo Debug          : {'Sí' if modo_debug else 'No'}")
    console.print(f".ignore Temporal    : {'Sí (generado)' if ruta_ignore_temporal else 'No (usará el del proyecto si existe)'}")
    console.print("---------------------------\n", style="bold blue")

    if not questionary.confirm("¿Iniciar escaneo con esta configuración?", default=True).unsafe_ask():
        console.print("[yellow]Escaneo cancelado por el usuario.[/yellow]")
        return

    # --- Ejecutar el Core ---
    nombre_base_proyecto = os.path.basename(ruta_proyecto)
    id_escaneo = ''.join(random.choice(string.ascii_letters) for _ in range(6)) # Mover generar_id aquí?
    nombre_subdir_escaneo = f"{nombre_base_proyecto}-{id_escaneo}"
    directorio_salida_escaneo_actual = os.path.join(ruta_salida, nombre_subdir_escaneo)

    try:
        os.makedirs(directorio_salida_escaneo_actual, exist_ok=True) # Asegurar que existe
        console.print(f"\n[green]Iniciando escaneo... Los resultados se guardarán en:[/green] {directorio_salida_escaneo_actual}")

        # --- Limpieza del ignore temporal ---
        try:
            # Llamamos a la función principal del core
            # Pasamos None para nombre_script_ignorar ya que no es relevante aquí
            # Pasamos el modo debug y la ruta de salida calculada
            # Añadiremos la ruta al ignore temporal cuando exista
            ejecutar_escaneo(
                directorio_objetivo=ruta_proyecto,
                nombre_script_ignorar=None, # El script principal no estará en el objetivo
                directorio_salida_escaneo=directorio_salida_escaneo_actual,
                debug_mode=modo_debug
                # , ruta_ignore_especifica=ruta_ignore_temporal # Argumento futuro
            )
            console.print(f"\n[bold green]¡Escaneo completado exitosamente![/bold green]")

        finally:
            # --- Borrar .ignore temporal SI SE CREÓ ---
            if ruta_ignore_temporal and os.path.exists(ruta_ignore_temporal):
                 try:
                      os.remove(ruta_ignore_temporal)
                      logger.info(f"Archivo .ignore temporal eliminado: {ruta_ignore_temporal}")
                 except OSError as e_remove:
                      logger.warning(f"No se pudo eliminar el archivo .ignore temporal {ruta_ignore_temporal}: {e_remove}")
            # ------------------------------------------

    except Exception as e:
        console.print(f"\n[bold red]ERROR durante el escaneo:[/bold red]")
        logger.critical("Error no capturado durante la ejecución del escaneo:", exc_info=True)
        # Imprimir traceback si no usamos logging extenso
        # import traceback
        # console.print(traceback.format_exc())


def gestionar_escaneos():
    # Placeholder para Fase C
    console.print("[yellow]Gestión de escaneos aún no implementada.[/yellow]")

def configurar_opciones():
    # Placeholder para Fase A.3
    console.print("[yellow]Configuración de opciones aún no implementada.[/yellow]")
    # Aquí iría la lógica con questionary y config_manager

# --- Función Principal de la CLI ---
def run_interactive_cli():
    """Ejecuta el menú principal interactivo."""

    while True:
        console.print(Panel("Bienvenido a ProyScan V2.1", title="Menú Principal", border_style="blue"))
        choice = questionary.select(
            "Selecciona una opción:",
            choices=[
                questionary.Choice(title="1. Escanear Nuevo Proyecto", value="scan"),
                questionary.Choice(title="2. Gestionar Escaneos Guardados", value="manage"),
                questionary.Choice(title="3. Configuración", value="config"),
                questionary.Separator(),
                questionary.Choice(title="4. Salir", value="exit"),
            ],
            use_shortcuts=True # Permite usar números
        ).unsafe_ask()

        if choice == "scan":
            ejecutar_flujo_escaneo()
        elif choice == "manage":
            gestionar_escaneos()
        elif choice == "config":
            configurar_opciones()
        elif choice == "exit" or choice is None: # Salir si se presiona Esc o Ctrl+C
            console.print("[bold cyan]¡Hasta luego![/bold cyan]")
            break
        else:
             # Opción inválida (no debería pasar con select)
             console.print("[yellow]Opción no reconocida.[/yellow]")

        # Pausa opcional antes de volver a mostrar el menú
        # questionary.press_any_key_to_continue().ask()
        console.print("\n" * 2) # Espacio antes del siguiente menú


if __name__ == '__main__':
    # Esto es principalmente para probar cli.py directamente
    # Configuración básica de logging para pruebas
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    run_interactive_cli()