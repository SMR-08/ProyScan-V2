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
    # Web Frontend
    '.html': 'html', '.htm': 'html',
    '.css': 'css', '.scss': 'scss', '.sass': 'sass', '.less': 'less', # CSS Preprocessors
    '.js': 'javascript', '.mjs': 'javascript', '.cjs': 'javascript',
    '.jsx': 'jsx', # JavaScript con JSX
    '.ts': 'typescript', # TypeScript
    '.tsx': 'tsx', # TypeScript con JSX
    '.vue': 'vue', # Vue.js Single File Components

    # Web Backend / General
    '.py': 'python',
    '.php': 'php',
    '.java': 'java', # Java
    '.cs': 'csharp', # C#
    '.go': 'go',
    '.rb': 'ruby',
    '.rs': 'rust',
    '.swift': 'swift',
    '.kt': 'kotlin', # Kotlin
    '.scala': 'scala', # Scala

    # Datos y Configuración
    '.json': 'json',
    '.xml': 'xml',
    '.yaml': 'yaml', '.yml': 'yaml',
    '.toml': 'toml',
    '.ini': 'ini',
    '.env': 'env',
    '.sql': 'sql',
    '.graphql': 'graphql', '.gql': 'graphql',

    # Scripting / Shell
    '.sh': 'shell', '.bash': 'shell', '.zsh': 'shell',
    '.bat': 'batch', '.cmd': 'batch',
    '.ps1': 'powershell',
    '.pl': 'perl',
    '.lua': 'lua',

    # Documentación / Texto
    '.md': 'markdown',
    '.txt': 'text',
    '.log': 'log',
    '. R': 'r', '.r': 'r',

    # Otros (pueden requerir análisis más específico)
    '.c': 'c',
    '.cpp': 'cpp', '.cxx': 'cpp', '.cc': 'cpp', '.hpp': 'cpp', '.hxx': 'cpp', '.h': 'c', # C/C++ Headers también
    # Añadir más según sea necesario
}
LENGUAJE_DEFECTO = 'text'

MAX_TAMANO_MB_TEXTO = 5
MAX_TAMANO_BYTES_TEXTO = MAX_TAMANO_MB_TEXTO * 1024 * 1024

# --- Otras Configuraciones ---
ANALIZAR_DEPENDENCIAS = True # Mantenemos esto

# --- Patrones Comunes para .ignore Interactivo ---
# Estructura: { "Categoría Display": { "patrón": "Descripción (opcional)", ... } }
# O: { "Categoría Display": ["patrón1", "patrón2"] } (si no necesitamos descripción)

PATRONES_IGNORE_COMUNES = {
    "Sistemas de Control de Versiones": {
        ".git/": "Directorio de metadatos de Git",
        ".svn/": "Directorio de metadatos de Subversion",
        ".hg/": "Directorio de metadatos de Mercurial",
        ".bzr/": "Directorio de metadatos de Bazaar",
    },
    "Python": {
        "__pycache__/": "Caché de bytecode de Python",
        "*.pyc": "Archivos de bytecode compilado",
        "*.pyo": "Archivos de bytecode optimizado (obsoleto)",
        "*.pyd": "Archivos de extensión compilados (Windows)",
        ".*.egg": "Archivos Egg (distribución antigua)",
        "*.egg-info/": "Metadatos de Eggs",
        ".env*": "Archivos de variables de entorno (potencialmente sensibles)",
        "*.venv/": "Entornos virtuales comunes (venv, .venv, env)",
        "env/": "Entorno virtual",
        "venv/": "Entorno virtual",
        ".pytest_cache/": "Caché de Pytest",
        ".mypy_cache/": "Caché de MyPy",
        ".ruff_cache/": "Caché de Ruff",
        "build/": "Directorio de construcción (setuptools, etc.)",
        "dist/": "Directorio de distribución",
        "htmlcov/": "Directorio de cobertura HTML (coverage.py)",
        ".cache": "Directorios de caché genéricos", # Cuidado, puede ser muy amplio
    },
    "JavaScript / Node.js": {
        "node_modules/": "Dependencias de Node.js (muy grande)",
        "dist/": "Directorio de distribución/compilación",
        "build/": "Directorio de construcción",
        "coverage/": "Directorio de cobertura de tests",
        "*.log": "Archivos de log genéricos",
        "npm-debug.log*": "Logs de debug de NPM",
        "yarn-debug.log*": "Logs de debug de Yarn",
        "yarn-error.log*": "Logs de error de Yarn",
        "pnpm-debug.log*": "Logs de debug de PNPM",
        ".npm/": "Caché de NPM",
        ".yarn/": "Metadatos/Caché de Yarn",
        ".pnp.*": "Archivos Plug'n'Play de Yarn",
    },
    "IDEs y Editores": {
        ".vscode/": "Configuración de VS Code",
        ".idea/": "Configuración de JetBrains IDEs",
        "*.iml": "Archivos de módulo de JetBrains",
        "*.sublime-project": "Proyecto de Sublime Text",
        "*.sublime-workspace": "Workspace de Sublime Text",
        ".project": "Proyecto de Eclipse",
        ".classpath": "Classpath de Eclipse",
        ".settings/": "Configuración de Eclipse",
        "nbproject/": "Proyecto de NetBeans",
    },
    "Sistema Operativo": {
        ".DS_Store": "Metadatos de Finder (macOS)",
        ".AppleDouble": "Recursos de archivo (macOS)",
        ".LSOverride": "Configuración de Launch Services (macOS)",
        ".Spotlight-V100": "Índice de Spotlight (macOS)",
        ".Trashes": "Papelera (macOS)",
        "Thumbs.db": "Caché de miniaturas (Windows)",
        "ehthumbs.db": "Caché de miniaturas (Windows)",
        "desktop.ini": "Configuración de carpetas (Windows)",
        "*~": "Archivos de backup comunes (Linux/Unix)",
        "*.swp": "Archivo swap de Vim",
        "*.swo": "Archivo swap de Vim",
    },
    "Archivos Comprimidos/Binarios Comunes": {
        "*.zip": "Archivo ZIP",
        "*.rar": "Archivo RAR",
        "*.tar": "Archivo TAR",
        "*.gz": "Archivo Gzip",
        "*.bz2": "Archivo Bzip2",
        "*.7z": "Archivo 7zip",
        "*.pdf": "Documento PDF",
        "*.png": "Imagen PNG",
        "*.jpg": "Imagen JPEG",
        "*.jpeg": "Imagen JPEG",
        "*.gif": "Imagen GIF",
        "*.bmp": "Imagen BMP",
        "*.svg": "Gráfico Vectorial Escalable (puede ser texto, pero a menudo es asset)",
        "*.mp3": "Archivo de audio MP3",
        "*.mp4": "Archivo de vídeo MP4",
        "*.avi": "Archivo de vídeo AVI",
        "*.exe": "Ejecutable Windows",
        "*.dll": "Biblioteca Windows",
        "*.so": "Biblioteca Linux",
    }
    # Añadir más categorías: Java, PHP, Ruby, Go, Docker, Terraform...
}