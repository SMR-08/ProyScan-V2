# proyscan/dependency_analysis/python_parser.py
import ast
import os
import logging # Importar
from typing import List, Set, Dict, Optional

from ..utils.path_utils import resolver_import_python, es_stdlib, normalizar_ruta
from ..models import DependencyInfo

# Obtener logger
logger = logging.getLogger(__name__) # Usa 'proyscan.dependency_analysis.python_parser'

class PythonImportVisitor(ast.NodeVisitor):
    """Visita nodos AST para encontrar importaciones."""
    def __init__(self, ruta_archivo_actual_rel: str, archivos_proyecto: Set[str]):
        self.ruta_actual_rel = ruta_archivo_actual_rel
        self.archivos_proyecto = archivos_proyecto
        self.dependencias_encontradas: Set[tuple] = set() # Usar tuplas para set
        self.modulos_externos: Set[str] = set()
        logger.debug(f"PythonImportVisitor inicializado para: {ruta_archivo_actual_rel}") # DEBUG

    def _clasificar_y_agregar(self, nombre_modulo: str, nivel: int):
        logger.debug(f"Clasificando: Mod='{nombre_modulo}', Nivel={nivel}") # DEBUG
        if nivel == 0 and es_stdlib(nombre_modulo):
            mod_base = nombre_modulo.split('.')[0]
            logger.debug(f"  -> Detectado como StdLib: {mod_base}") # DEBUG
            self.modulos_externos.add(mod_base)
            return

        ruta_resuelta_rel = resolver_import_python(
            nombre_modulo, nivel, self.ruta_actual_rel, self.archivos_proyecto
        )

        if ruta_resuelta_rel:
            logger.debug(f"  -> Resuelto Internamente a: '{ruta_resuelta_rel}'") # DEBUG
            dep_info = DependencyInfo(tipo='interna', path=ruta_resuelta_rel)
            self.dependencias_encontradas.add(tuple(sorted(dep_info.items())))
        else:
            if nivel == 0: # Solo absolutos no resueltos son bibliotecas/externos
                 mod_base = nombre_modulo.split('.')[0]
                 logger.debug(f"  -> No resuelto internamente (Absoluto): Asumiendo Biblioteca/Externa '{mod_base}'") # DEBUG
                 self.modulos_externos.add(mod_base)
            else: # Relativos no resueltos son rotos
                 path_display = f"{'.' * nivel}{nombre_modulo}" if nombre_modulo else '.' * nivel
                 logger.debug(f"  -> No resuelto internamente (Relativo): Marcando como Rota '{path_display}'") # DEBUG
                 dep_info = DependencyInfo(tipo='interna_rota', path=f"'{path_display}' desde '{self.ruta_actual_rel}'")
                 self.dependencias_encontradas.add(tuple(sorted(dep_info.items())))


    def visit_Import(self, node: ast.Import):
        logger.debug(f"Visitando nodo Import: {[alias.name for alias in node.names]}") # DEBUG
        for alias in node.names:
            self._clasificar_y_agregar(alias.name, 0)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        modulo = node.module if node.module else '' # '' si es from . import ...
        logger.debug(f"Visitando nodo ImportFrom: Mod='{modulo}', Nivel={node.level}, Nombres={[alias.name for alias in node.names]}") # DEBUG
        # Clasificar basado en el módulo, no en los nombres específicos importados
        self._clasificar_y_agregar(modulo, node.level)
        self.generic_visit(node)

    def obtener_dependencias(self) -> List[DependencyInfo]:
        lista_final: List[DependencyInfo] = [dict(dep_tuple) for dep_tuple in self.dependencias_encontradas]
        for modulo_ext in sorted(list(self.modulos_externos)):
             tipo = 'stdlib' if es_stdlib(modulo_ext) else 'biblioteca'
             lista_final.append(DependencyInfo(tipo=tipo, path=modulo_ext))
        lista_final.sort(key=lambda x: (x['tipo'], x['path']))
        logger.debug(f"Dependencias Python finales: {lista_final}") # DEBUG
        return lista_final

def analizar_python(contenido_lineas: List[str], ruta_archivo_rel: str, archivos_proyecto: Set[str]) -> Optional[List[DependencyInfo]]:
    logger.debug(f"--- Iniciando análisis Python AST para {ruta_archivo_rel} ---") # DEBUG
    codigo_completo = "\n".join(contenido_lineas)
    if not codigo_completo.strip():
        logger.debug("Archivo Python vacío.") # DEBUG
        return []

    try:
        arbol_ast = ast.parse(codigo_completo)
        visitor = PythonImportVisitor(ruta_archivo_rel, archivos_proyecto)
        visitor.visit(arbol_ast)
        return visitor.obtener_dependencias()
    except SyntaxError as e:
        # Usar logger.warning para errores de sintaxis esperables
        logger.warning(f"Error de sintaxis en {ruta_archivo_rel}, no se analizan dependencias Python. Error: {e}")
        return None
    except Exception as e:
        # Usar logger.exception para errores inesperados durante el parseo AST
        logger.exception(f"Error inesperado analizando AST de {ruta_archivo_rel}")
        return None