# proyscan/dependency_analysis/regex_parser.py
import re
import os
from typing import List, Set, Optional, Dict, Tuple

# Importar funciones de utilidad y modelos
from ..utils.path_utils import resolver_ruta_referencia, normalizar_ruta
from ..models import DependencyInfo # Usar el TypedDict definido

# --- Definición de Patrones Regex ---
# Compilar Regex para eficiencia
PATTERNS = {
    'html': [
        # src y href en tags comunes (script, link, img, audio, video, source, iframe, form action)
        re.compile(r"""<(?:script|img|audio|video|iframe|source|embed)\s+[^>]*?src\s*=\s*["']([^"']+)["'][^>]*?>""", re.IGNORECASE | re.DOTALL),
        re.compile(r"""<link\s+[^>]*?href\s*=\s*["']([^"']+)["'][^>]*?rel\s*=\s*["']stylesheet["'][^>]*?>""", re.IGNORECASE | re.DOTALL),
        re.compile(r"""<a\s+[^>]*?href\s*=\s*["']([^"']+)["'][^>]*?>""", re.IGNORECASE | re.DOTALL), # Opcional: enlaces <a>
        re.compile(r"""<form\s+[^>]*?action\s*=\s*["']([^"']+)["'][^>]*?>""", re.IGNORECASE | re.DOTALL),
        # url() en atributos style="..."
        re.compile(r"""style\s*=\s*["'][^"']*?url\(["']?([^"')]+?)["']?\)[^"']*?["']""", re.IGNORECASE | re.DOTALL),
    ],
    'css': [
        # @import url("...") or @import "..."
        re.compile(r"""@import\s+(?:url\()?["']([^"'\)]+)["']\)?\s*;?""", re.IGNORECASE),
        # url(...) en propiedades (background, font-face, etc.)
        re.compile(r"""url\(["']?([^"')]+?)["']?\)""", re.IGNORECASE),
    ],
    'javascript': [
        # import ... from '...' / import '...'
        re.compile(r"""import(?:["'\s]*(?:[\w*{}\n\r\s,]+from\s*)?)(["'])([^"'\n\r]+?)\1\s*;?""", re.MULTILINE),
        # require('...')
        re.compile(r"""require\s*\(\s*(["'])([^"'\n\r]+?)\1\s*\)\s*;?"""),
        # importScripts('...') for Web Workers
        re.compile(r"""importScripts\s*\(\s*(["'])([^"'\n\r]+?)\1\s*\)\s*;?"""),
        # new Worker('...')
        re.compile(r"""new\s+Worker\s*\(\s*(["'])([^"'\n\r]+?)\1\s*\)"""),
        # Basic fetch('/api/...') - Captura solo el primer argumento si es string literal
        re.compile(r"""fetch\s*\(\s*(["'])([^"'\n\r]+?)\1\s*(?:,|\))""", re.MULTILINE),
    ],
    'php': [
        # include/require/include_once/require_once '...' or "..."
        # Captura opcional __DIR__ .
        re.compile(r"""(?:include|require|include_once|require_once)\s+(?:(?:__DIR__|\$[_a-zA-Z0-9]+)\s*\.\s*)?(["'])([^"']+\.php)\1\s*;""", re.IGNORECASE),
    ]
    # Añadir más lenguajes/patrones si es necesario
}

def analizar_regex(
    contenido_lineas: List[str],
    lenguaje: str,
    ruta_archivo_rel: str,
    archivos_proyecto: Set[str],
    dir_proyecto_raiz: str # Necesario para resolver rutas absolutas '/'
) -> Optional[List[DependencyInfo]]:
    """
    Analiza dependencias usando Regex para lenguajes web comunes.
    """
    if lenguaje not in PATTERNS:
        return None # Lenguaje no soportado por este parser

    contenido_completo = "\n".join(contenido_lineas)
    if not contenido_completo.strip():
        return []

    dependencias_encontradas_raw: Set[str] = set()

    # Aplicar todos los patrones para el lenguaje dado
    for pattern in PATTERNS[lenguaje]:
        try:
            matches = pattern.findall(contenido_completo)
            for match in matches:
                # findall puede devolver tuplas si hay múltiples grupos de captura
                # Tomamos el último grupo no vacío o el string si no es tupla
                referencia = match[-1] if isinstance(match, tuple) and match else match
                if isinstance(referencia, str) and referencia.strip():
                     dependencias_encontradas_raw.add(referencia.strip())
        except Exception as e:
             print(f"      * Advertencia: Error aplicando Regex en {ruta_archivo_rel}: {e}")


    # --- Resolución y Clasificación ---
    dependencias_clasificadas: List[DependencyInfo] = []
    rutas_internas_procesadas = set() # Evitar duplicados de la misma ruta interna

    for ref in dependencias_encontradas_raw:
        tipo_ref, ruta_resuelta_o_original = resolver_ruta_referencia(
            ref, ruta_archivo_rel #, dir_proyecto_raiz # dir_proyecto_raiz no se usa directamente en resolver ahora
        )

        dep_info: Optional[DependencyInfo] = None

        if tipo_ref == 'url':
            dep_info = DependencyInfo(tipo='url', path=ruta_resuelta_o_original)
        elif tipo_ref == 'externa':
             # Puede ser una biblioteca (JS/PHP) o un módulo interno en raíz no encontrado
             # Por ahora clasificamos como biblioteca si no se resuelve
             dep_info = DependencyInfo(tipo='biblioteca', path=ruta_resuelta_o_original)
        elif tipo_ref in ['absoluta', 'relativa'] and ruta_resuelta_o_original:
            ruta_norm = normalizar_ruta(ruta_resuelta_o_original)
            if ruta_norm in archivos_proyecto:
                 # Solo añadir si no la hemos añadido ya
                 if ruta_norm not in rutas_internas_procesadas:
                      dep_info = DependencyInfo(tipo='interna', path=ruta_norm)
                      rutas_internas_procesadas.add(ruta_norm)
            else:
                 # Si se resolvió a una ruta que parece interna pero no existe
                 # Podríamos omitirla o marcarla como rota
                 if ruta_norm not in rutas_internas_procesadas:
                      dep_info = DependencyInfo(tipo='interna_rota', path=ruta_norm)
                      rutas_internas_procesadas.add(ruta_norm)
        # else: tipo 'desconocida' o None no se añade por ahora

        if dep_info:
             dependencias_clasificadas.append(dep_info)

    # Ordenar para consistencia (opcional)
    dependencias_clasificadas.sort(key=lambda x: (x['tipo'], x['path']))

    return dependencias_clasificadas