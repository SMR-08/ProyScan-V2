# proyscan/cli.py
import sys
import os
import logging
import questionary
import random # Necesario para ID único
import string # Necesario para ID único
from rich.console import Console
from rich.panel import Panel

try:
    from .core import ejecutar_escaneo
    # --- Importar config manager ---
    from .config_manager import cargar_config, guardar_config, obtener_ruta_salida_predeterminada_global
except ImportError as e:
     print(f"Error crítico de importación en cli.py: {e}", file=sys.stderr)
     print("Asegúrate de que la estructura del proyecto es correcta.", file=sys.stderr)
     sys.exit(1)

logger = logging.getLogger(__name__)
console = Console()

# --- Funciones Auxiliares CLI ---

def mostrar_configuracion_actual(config: dict):
    """Muestra la configuración actual formateada."""
    console.print("\n--- Configuración Actual ---", style="bold blue")
    # Usamos la función para obtener la ruta global predeterminada
    salida_predet = config.get("default_output_dir", obtener_ruta_salida_predeterminada_global())
    ultimo_proyecto = config.get("last_target_dir", "Ninguno")
    debug_predet = config.get("default_debug_mode", False)

    console.print(f"[cyan]Directorio Salida Predeterminado:[/cyan] {salida_predet if salida_predet else 'No establecido (se usará ./' + os.path.basename(obtener_ruta_salida_predeterminada_global()) + ')'}")
    console.print(f"[cyan]Último Directorio Escaneado:[/cyan] {ultimo_proyecto}")
    console.print(f"[cyan]Modo Debug Predeterminado:[/cyan] {'Activado' if debug_predet else 'Desactivado'}")
    console.print("--------------------------\n", style="bold blue")

# --- Funciones Principales de la CLI (Modificadas) ---

# (seleccionar_directorio_proyecto y seleccionar_directorio_salida se modificarán en Fase B/E)
# Dejamos los placeholders actuales por ahora, pero usamos la config para sugerencias

def seleccionar_directorio_proyecto(ultimo_conocido=None):
    mensaje = "Introduce la ruta al directorio del proyecto"
    if ultimo_conocido:
        mensaje += f" (Enter para usar último: '{ultimo_conocido}')"
    mensaje += ":"

    ruta = questionary.text(
        mensaje,
        default=ultimo_conocido if ultimo_conocido else "", # Usar último como default
        validate=lambda text: True if not text or os.path.isdir(text) else "La ruta debe ser un directorio válido o vacío para usar el último."
    ).unsafe_ask()

    if not ruta and ultimo_conocido:
        # Validar si el último conocido sigue siendo válido
        if os.path.isdir(ultimo_conocido):
             return ultimo_conocido
        else:
             console.print(f"[yellow]Advertencia: El último directorio '{ultimo_conocido}' ya no es válido. Por favor, introduce uno nuevo.[/yellow]")
             # Volver a preguntar sin default
             ruta = questionary.text(
                  "Introduce la ruta al directorio del proyecto:",
                  validate=lambda t: True if os.path.isdir(t) else "La ruta debe ser un directorio válido."
             ).unsafe_ask()
             return os.path.abspath(ruta) if ruta and os.path.isdir(ruta) else None
    elif ruta and os.path.isdir(ruta):
         return os.path.abspath(ruta)
    else:
         return None


def seleccionar_directorio_salida(predeterminado_config=None):
    mensaje = "Introduce la ruta para guardar los resultados"
    # Usar la ruta global como predeterminado si no hay nada en config
    predeterminado_real = predeterminado_config if predeterminado_config else obtener_ruta_salida_predeterminada_global()

    mensaje += f" (Enter para usar: '{predeterminado_real}')"
    mensaje += ":"

    ruta = questionary.text(mensaje, default="").unsafe_ask() # No poner default aquí para forzar Enter

    ruta_final = None
    if not ruta:
        ruta_final = predeterminado_real # Usar el predeterminado real
    elif ruta:
        ruta_final = os.path.abspath(ruta)

    # Validar/Crear directorio final
    if ruta_final:
        if os.path.exists(ruta_final) and not os.path.isdir(ruta_final):
             console.print(f"[red]Error: La ruta de salida '{ruta_final}' existe pero no es un directorio.[/red]")
             return None
        # No necesitamos crearlo aquí, se hará antes de llamar a ejecutar_escaneo
        return ruta_final
    else:
        return None


def configurar_ignore_interactivo():
    # Placeholder para Fase B
    console.print("[yellow](Placeholder) Configuración de .ignore interactivo aún no implementada.[/yellow]")
    return None

def preguntar_modo_debug(predeterminado=False):
     # Usar confirmación con el valor predeterminado cargado
     return questionary.confirm("¿Habilitar modo Debug para este escaneo?", default=predeterminado).unsafe_ask()


def ejecutar_flujo_escaneo():
    """Guía al usuario a través del proceso de escaneo."""
    logger.info("Iniciando flujo de escaneo interactivo...")

    # --- Cargar configuración ---
    config = cargar_config()
    predeterminado_salida = config.get("default_output_dir") # Puede ser None
    ultimo_proyecto = config.get("last_target_dir") # Puede ser None
    debug_predeterminado = config.get("default_debug_mode", False)
    # ---------------------------

    # 1. Seleccionar Proyecto (pasando último conocido)
    ruta_proyecto = seleccionar_directorio_proyecto(ultimo_proyecto)
    if not ruta_proyecto:
        console.print("[red]Escaneo cancelado.[/red]")
        return

    # --- Guardar última ruta ---
    config["last_target_dir"] = ruta_proyecto
    guardar_config(config)
    # -------------------------

    # 2. Seleccionar Salida (pasando predeterminado de config)
    ruta_salida_base = seleccionar_directorio_salida(predeterminado_salida)
    if not ruta_salida_base:
        console.print("[red]Escaneo cancelado.[/red]")
        return

    # 3. Configurar .ignore (temporal) - Sin cambios aún
    ruta_ignore_temporal = configurar_ignore_interactivo()

    # 4. Modo Debug (pasando predeterminado de config)
    modo_debug = preguntar_modo_debug(debug_predeterminado)

    # 5. Resumen y Confirmación - Sin cambios visuales

    console.print("\n--- Resumen del Escaneo ---", style="bold blue")
    console.print(f"Proyecto a escanear : {ruta_proyecto}")
    console.print(f"Directorio base salida: {ruta_salida_base}")
    console.print(f"Modo Debug          : {'Sí' if modo_debug else 'No'}")
    console.print(f".ignore Temporal    : {'Sí (generado)' if ruta_ignore_temporal else 'No (usará el del proyecto si existe)'}")
    console.print("---------------------------\n", style="bold blue")

    # --- Añadir opción de Cancelar ---
    choices = [
        questionary.Choice(title="Iniciar Escaneo", value="start"),
        questionary.Choice(title="Cancelar", value="cancel")
    ]
    accion = questionary.select("¿Confirmar y iniciar?", choices=choices, default="start").unsafe_ask()

    if accion == "cancel" or accion is None:
        console.print("[yellow]Escaneo cancelado por el usuario.[/yellow]")
        return
    # ---------------------------------

    # --- Preparar directorio de salida específico ---
    nombre_base_proyecto = os.path.basename(ruta_proyecto)
    id_escaneo = ''.join(random.choice(string.ascii_letters) for _ in range(6))
    nombre_subdir_escaneo = f"{nombre_base_proyecto}-{id_escaneo}"
    directorio_salida_escaneo_actual = os.path.join(ruta_salida_base, nombre_subdir_escaneo)

    try:
        # Crear ambos directorios (base y específico) si no existen
        os.makedirs(directorio_salida_escaneo_actual, exist_ok=True)
        console.print(f"\n[green]Iniciando escaneo... Los resultados se guardarán en:[/green] {directorio_salida_escaneo_actual}")

        # --- Limpieza del ignore temporal (try...finally) ---
        try:
            ejecutar_escaneo(
                directorio_objetivo=ruta_proyecto,
                nombre_script_ignorar=None,
                directorio_salida_escaneo=directorio_salida_escaneo_actual,
                debug_mode=modo_debug
                # , ruta_ignore_especifica=ruta_ignore_temporal # Futuro
            )
            console.print(f"\n[bold green]¡Escaneo completado exitosamente![/bold green]")

        finally:
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


def gestionar_escaneos():
    # Placeholder Fase C
    console.print("[yellow](Placeholder) Gestión de escaneos aún no implementada.[/yellow]")

def configurar_opciones():
    """Permite al usuario ver y modificar la configuración."""
    logger.info("Accediendo al menú de configuración...")
    config = cargar_config()

    while True:
        mostrar_configuracion_actual(config)

        opcion = questionary.select(
            "Selecciona una opción de configuración:",
            choices=[
                "1. Cambiar Directorio de Salida Predeterminado",
                "2. Activar/Desactivar Modo Debug Predeterminado",
                "3. Borrar Último Directorio Escaneado (sugerencia)",
                questionary.Separator(),
                "4. Volver al Menú Principal",
            ],
            use_shortcuts=True
        ).unsafe_ask()

        if opcion is None or opcion.startswith("4."): # Salir
            break
        elif opcion.startswith("1."):
            nueva_ruta = questionary.text(
                "Introduce la nueva ruta de salida predeterminada:",
                validate=lambda text: True if text else "La ruta no puede estar vacía." # Validación simple
            ).unsafe_ask()
            if nueva_ruta:
                abs_nueva_ruta = os.path.abspath(nueva_ruta)
                # Validar si podemos crearla (simplificado)
                try:
                     os.makedirs(abs_nueva_ruta, exist_ok=True)
                     config["default_output_dir"] = abs_nueva_ruta
                     guardar_config(config)
                     console.print(f"[green]Directorio de salida predeterminado actualizado a:[/green] {abs_nueva_ruta}")
                except Exception as e:
                     console.print(f"[red]Error al establecer la ruta '{abs_nueva_ruta}': {e}[/red]")
        elif opcion.startswith("2."):
            debug_actual = config.get("default_debug_mode", False)
            nuevo_estado = questionary.confirm(f"Modo Debug predeterminado está {'ACTIVADO' if debug_actual else 'DESACTIVADO'}. ¿Desea cambiarlo?", default=True).unsafe_ask()
            if nuevo_estado:
                config["default_debug_mode"] = not debug_actual
                guardar_config(config)
                console.print(f"[green]Modo Debug predeterminado ahora está {'ACTIVADO' if config['default_debug_mode'] else 'DESACTIVADO'}.[/green]")
        elif opcion.startswith("3."):
            if config.get("last_target_dir"):
                 if questionary.confirm("¿Seguro que quieres borrar la sugerencia del último directorio escaneado?", default=False).unsafe_ask():
                      config["last_target_dir"] = None
                      guardar_config(config)
                      console.print("[green]Sugerencia de último directorio borrada.[/green]")
            else:
                 console.print("[yellow]No hay último directorio guardado para borrar.[/yellow]")

        console.print("\n") # Espacio

# --- Función Principal de la CLI (run_interactive_cli) ---
# (El bucle while True y las llamadas a funciones como estaban antes)
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
            use_shortcuts=True
        ).unsafe_ask()

        if choice == "scan":
            ejecutar_flujo_escaneo()
        elif choice == "manage":
            gestionar_escaneos()
        elif choice == "config":
            configurar_opciones() # Llamar a la nueva función
        elif choice == "exit" or choice is None:
            console.print("[bold cyan]¡Hasta luego![/bold cyan]")
            break
        else:
             console.print("[yellow]Opción no reconocida.[/yellow]")

        console.print("\n" * 1) # Menos espacio
        # Pausa opcional antes de volver a mostrar el menú
        # input("Presiona Enter para continuar...")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    run_interactive_cli()