# proyscan/dependency_analysis/python_parser.py
import ast
import os
import logging
from typing import List, Set, Dict, Optional, Tuple

# Importar funciones de utilidad y modelos
# Asegúrate de que path_utils tenga la versión más reciente de resolver_import_python
from ..utils.path_utils import resolver_import_python, es_stdlib, normalizar_ruta
from ..models import DependencyInfo # Usar el TypedDict definido

# Obtener logger
logger = logging.getLogger(__name__) # Usa 'proyscan.dependency_analysis.python_parser'

class PythonImportVisitor(ast.NodeVisitor):
    """
    Visita nodos AST para encontrar declaraciones de importación.
    """
    def __init__(self, ruta_archivo_actual_rel: str, archivos_proyecto: Set[str]):
        self.ruta_actual_rel = ruta_archivo_actual_rel
        self.archivos_proyecto = archivos_proyecto
        # Usamos tuplas (type, path) para poder añadirlas a un set y evitar duplicados exactos
        self.dependencias_encontradas: Set[tuple] = set()
        # Guardamos solo el nombre base del módulo externo/stdlib para evitar duplicados como 'os' y 'os.path'
        self.modulos_externos: Set[str] = set()
        logger.debug(f"PythonImportVisitor inicializado para: {ruta_archivo_actual_rel}")

    def _procesar_resolucion(self, resoluciones: List[Tuple[str, Optional[str]]]):
        """
        Clasifica y agrega dependencias basadas en la lista de resultados de resolución.
        Cada tupla en resoluciones es (nombre_original_importado, ruta_resuelta | None).
        """
        for nombre_original, ruta_resuelta_inicial in resoluciones:
            logger.debug(f"Procesando resolución: Original='{nombre_original}', ResueltaInicial='{ruta_resuelta_inicial}'")

            ruta_final_a_registrar = ruta_resuelta_inicial # Ruta a usar para el índice inverso

            if ruta_resuelta_inicial:
                # --- AJUSTE PAQUETES PARA ÍNDICE INVERSO ---
                # Si resolvimos a un __init__.py, pero el import original tenía más partes
                # (ej: from app import models -> nombre_original='app.models'),
                # intentamos encontrar el archivo específico (app/models.py) para el registro inverso.
                partes_original = nombre_original.split('.')
                # Comprobamos si es un __init__ y si el import original tenía submódulos/nombres
                # y NO es un import relativo que empiece justo con '.' (ej: from . import utils)
                if ruta_resuelta_inicial.endswith('/__init__.py') and len(partes_original) > 1 and not nombre_original.startswith('.'):
                    # Construir ruta al módulo/archivo específico como si fuera absoluto desde raíz
                    ruta_especifica_tentativa = os.path.join(*partes_original)
                    # Intentar encontrar .py para esa ruta específica
                    ruta_especifica_py = normalizar_ruta(ruta_especifica_tentativa + ".py")

                    if ruta_especifica_py in self.archivos_proyecto:
                        logger.debug(f"  -> Ajuste Paquete: Usando ruta específica '{ruta_especifica_py}' para índice inverso (encontrada).")
                        ruta_final_a_registrar = ruta_especifica_py # Usar esta para el registro inverso
                    else:
                         # Si no encontramos el archivo .py específico, mantenemos la dependencia
                         # hacia el __init__.py como indicador del paquete.
                         logger.debug(f"  -> Ajuste Paquete: No se encontró '{ruta_especifica_py}', se mantiene dependencia a '{ruta_resuelta_inicial}'")
                         # ruta_final_a_registrar ya es ruta_resuelta_inicial
                # --- FIN AJUSTE ---

                logger.debug(f"  -> Clasificado como INTERNA: '{ruta_final_a_registrar}'")
                # Guardamos la dependencia con la ruta final (puede ser .py o __init__.py)
                dep_info = DependencyInfo(type='internal', path=ruta_final_a_registrar)
                self.dependencias_encontradas.add(tuple(sorted(dep_info.items())))

            else: # No resuelto internamente
                # ¿Es stdlib o biblioteca externa? Usamos el nombre original para comprobar.
                modulo_base_original = nombre_original.split('.')[0]

                # Si empieza con '.', es un relativo que no se pudo resolver -> roto
                if nombre_original.startswith('.'):
                    logger.warning(f"  -> Import relativo no resuelto: Marcando como ROTA '{nombre_original}' desde '{self.ruta_actual_rel}'")
                    dep_info = DependencyInfo(type='internal_broken', path=f"Relative import '{nombre_original}' from '{self.ruta_actual_rel}'")
                    # Añadir la dependencia rota también para información
                    self.dependencias_encontradas.add(tuple(sorted(dep_info.items())))
                # Si no empieza con '.' y no se resolvió, comprobar si es stdlib
                elif es_stdlib(modulo_base_original):
                     logger.debug(f"  -> Clasificado como STDLIB: '{modulo_base_original}'")
                     self.modulos_externos.add(modulo_base_original)
                # Si no, asumir biblioteca externa
                else:
                     logger.debug(f"  -> Clasificado como LIBRARY: '{modulo_base_original}'")
                     self.modulos_externos.add(modulo_base_original)

    def visit_Import(self, node: ast.Import):
        """Procesa declaraciones 'import modulo'."""
        nombres = [alias.name for alias in node.names]
        logger.debug(f"Visitando nodo Import: {nombres}")
        # Nivel es siempre 0. Llamamos a resolver para cada módulo importado.
        for nombre in nombres:
             # Para 'import x', el módulo base es 'x', los nombres importados son irrelevantes aquí
             # pero pasamos una lista con el nombre base para consistencia con la firma de resolver.
             resoluciones = resolver_import_python(nombre, [nombre], 0, self.ruta_actual_rel, self.archivos_proyecto)
             self._procesar_resolucion(resoluciones)
        self.generic_visit(node) # Continuar visitando hijos si es necesario

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Procesa declaraciones 'from modulo import nombre1, nombre2'."""
        modulo_base = node.module if node.module else '' # Puede ser '' en 'from . import X'
        nombres_importados = [alias.name for alias in node.names]
        logger.debug(f"Visitando nodo ImportFrom: Mod='{modulo_base}', Nivel={node.level}, Nombres={nombres_importados}")

        # Llamar a resolver_import_python pasando el módulo base y los nombres específicos
        resoluciones = resolver_import_python(
            modulo_base,
            nombres_importados,
            node.level,
            self.ruta_actual_rel,
            self.archivos_proyecto
        )
        self._procesar_resolucion(resoluciones)
        self.generic_visit(node)

    def obtener_dependencias(self) -> List[DependencyInfo]:
        """Construye y devuelve la lista final de dependencias únicas."""
        lista_final: List[DependencyInfo] = []

        # Convertir tuplas de dependencias internas/rotas de nuevo a dicts
        for dep_tuple in self.dependencias_encontradas:
            lista_final.append(dict(dep_tuple)) # type: ignore [arg-type]

        # Añadir módulos externos/stdlib
        for modulo_ext in sorted(list(self.modulos_externos)):
             tipo = 'stdlib' if es_stdlib(modulo_ext) else 'library'
             lista_final.append(DependencyInfo(type=tipo, path=modulo_ext))

        # Ordenar para una salida consistente
        lista_final.sort(key=lambda x: (x['type'], x['path']))
        logger.debug(f"Dependencias Python finales para {self.ruta_actual_rel}: {lista_final}")
        return lista_final


def analizar_python(
    contenido_lineas: List[str],
    ruta_archivo_rel: str,
    archivos_proyecto: Set[str]
    # dir_proyecto_raiz: str # No es necesario si trabajamos con relativas y archivos_proyecto
) -> Optional[List[DependencyInfo]]:
    """
    Función principal para analizar dependencias de Python usando AST.
    """
    logger.debug(f"--- Iniciando análisis Python AST para {ruta_archivo_rel} ---")
    codigo_completo = "\n".join(contenido_lineas)
    if not codigo_completo.strip():
        logger.debug("Archivo Python vacío.")
        return [] # Devolver lista vacía para archivos vacíos

    try:
        arbol_ast = ast.parse(codigo_completo)
        visitor = PythonImportVisitor(ruta_archivo_rel, archivos_proyecto)
        visitor.visit(arbol_ast)
        return visitor.obtener_dependencias()
    except SyntaxError as e:
        logger.warning(f"Error de sintaxis en {ruta_archivo_rel}, no se analizan dependencias Python. Error: {e}")
        # Devolver None indica que el análisis falló debido a sintaxis inválida
        return None
    except Exception as e:
        logger.exception(f"Error inesperado analizando AST de {ruta_archivo_rel}")
        # Devolver None para errores inesperados también
        return None