# proyscan/config.py
import os

# --- Constantes de Archivos ---
ARCHIVO_ESTRUCTURA = "estructura_archivos.txt"
ARCHIVO_CONTENIDO = "contenido_archivos.json"
ARCHIVO_IGNORAR = ".ignore"

# --- Constantes de Procesamiento ---
EXTENSIONES_BINARIAS = {
    # ... (lista sin cambios) ...
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
    # ... (mapa sin cambios) ...
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

# --- Otras Configuraciones ---
ANALIZAR_DEPENDENCIAS = True # Mantenemos esto