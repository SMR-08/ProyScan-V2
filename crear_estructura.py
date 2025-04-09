import os

# --- Estructura de Directorios y Archivos a Crear ---
# Basado en el roadmap de modularización propuesto

# Lista de directorios a crear (incluyendo subdirectorios)
directorios = [
    "proyscan",                     # Directorio principal del paquete
    "proyscan/utils",               # Subdirectorio para utilidades
    "proyscan/dependency_analysis", # Subdirectorio para análisis de dependencias
    "tests"                         # Directorio para pruebas (buena práctica)
]

# Lista de archivos a crear (vacíos por ahora)
# Usamos rutas relativas desde el directorio raíz del proyecto
archivos = [
    "proyscan.py",                  # Script principal ejecutable (fuera del paquete)
    "proyscan/__init__.py",         # Hace que 'proyscan' sea un paquete importable
    "proyscan/core.py",
    "proyscan/config.py",
    "proyscan/tree_generator.py",
    "proyscan/ignore_handler.py",
    "proyscan/models.py",           # Para definir modelos de datos (dataclasses/TypedDict)
    "proyscan/utils/__init__.py",
    "proyscan/utils/path_utils.py",
    "proyscan/utils/file_utils.py",
    "proyscan/dependency_analysis/__init__.py",
    "proyscan/dependency_analysis/analyzer.py",
    "proyscan/dependency_analysis/base_parser.py",  # Aunque vacío, define la intención
    "proyscan/dependency_analysis/python_parser.py",
    "proyscan/dependency_analysis/regex_parser.py",
    "proyscan/dependency_analysis/html_parser.py",
    "proyscan/dependency_analysis/css_parser.py",
    "proyscan/dependency_analysis/external_runners.py", # Para futura lógica subprocess
    "tests/__init__.py",            # Para que 'tests' sea reconocible
    "requirements.txt",             # Archivo de dependencias
    ".ignore",                      # Archivo de exclusiones de ProyScan
    "README.md"                     # Documentación principal
]

# --- Lógica de Creación ---

print("Creando la estructura de directorios y archivos para ProyScan...")

# Crear directorios
for dir_path in directorios:
    try:
        # exist_ok=True evita errores si el directorio ya existe
        os.makedirs(dir_path, exist_ok=True)
        print(f"Directorio creado o ya existente: {dir_path}")
    except OSError as e:
        print(f"ERROR: No se pudo crear el directorio {dir_path}: {e}")
        # Considerar salir si un directorio base falla
        # exit(1)

# Crear archivos (solo si no existen para evitar sobrescribir trabajo previo)
for file_path in archivos:
    if not os.path.exists(file_path):
        try:
            # 'w' crea el archivo si no existe, 'a' también lo haría
            # Usar 'with' asegura que el archivo se cierre correctamente
            with open(file_path, 'w') as f:
                pass # Solo queremos crear el archivo vacío
            print(f"Archivo creado: {file_path}")
        except OSError as e:
            print(f"ERROR: No se pudo crear el archivo {file_path}: {e}")
    else:
        print(f"Archivo ya existente, omitido: {file_path}")

print("\n¡Estructura base creada exitosamente!")
print("Puedes empezar a mover el código existente a los módulos correspondientes.")
print("Recuerda añadir esta estructura a Git (excepto archivos sensibles si los hubiera).")