# proyscan/models.py
# Define estructuras de datos para mejorar la claridad y el tipado
from typing import TypedDict, List, Optional, Dict, Any

class DependencyInfo(TypedDict):
    type: str # 'interna', 'externa', 'interna_rota', 'desconocida', 'url', 'biblioteca'
    path: str # Ruta resuelta (si es interna) o nombre/url original

# Metadatos asociados a cada archivo en el JSON
class Metadata(TypedDict):
    path: str
    size_bytes: Optional[int]
    status: str # ok, ignored, binary, read_error, too_large, access_error, etc.
    encoding: Optional[str]
    language: Optional[str]
    line_count: Optional[int]
    dependencies: Optional[List[DependencyInfo]]
    referenced_by: Optional[List[str]] 
    
# Objeto completo para un archivo en la lista final del JSON
class FileObject(TypedDict):
    metadata: Metadata
    content_lines: Optional[List[str]]
    error_message: Optional[str]

# Estructura del JSON de salida final
class OutputJson(TypedDict):
    files: List[FileObject] 

# Estructura para dependencias (Fase 1+)

class ScanInfo(TypedDict):
    project_name: str
    original_project_path: str
    scan_timestamp: str # ISO 8601 format
    scan_id: str
    output_directory: str
    parameters_used: Dict[str, Any] # ej: {'debug_mode': True, 'ignore_file_used': 'temporal'}