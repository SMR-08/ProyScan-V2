# proyscan/models.py
# Define estructuras de datos para mejorar la claridad y el tipado
from typing import TypedDict, List, Optional, Dict, Any

# Metadatos asociados a cada archivo en el JSON
class Metadata(TypedDict):
    path: str
    size_bytes: Optional[int]
    status: str # ok, ignored, binary, read_error, too_large, access_error, etc.
    encoding: Optional[str]
    language: Optional[str]
    line_count: Optional[int]
    # Campo para futuras dependencias (Fase 1+)
    dependencias: Optional[List[Dict[str, str]]] # Ej: [{'tipo': 'interna', 'path': '...'}, ...]

# Objeto completo para un archivo en la lista final del JSON
class FileObject(TypedDict):
    metadata: Metadata
    content_lines: Optional[List[str]]
    error_message: Optional[str]

# Estructura del JSON de salida final
class OutputJson(TypedDict):
    archivos: List[FileObject]

# Estructura para dependencias (Fase 1+)
class DependencyInfo(TypedDict):
    tipo: str # 'interna', 'externa', 'interna_rota', 'desconocida', 'url', 'biblioteca'
    path: str # Ruta resuelta (si es interna) o nombre/url original