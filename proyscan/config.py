# proyscan/config.py
import os

# --- Constantes de Archivos ---
ARCHIVO_ESTRUCTURA = "estructura_archivos.txt"
ARCHIVO_CONTENIDO = "contenido_archivos.json"
ARCHIVO_IGNORAR = ".ignore"

# --- Constantes de Procesamiento ---
EXTENSIONES_BINARIAS = {
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.ico',
    '.mp3', '.wav', '.ogg', '.flac', '.aac',
    '.mp4', '.avi', '.mkv', '.mov', '.wmv',
    '.exe', '.dll', '.so', '.dylib', '.o', '.a',
    '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2',
    '.pdf',
    '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.odt', '.ods', '.odp',
    '.sqlite', '.db', '.mdb',
    '.pyc', '.pyo',
    '.class', '.jar',
    '.woff', '.woff2', '.ttf', '.otf', '.eot'
}

MAPA_LENGUAJES = {
    '.py': 'python', '.js': 'javascript', '.html': 'html', '.htm': 'html',
    '.css': 'css', '.json': 'json', '.xml': 'xml', '.yaml': 'yaml', '.yml': 'yaml',
    '.md': 'markdown', '.txt': 'text', '.log': 'log', '.sh': 'shell',
    '.bash': 'shell', '.zsh': 'shell', '.bat': 'batch', '.cmd': 'batch',
    '.ps1': 'powershell', '.java': 'java', '.c': 'c', '.cpp': 'cpp',
    '.cs': 'csharp', '.go': 'go', '.php': 'php', '.rb': 'ruby',
    '.swift': 'swift', '.kt': 'kotlin', '.rs': 'rust', '.sql': 'sql',
    '.r': 'r', '.R': 'r', '.pl': 'perl',
}
LENGUAJE_DEFECTO = 'text'

MAX_TAMANO_MB_TEXTO = 5
MAX_TAMANO_BYTES_TEXTO = MAX_TAMANO_MB_TEXTO * 1024 * 1024

# --- Determinación del Directorio del Script/Proyecto ---
# Se asume que el script principal (proyscan.py) o el punto de entrada
# estará en la raíz del proyecto escaneado.
try:
    # Si __file__ está definido (ejecución normal)
    # Queremos la ruta del directorio que *contiene* el script de entrada (proyscan.py)
    # que estará UN NIVEL POR ENCIMA del paquete 'proyscan'
    DIR_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    # Si se ejecuta interactivamente o __file__ no está, usar directorio actual
    DIR_PROYECTO = os.getcwd()
    print(f"Advertencia: No se pudo determinar DIR_PROYECTO desde __file__, usando directorio actual: {DIR_PROYECTO}")

# --- Otras Configuraciones (Placeholder) ---
# Aquí podrían ir flags para habilitar/deshabilitar análisis de dependencias, etc.
ANALIZAR_DEPENDENCIAS = True # Preparado para el futuro