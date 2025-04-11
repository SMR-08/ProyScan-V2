# proyscan/cli.py
import sys
import os
import logging
import questionary
import random
import string
from typing import Optional
import tempfile # Para crear archivo temporal
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

try:
    from .core import ejecutar_escaneo
    from .config_manager import cargar_config, guardar_config, obtener_ruta_salida_predeterminada_global
    from .config import PATRONES_IGNORE_COMUNES    # --- Importar config manager ---
except ImportError as e:
     print(f"Error crítico de importación en cli.py: {e}", file=sys.stderr)
     print("Asegúrate de que la estructura del proyecto es correcta.", file=sys.stderr)
     sys.exit(1)

logger = logging.getLogger(__name__)
console = Console()

# --- Funciones Auxiliares CLI ---

def validar_directorio(ruta: str) -> bool | str:
    """Valida si una ruta es un directorio existente."""
    if not ruta: # Permitir entrada vacía para usar predeterminado/último
        return True
    if os.path.isdir(ruta):
        return True
    else:
        return f"La ruta '{ruta}' no es un directorio válido o no existe."

def validar_ruta_salida(ruta: str) -> bool | str:
    """Valida si una ruta de salida es potencialmente válida."""
    if not ruta: # Permitir vacío para usar predeterminado
        return True
    abs_ruta = os.path.abspath(ruta)
    # Comprobar si el padre existe y es escribible (heurística)
    dir_padre = os.path.dirname(abs_ruta)
    if not dir_padre: dir_padre = '.' # Caso raíz

    if os.path.exists(abs_ruta) and not os.path.isdir(abs_ruta):
        return f"'{abs_ruta}' existe pero no es un directorio."
    if not os.path.exists(dir_padre):
         return f"El directorio padre '{dir_padre}' no existe."
    if not os.access(dir_padre, os.W_OK):
         return f"No tienes permisos de escritura en '{dir_padre}'."
    return True

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
    """Pide al usuario la ruta del proyecto con validación."""
    mensaje = "Introduce la ruta al directorio del proyecto"
    default_val = ultimo_conocido if ultimo_conocido and os.path.isdir(ultimo_conocido) else ""
    if default_val:
        mensaje += f" (Enter para usar último: '{default_val}')"
    mensaje += ":"

    while True: # Bucle hasta obtener ruta válida o cancelar
        ruta = questionary.text(
            mensaje,
            default=default_val,
            validate=validar_directorio # Usar validador
        ).ask() # Usar ask() que devuelve None si se cancela (Ctrl+C)

        if ruta is None: # Cancelado por el usuario
             return None
        elif ruta == "" and default_val:
             console.print(f"[dim]Usando último directorio: {default_val}[/dim]")
             return default_val
        elif ruta and os.path.isdir(ruta):
             return os.path.abspath(ruta)
        elif ruta == "": # Si no había default y se presiona Enter
             console.print("[yellow]Por favor, introduce una ruta válida.[/yellow]")


def seleccionar_directorio_salida(predeterminado_config=None):
    """Pide al usuario la ruta de salida con validación."""
    predeterminado_real = predeterminado_config if predeterminado_config else obtener_ruta_salida_predeterminada_global()
    mensaje = f"Introduce la ruta para guardar los resultados (Enter para usar: '{predeterminado_real}'):"

    while True:
        ruta = questionary.text(
            mensaje,
            default="", # No poner el default aquí, se maneja abajo
            validate=validar_ruta_salida # Usar validador
        ).ask()

        if ruta is None: # Cancelado
            return None
        elif ruta == "":
             console.print(f"[dim]Usando directorio de salida predeterminado: {predeterminado_real}[/dim]")
             # Asegurarse de que exista al final
             return predeterminado_real
        else:
             abs_ruta = os.path.abspath(ruta)
             # La validación ya comprobó si es un dir existente o si se puede crear
             return abs_ruta

def configurar_ignore_interactivo(directorio_objetivo: str) -> Optional[str]:
    """Permite al usuario seleccionar patrones y genera un .ignore temporal."""
    console.print("\n--- Configuración de .ignore Temporal ---", style="bold blue")
    if not questionary.confirm("¿Quieres configurar un archivo .ignore temporal para este escaneo?", default=False).ask():
        return None

    selecciones_finales = set()
    patrones_disponibles = PATRONES_IGNORE_COMUNES

    # 1. Seleccionar Categorías Principales
    categorias = list(patrones_disponibles.keys())
    categorias_seleccionadas = questionary.checkbox(
        "Selecciona las categorías generales a ignorar:",
        choices=categorias
    ).ask()

    if categorias_seleccionadas is None: return None # Cancelado

    # 2. Refinar por Categoría (Selección Detallada)
    for cat in categorias_seleccionadas:
        items_categoria = patrones_disponibles[cat]
        choices_items = []
        # Crear choices para questionary, manejando dict o list
        if isinstance(items_categoria, dict):
             choices_items = [questionary.Choice(title=f"{patron} ({desc})", value=patron, checked=True)
                              for patron, desc in items_categoria.items()]
        elif isinstance(items_categoria, list):
             choices_items = [questionary.Choice(title=patron, value=patron, checked=True)
                              for patron in items_categoria]

        if not choices_items: continue

        console.print(f"\n[cyan]Refinar selecciones para '{cat}':[/cyan]")
        items_seleccionados = questionary.checkbox(
            f"Patrones a incluir de '{cat}' (preseleccionados):",
            choices=choices_items
        ).ask()

        if items_seleccionados is None: return None # Cancelado
        selecciones_finales.update(items_seleccionados)

    if not selecciones_finales:
        console.print("[yellow]No se seleccionó ningún patrón. No se creará .ignore temporal.[/yellow]")
        return None

    # 3. Generar y Guardar Archivo Temporal
    contenido_ignore = f"# ProyScan .ignore Temporal Generado\n"
    contenido_ignore += f"# {len(selecciones_finales)} patrones seleccionados\n\n"
    contenido_ignore += "\n".join(sorted(list(selecciones_finales)))

    try:
        # Crear archivo temporal en el directorio OBJETIVO
        # Usamos un nombre específico para poder borrarlo después
        ignore_temp_path = os.path.join(directorio_objetivo, ".proyscan_ignore_temp")

        with open(ignore_temp_path, 'w', encoding='utf-8') as f:
            f.write(contenido_ignore)
        logger.info(f"Archivo .ignore temporal creado en: {ignore_temp_path}")
        console.print(f"[green].ignore temporal generado con {len(selecciones_finales)} patrones.[/green]")
        return ignore_temp_path # Devolver la ruta al archivo temporal
    except Exception as e:
        logger.error(f"No se pudo crear el archivo .ignore temporal en {directorio_objetivo}: {e}", exc_info=True)
        console.print(f"[red]Error al crear .ignore temporal.[/red]")
        return None

def preguntar_modo_debug(predeterminado=False):
     # Usar confirmación con el valor predeterminado cargado
     return questionary.confirm("¿Habilitar modo Debug para este escaneo?", default=predeterminado).unsafe_ask()


def ejecutar_flujo_escaneo():
    """Guía al usuario a través del proceso de escaneo."""
    logger.info("Iniciando flujo de escaneo interactivo...")
    config = cargar_config()
    predeterminado_salida = config.get("default_output_dir")
    ultimo_proyecto = config.get("last_target_dir")
    debug_predeterminado = config.get("default_debug_mode", False)

    console.print(Panel("Paso 1: Seleccionar Directorio del Proyecto", style="bold green"))
    ruta_proyecto = seleccionar_directorio_proyecto(ultimo_proyecto)
    if ruta_proyecto is None: console.print("[yellow]Operación cancelada.[/yellow]"); return
    config["last_target_dir"] = ruta_proyecto # Guardar aunque cancele después
    guardar_config(config)

    console.print(Panel("Paso 2: Seleccionar Directorio de Salida", style="bold green"))
    ruta_salida_base = seleccionar_directorio_salida(predeterminado_salida)
    if ruta_salida_base is None: console.print("[yellow]Operación cancelada.[/yellow]"); return

    # --- Llamar a la configuración interactiva de .ignore ---
    ruta_ignore_temporal = configurar_ignore_interactivo(ruta_proyecto)
    # Si se cancela aquí, ruta_ignore_temporal será None, lo cual está bien.

    console.print(Panel("Paso 4: Opciones de Ejecución", style="bold green"))
    modo_debug = preguntar_modo_debug(debug_predeterminado)
    if modo_debug is None: console.print("[yellow]Operación cancelada.[/yellow]"); return


    console.print("\n--- Resumen del Escaneo ---", style="bold blue")
    console.print(f"[cyan]Proyecto a escanear :[/cyan] {ruta_proyecto}")
    console.print(f"[cyan]Directorio base salida:[/cyan] {ruta_salida_base}")
    console.print(f"[cyan]Modo Debug          :[/cyan] {'Sí' if modo_debug else 'No'}")
    ignore_status = "No"
    if ruta_ignore_temporal: ignore_status = f"Sí (en {os.path.basename(ruta_ignore_temporal)})"
    console.print(f"[cyan].ignore Temporal    :[/cyan] {ignore_status}")
    console.print("---------------------------\n", style="bold blue")

    choices = [ questionary.Choice(title="Iniciar Escaneo", value="start"), questionary.Choice(title="Cancelar", value="cancel")]
    accion = questionary.select("¿Confirmar y iniciar?", choices=choices, default="start").ask()

    if accion == "cancel" or accion is None:
        console.print("[yellow]Escaneo cancelado.[/yellow]")
        # Borrar ignore temporal si se creó y se cancela aquí
        if ruta_ignore_temporal and os.path.exists(ruta_ignore_temporal):
            try: os.remove(ruta_ignore_temporal); logger.info("Ignore temporal eliminado por cancelación.")
            except Exception: logger.warning("No se pudo eliminar ignore temporal tras cancelación.")
        return

    # --- Preparar y ejecutar ---
    nombre_base_proyecto = os.path.basename(ruta_proyecto)
    id_escaneo = ''.join(random.choice(string.ascii_letters) for _ in range(6))
    nombre_subdir_escaneo = f"{nombre_base_proyecto}-{id_escaneo}"
    directorio_salida_escaneo_actual = os.path.join(ruta_salida_base, nombre_subdir_escaneo)

    try:
        os.makedirs(directorio_salida_escaneo_actual, exist_ok=True)
        console.print(f"\n[green]Iniciando escaneo... Los resultados se guardarán en:[/green] {directorio_salida_escaneo_actual}")

        # --- Bloque try...finally para limpieza ---
        ignore_a_usar = ruta_ignore_temporal # Usar el temporal si existe
        try:
            ejecutar_escaneo(
                directorio_objetivo=ruta_proyecto,
                nombre_script_ignorar=None,
                directorio_salida_escaneo=directorio_salida_escaneo_actual,
                debug_mode=modo_debug,
                ruta_ignore_especifica=ignore_a_usar # Pasar la ruta temporal
            )
            console.print(f"\n[bold green]¡Escaneo completado exitosamente![/bold green]")
        finally:
            if ignore_a_usar and os.path.exists(ignore_a_usar):
                 try:
                      os.remove(ignore_a_usar)
                      logger.info(f"Archivo .ignore temporal eliminado: {ignore_a_usar}")
                 except OSError as e_remove:
                      logger.warning(f"No se pudo eliminar el archivo .ignore temporal {ignore_a_usar}: {e_remove}")
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
        choices = [
            "1. Cambiar Directorio de Salida Predeterminado",
            "2. Activar/Desactivar Modo Debug Predeterminado",
            "3. Borrar Último Directorio Escaneado (sugerencia)",
            questionary.Separator(),
            "4. Volver al Menú Principal",
        ]
        opcion = questionary.select(
            "Selecciona una opción de configuración:",
            choices=choices, use_shortcuts=True
        ).ask()

        if opcion is None or opcion.startswith("4."): break

        elif opcion.startswith("1."):
            ruta_actual = config.get("default_output_dir", obtener_ruta_salida_predeterminada_global())
            nueva_ruta = questionary.text(
                f"Introduce la nueva ruta de salida predeterminada (Actual: '{ruta_actual}'):",
                validate=validar_ruta_salida
            ).ask()
            if nueva_ruta is not None: # Permite borrarla (string vacío) o cancelar (None)
                 abs_nueva_ruta = os.path.abspath(nueva_ruta) if nueva_ruta else None
                 # Guardar None si la ruta está vacía para usar el default global
                 config["default_output_dir"] = abs_nueva_ruta
                 guardar_config(config)
                 if abs_nueva_ruta:
                     console.print(f"[green]Directorio de salida predeterminado actualizado a:[/green] {abs_nueva_ruta}")
                 else:
                     console.print(f"[green]Directorio de salida predeterminado borrado. Se usará la ruta global: {obtener_ruta_salida_predeterminada_global()}[/green]")

        elif opcion.startswith("2."):
            debug_actual = config.get("default_debug_mode", False)
            confirmacion = questionary.confirm(f"Modo Debug predeterminado está {'ACTIVADO' if debug_actual else 'DESACTIVADO'}. ¿Desea cambiarlo?", default=True).ask()
            if confirmacion: # Solo cambia si el usuario confirma
                config["default_debug_mode"] = not debug_actual
                guardar_config(config)
                console.print(f"[green]Modo Debug predeterminado ahora está {'ACTIVADO' if config['default_debug_mode'] else 'DESACTIVADO'}.[/green]")

        elif opcion.startswith("3."):
            if config.get("last_target_dir"):
                 if questionary.confirm("¿Seguro que quieres borrar la sugerencia del último directorio escaneado?", default=False).ask():
                      config["last_target_dir"] = None
                      guardar_config(config)
                      console.print("[green]Sugerencia de último directorio borrada.[/green]")
            else:
                 console.print("[yellow]No hay último directorio guardado para borrar.[/yellow]")

        console.print("\n")

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
        ).ask() # Usar ask() para permitir cancelación con Ctrl+C

        if choice == "scan":
            ejecutar_flujo_escaneo()
        elif choice == "manage":
            gestionar_escaneos()
        elif choice == "config":
            configurar_opciones()
        elif choice == "exit" or choice is None: # Si se presiona Ctrl+C, ask() devuelve None
            console.print("[bold cyan]¡Hasta luego![/bold cyan]")
            break
        # else: # No es necesario, select fuerza una opción válida o None

        console.print("\n" * 1)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    run_interactive_cli()