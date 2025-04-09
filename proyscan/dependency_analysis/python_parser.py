# proyscan/dependency_analysis/python_parser.py
import ast
import os
from typing import List, Set, Dict, Optional

# Importar funciones de utilidad y modelos
from ..utils.path_utils import resolver_import_python, es_stdlib, normalizar_ruta
from ..models import DependencyInfo # Usar el TypedDict definido

class PythonImportVisitor(ast.NodeVisitor):
    """
    Visita nodos AST para encontrar declaraciones de importación.
    """
    def __init__(self, ruta_archivo_actual_rel: str, archivos_proyecto: Set[str]):
        self.ruta_actual_rel = ruta_archivo_actual_rel
        self.archivos_proyecto = archivos_proyecto
        # Usamos un set para evitar duplicados de rutas resueltas
        self.dependencias_encontradas: Set[DependencyInfo] = set()
        # Para manejar stdlib y bibliotecas
        self.modulos_externos: Set[str] = set()

    def _clasificar_y_agregar(self, nombre_modulo: str, nivel: int):
        """Intenta resolver y clasificar una importación."""

        # 1. Comprobar si es librería estándar (solo para absolutas)
        if nivel == 0 and es_stdlib(nombre_modulo):
            # print(f"[DEBUG Visitor] StdLib detectado: {nombre_modulo}")
            self.modulos_externos.add(nombre_modulo.split('.')[0]) # Guardar solo el nombre base
            return # No necesita más resolución

        # 2. Intentar resolver como archivo/paquete interno
        ruta_resuelta_rel = resolver_import_python(
            nombre_modulo, nivel, self.ruta_actual_rel, self.archivos_proyecto
        )

        if ruta_resuelta_rel:
            # Encontrado internamente
            dep_info = DependencyInfo(tipo='interna', path=ruta_resuelta_rel)
            # Convertir a tupla para poder añadir a set (los dicts no son hasheables)
            self.dependencias_encontradas.add(tuple(sorted(dep_info.items())))
        else:
            # No encontrado internamente y no es stdlib (asumimos biblioteca externa o error)
            if nivel == 0: # Solo consideramos externos los absolutos no resueltos
                 # print(f"[DEBUG Visitor] Externo/No resuelto: {nombre_modulo}")
                 self.modulos_externos.add(nombre_modulo.split('.')[0]) # Nombre base
            # else: # Los relativos no resueltos podrían marcarse como 'interna_rota'
            #     dep_info = DependencyInfo(tipo='interna_rota', path=f"Relativo: {nombre_modulo} desde {self.ruta_actual_rel}")
            #     self.dependencias_encontradas.add(tuple(sorted(dep_info.items())))
            # Simplificación: por ahora solo capturamos los resueltos internos y los externos/stdlib.

    def visit_Import(self, node: ast.Import):
        # print(f"[DEBUG Visitor] Visitando Import: {ast.dump(node)}")
        for alias in node.names:
            # Import simple: import os, import mi_paquete.utils
            # Nivel siempre es 0 aquí
            self._clasificar_y_agregar(alias.name, 0)
        self.generic_visit(node) # Visitar nodos hijos si los hubiera

    def visit_ImportFrom(self, node: ast.ImportFrom):
        # print(f"[DEBUG Visitor] Visitando ImportFrom: {ast.dump(node)}")
        # from . import utils (node.module es None, nivel > 0)
        # from .utils import helper (node.module es 'utils', nivel > 0)
        # from ..config import SETTINGS (node.module es 'config', nivel > 0)
        # from mi_paquete import utils (node.module es 'mi_paquete', nivel == 0)
        # from os import path (node.module es 'os', nivel == 0)

        # Ignoramos los nombres importados específicos (ej: 'path' en 'from os import path')
        # solo nos interesa el módulo base ('os') para la dependencia de archivo/paquete.
        if node.module: # Puede ser None en 'from . import X'
             self._clasificar_y_agregar(node.module, node.level)
        elif node.level > 0: # Caso 'from . import X' o 'from .. import X'
             # Consideramos el directorio base como la "dependencia"
             self._clasificar_y_agregar('', node.level) # Módulo vacío, nivel indica relativo

        self.generic_visit(node)

    def obtener_dependencias(self) -> List[DependencyInfo]:
        """Devuelve la lista final de dependencias únicas."""
        lista_final: List[DependencyInfo] = []
        # Añadir internas resueltas
        for dep_tuple in self.dependencias_encontradas:
            lista_final.append(dict(dep_tuple)) # Convertir tupla de nuevo a dict

        # Añadir externas/stdlib
        for modulo_ext in sorted(list(self.modulos_externos)):
             # Determinar si es stdlib o biblioteca
             tipo = 'stdlib' if es_stdlib(modulo_ext) else 'biblioteca'
             lista_final.append(DependencyInfo(tipo=tipo, path=modulo_ext))

        # Ordenar para consistencia (opcional)
        lista_final.sort(key=lambda x: (x['tipo'], x['path']))
        return lista_final


def analizar_python(
    contenido_lineas: List[str],
    ruta_archivo_rel: str,
    archivos_proyecto: Set[str]
    # dir_proyecto_raiz: str # No necesario si trabajamos con relativas y archivos_proyecto
) -> Optional[List[DependencyInfo]]:
    """
    Parsea código Python usando AST y extrae dependencias.
    """
    codigo_completo = "\n".join(contenido_lineas)
    if not codigo_completo.strip():
        return [] # Archivo vacío

    try:
        arbol_ast = ast.parse(codigo_completo)
        visitor = PythonImportVisitor(ruta_archivo_rel, archivos_proyecto)
        visitor.visit(arbol_ast)
        return visitor.obtener_dependencias()
    except SyntaxError as e:
        print(f"      * Advertencia: Error de sintaxis en {ruta_archivo_rel}, no se analizan dependencias Python. Error: {e}")
        return None # O devolver lista vacía, o añadir al error_message principal
    except Exception as e:
        print(f"      * Advertencia: Error inesperado analizando AST de {ruta_archivo_rel}: {e}")
        # Considerar loggear traceback
        return None