# proyscan/tui_browser.py
import os
import platform
import logging
import shutil
import subprocess
import string # Necesario si usamos generar_id aquí, aunque ya no se usa
from typing import Optional, List, Tuple
from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, VSplit, Window, WindowAlign, ConditionalContainer
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.styles import Style
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.filters import IsDone
from prompt_toolkit.layout.margins import ScrollbarMargin
from prompt_toolkit.data_structures import Point

logger = logging.getLogger(__name__)

# Estilo básico
default_style = Style.from_dict({
    'list-item.selected': 'reverse',
    'list-item.directory': 'bold cyan',
    'list-item.file': '',
    'list-item.drive': 'bold yellow', # Estilo para unidades
    'header': 'bg:#005f00 #ffffff bold',
    'footer': 'bg:#444444 #ffffff',
    'current-path': '#aaddff italic',
    'error-message': 'bg:ansired #ffffff',
})

# --- Función para obtener unidades en Windows ---
def get_windows_drives() -> List[str]:
    """Obtiene una lista de letras de unidad válidas en Windows (ej: ['C:', 'D:'])."""
    drives = []
    if platform.system() == "Windows":
        # Usar string.ascii_uppercase para iterar A-Z
        possible_drives = (f"{char}:" for char in string.ascii_uppercase)
        for drive in possible_drives:
            # os.path.exists es más seguro que probar a listar
            if os.path.exists(drive + os.sep): # Añadir separador para validar montaje
                drives.append(drive)
    return drives
# -------------------------------------------

class FileBrowser:
    """ Navegador TUI con soporte básico para cambio de unidad en Windows. """
    def __init__(self, start_path: str = ".", select_dirs_only: bool = True):
        abs_start_path = os.path.abspath(start_path if start_path else ".")
        if not os.path.isdir(abs_start_path):
            logger.warning(f"Ruta TUI '{abs_start_path}' inválida, usando dir actual.")
            abs_start_path = os.path.abspath(".")
        self.current_path = abs_start_path
        self.select_dirs_only = select_dirs_only
        self.items: List[str] = []
        self.selected_index = 0
        self.message = ""
        self.result: Optional[str] = None
        self.exit_requested = False
        # --- Variable para saber si estamos mostrando unidades ---
        self.showing_drives = False
        # ------------------------------------------------------
        self._update_items()

    def _is_windows_root(self) -> bool:
        """Comprueba si estamos en la raíz virtual de unidades de Windows."""
        # Consideramos raíz si el path actual es solo una letra de unidad (C:, D:)
        # y el directorio padre es el mismo (indicador de raíz de unidad)
        # O si estamos en el estado especial 'showing_drives'
        if platform.system() != "Windows":
            return self.current_path == '/' # Raíz en Unix-like

        # Comprobar si es raíz de una unidad (C:\, D:\)
        if len(self.current_path) == 3 and self.current_path.endswith(':' + os.sep):
             return True
        # Comprobar si es solo la letra de unidad (C:, D:) - Menos probable pero por si acaso
        if len(self.current_path) == 2 and self.current_path.endswith(':'):
             return True

        return False

    def _get_drive_list_or_show_root(self):
        """Muestra la lista de unidades (Windows) o la raíz Unix."""
        if platform.system() == "Windows":
            self.items = get_windows_drives()
            self.showing_drives = True
            self.current_path = "Unidades del Sistema" # Texto indicador
            self.selected_index = 0
            self.message = "Selecciona una unidad con [Enter]"
        else: # Linux/macOS
             self.current_path = "/"
             self.showing_drives = False # No hay estado especial de unidades
             self._update_items() # Listar contenido de la raíz '/'

    def _update_items(self):
        """Actualiza la lista de items, manejando unidades en Windows."""
        previous_selection = self.items[self.selected_index] if self.items and 0 <= self.selected_index < len(self.items) else None
        self.items = []
        self.message = ""
        self.showing_drives = False # Por defecto no mostramos unidades

        try:
            # Caso especial: Si queremos ver las unidades en Windows (o raíz en Unix)
            if self.current_path == "Unidades del Sistema": # Estado especial
                 self._get_drive_list_or_show_root()
                 return # Ya hemos poblado self.items

            # Verificar acceso al directorio actual
            if not os.path.isdir(self.current_path) or not os.access(self.current_path, os.R_OK):
                self.message = "Error: Directorio inválido o permiso denegado"
                # Intentar ir a la lista de unidades/raíz si falla el directorio actual
                self._get_drive_list_or_show_root()
                return

            # --- Lógica de listado normal ---
            parent_dir = os.path.abspath(os.path.join(self.current_path, os.pardir))

            # Añadir ".." o "[Unidades]" / "[Raíz /]"
            # Si estamos en C:\, el padre es C:\, no añadir ".." normal
            # En Linux/macOS, si estamos en "/", el padre es "/", no añadir ".."
            is_root_of_system = (platform.system() == "Windows" and self.current_path == parent_dir) or \
                                (platform.system() != "Windows" and self.current_path == "/")

            if not is_root_of_system:
                 self.items.append("..")
            # Opción para volver a la selección de unidades/raíz
            if platform.system() == "Windows":
                 self.items.insert(0, "[Unidades...]") # Opción para ir a la lista de discos
            # else: # En Linux/macOS, podríamos poner "[Ir a /]" pero es menos necesario
                 # self.items.insert(0, "[Ir a /]")

            content = sorted(os.listdir(self.current_path), key=lambda x: (not os.path.isdir(os.path.join(self.current_path, x)), x.lower()))
            dirs = []
            files = []
            for item_name in content:
                 item_path = os.path.join(self.current_path, item_name)
                 try:
                     if os.path.isdir(item_path): dirs.append(item_name)
                     elif not self.select_dirs_only and os.path.isfile(item_path): files.append(item_name)
                 except OSError: logger.debug(f"Acceso omitido: {item_path}")

            self.items.extend(dirs)
            self.items.extend(files)

            # Intentar restaurar selección
            if previous_selection and previous_selection in self.items:
                 try: self.selected_index = self.items.index(previous_selection)
                 except ValueError: self.selected_index = 0
            else: self.selected_index = 0

        # --- Manejo de Errores ---
        except Exception as e:
            self.message = f"Error: {e}"
            logger.exception("Error inesperado actualizando items del navegador TUI")
            # En caso de error grave, intentar mostrar unidades/raíz como fallback seguro
            self._get_drive_list_or_show_root()

        # Asegurar índice válido
        if not self.items: self.selected_index = 0
        else: self.selected_index = max(0, min(self.selected_index, len(self.items) - 1))


    def _get_formatted_items(self) -> List[Tuple[str, str]]:
        """Genera la lista de tuplas (style_str, text) para el control."""
        result: List[Tuple[str, str]] = []
        if not self.items: result.append(('', '[Vacío o Inaccesible]')); return result

        for i, item_name in enumerate(self.items):
            style = ''
            display_name = item_name
            is_dir = False
            is_drive = False # Nuevo flag

            if item_name == "..": is_dir = True
            elif item_name == "[Unidades...]" or item_name == "[Ir a /]": is_dir = True # Tratar como directorio especial
            elif self.showing_drives: # Si estamos mostrando unidades
                 is_drive = True
                 is_dir = True # Las unidades actúan como directorios
                 display_name = f"[{item_name}]" # Mostrar entre corchetes
            else: # Ítem normal
                 try:
                     path_to_check = os.path.join(self.current_path, item_name)
                     if os.path.isdir(path_to_check): is_dir = True; display_name += "/"
                 except OSError: display_name += " (?)"

            # Aplicar estilo
            if i == self.selected_index: style = 'class:list-item.selected'
            elif is_drive: style = 'class:list-item.drive' # Estilo para unidades
            elif is_dir: style = 'class:list-item.directory'
            else: style = 'class:list-item.file'

            result.append((style, display_name))
            if i < len(self.items) - 1: result.append(('', '\n'))
        return result

    def _get_cursor_point(self) -> Point:
        """Devuelve la posición del cursor como un objeto Point(y, x)."""
        return Point(y=self.selected_index, x=0)

    def _build_layout(self):
        """Construye el layout de la TUI."""
        # ... (Header y list_window iguales que antes, usando _get_formatted_items y _get_cursor_point)...
        def get_header_text():
            max_width = os.get_terminal_size().columns - len(" ProyScan Navegador | Dir: ") - 2
            path_display = self.current_path
            if len(path_display) > max_width: path_display = "..." + path_display[-(max_width-3):]
            return [('class:header', ' ProyScan Navegador |'), ('class:current-path', f' Dir: {path_display} ')]
        header = Window(FormattedTextControl(text=get_header_text), height=1)

        list_control = FormattedTextControl(text=self._get_formatted_items, focusable=True, key_bindings=self._get_key_bindings(), get_cursor_position=self._get_cursor_point)
        list_window = Window(content=list_control, wrap_lines=False, right_margins=[ScrollbarMargin(display_arrows=True)])

        def get_footer_text():
            controls = "[↑/↓] Mover [PgUp/Dn] Saltar [Enter] Entrar/Sel. [S] Sel. Actual [Esc/Q] Salir"
            if self.message: return [('class:footer', controls), ('', ' | '), ('class:error-message', f' {self.message} ')]
            else: return [('class:footer', controls)]
        footer = Window(FormattedTextControl(text=get_footer_text), height=1)

        return Layout(HSplit([header, list_window, footer]))

    def _get_key_bindings(self):
        """Define las acciones de las teclas, incluyendo cambio de unidad."""
        kb = KeyBindings()

        # ... (Navegación Up/Down/PgUp/PgDn/Home/End igual que antes) ...
        @kb.add('up')
        def _(event): self.selected_index = max(0, self.selected_index - 1)
        @kb.add('down')
        def _(event):
            if self.items: self.selected_index = min(len(self.items) - 1, self.selected_index + 1)
        @kb.add('pageup')
        def _(event):
             visible_height = event.app.output.get_size().rows - 3
             self.selected_index = max(0, self.selected_index - max(1, visible_height))
        @kb.add('pagedown')
        def _(event):
            if self.items:
                visible_height = event.app.output.get_size().rows - 3
                self.selected_index = min(len(self.items) - 1, self.selected_index + max(1, visible_height))
        @kb.add('home')
        def _(event): self.selected_index = 0
        @kb.add('end')
        def _(event):
            if self.items: self.selected_index = len(self.items) - 1


        @kb.add('enter')
        def _(event):
            if not self.items or self.selected_index >= len(self.items): return
            selected_item_name = self.items[self.selected_index]

            # --- LÓGICA MODIFICADA PARA ENTER ---
            if self.showing_drives:
                # Seleccionando una unidad de disco (Windows)
                drive_letter = selected_item_name
                target_path = os.path.abspath(drive_letter + os.sep)
                if os.path.isdir(target_path):
                    self.current_path = target_path
                    self.showing_drives = False # Salir del modo de unidades
                    self._update_items()
                    self.selected_index = 0
                else:
                    self.message = f"No se puede acceder a la unidad {drive_letter}"
            elif selected_item_name == "[Unidades...]" or selected_item_name == "[Ir a /]":
                # Ir a la lista de unidades (Win) o a la raíz (Unix)
                self._get_drive_list_or_show_root()
            elif selected_item_name == "..":
                 parent = os.path.dirname(self.current_path)
                 # Condición extra para Windows: Si el padre es solo C:, ir a unidades
                 if platform.system() == "Windows" and len(parent) == 2 and parent.endswith(':'):
                      self._get_drive_list_or_show_root()
                 elif parent != self.current_path: # Comprobar que realmente subimos
                      self.current_path = parent
                      self._update_items(); self.selected_index = 0
                 else:
                      self.message = "Ya estás en la raíz" # O ya estamos en la lista de unidades
            else:
                # Intentar entrar en directorio o seleccionar archivo
                selected_path = os.path.abspath(os.path.join(self.current_path, selected_item_name))
                is_dir_selected = False
                try:
                    if os.path.isdir(selected_path): is_dir_selected = True
                except OSError as e: self.message = f"Error acceso: {e.filename}"; return

                if is_dir_selected:
                    try:
                        os.listdir(selected_path) # Intento rápido de acceso
                        self.current_path = selected_path
                        self._update_items(); self.selected_index = 0
                    except PermissionError: self.message = "Permiso denegado"; return
                    except Exception as e: self.message = f"Error al entrar: {e}"; return
                elif not self.select_dirs_only and os.path.isfile(selected_path):
                     self.result = selected_path; self.exit_requested = True; event.app.exit(result=self.result)
                else:
                     self.message = f"'{selected_item_name}' no es un directorio válido."
            # --- FIN LÓGICA MODIFICADA ---


        @kb.add('s')
        def _(event):
            # No permitir seleccionar el estado "Unidades del Sistema"
            if not self.showing_drives:
                 self.result = self.current_path
                 self.exit_requested = True
                 event.app.exit(result=self.result)
            else:
                 self.message = "Navega hasta un directorio real para seleccionarlo"


        @kb.add('escape')
        @kb.add('q')
        def _(event):
            self.result = None; self.exit_requested = True; event.app.exit(result=None)

        return kb

    def run(self) -> Optional[str]:
        # ... (Igual que la versión anterior) ...
        layout = self._build_layout(); bindings = self._get_key_bindings()
        app = Application(layout=layout, key_bindings=bindings, style=default_style, full_screen=True, mouse_support=True)
        self.result = None
        try: app.run()
        except Exception as e: logger.error("Error TUI", exc_info=True)
        finally:
             # Limpieza opcional
             # if platform.system() == "Windows": os.system('cls')
             # else: os.system('clear')
             pass # La limpieza la hace ahora el llamador
        return self.result


# --- Función de ayuda (sin cambios) ---
def browse_for_directory(start_path: str = ".") -> Optional[str]:
     # ... (igual que antes) ...
    logger.info(f"Iniciando navegador TUI en: {start_path}")
    abs_start_path = os.path.abspath(start_path if start_path else ".")
    if not os.path.isdir(abs_start_path): logger.warning(f"Ruta TUI '{abs_start_path}' inválida, usando dir actual."); abs_start_path = os.path.abspath(".")
    browser = FileBrowser(start_path=abs_start_path, select_dirs_only=True)
    selected_path = browser.run()
    # Limpieza pantalla post-ejecución
    if platform.system() == "Windows": os.system('cls')
    else: os.system('clear')
    if selected_path: logger.info(f"Dir seleccionado TUI: {selected_path}")
    else: logger.info("Navegador TUI cancelado/fallido.")
    return selected_path