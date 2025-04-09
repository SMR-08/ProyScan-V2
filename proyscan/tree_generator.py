# proyscan/tree_generator.py
import os
from typing import Set

def generar_arbol_texto(directorio_raiz: str, items_ignorados: Set[str]) -> str:
    """Genera una cadena de texto con la estructura de directorios y archivos."""
    texto_arbol = ""
    espacio = '    '
    rama = '│   '
    union = '├── '
    final = '└── '

    def recorrer_subdirectorio(ruta_actual: str, prefijo: str = ''):
        nonlocal texto_arbol
        # Usar la ruta relativa normalizada para buscar en items_ignorados
        ruta_rel_actual_norm = os.path.normpath(os.path.relpath(ruta_actual, directorio_raiz)).replace(os.sep, '/')
        if ruta_rel_actual_norm == '.': ruta_rel_actual_norm = ''

        try:
            nombres_contenido = os.listdir(ruta_actual)
            contenido_filtrado = []
            # Filtrar antes de procesar
            for nombre_item in nombres_contenido:
                ruta_rel_item = os.path.join(ruta_rel_actual_norm, nombre_item).replace(os.sep, '/')
                ruta_abs_item = os.path.join(ruta_actual, nombre_item)
                es_dir_item = os.path.isdir(ruta_abs_item)

                # Clave para buscar en items_ignorados
                clave_ignorar = ruta_rel_item + '/' if es_dir_item and not ruta_rel_item.endswith('/') else ruta_rel_item

                if clave_ignorar not in items_ignorados:
                    contenido_filtrado.append(nombre_item)

            # Separar y ordenar directorios y archivos filtrados
            lista_dirs = sorted([d for d in contenido_filtrado if os.path.isdir(os.path.join(ruta_actual, d))])
            lista_archivos = sorted([f for f in contenido_filtrado if os.path.isfile(os.path.join(ruta_actual, f))])
            items_ordenados = lista_dirs + lista_archivos

        except OSError as e:
            # Mostrar error pero no detener necesariamente todo el árbol
            texto_arbol += f"{prefijo}{final}[ERROR AL ACCEDER: {os.path.basename(ruta_actual)} - {e.strerror}]\n"
            return # No continuar en esta rama si no se pudo listar

        punteros = [union] * (len(items_ordenados) - 1) + [final]
        for puntero, nombre_item in zip(punteros, items_ordenados):
            ruta_item_completa = os.path.join(ruta_actual, nombre_item)
            es_dir_item = os.path.isdir(ruta_item_completa)
            texto_arbol += prefijo + puntero + nombre_item + ('/' if es_dir_item else '') + '\n'
            if es_dir_item:
                extension = rama if puntero == union else espacio
                # Llamada recursiva para subdirectorios
                recorrer_subdirectorio(ruta_item_completa, prefijo + extension)

    # Iniciar el árbol
    texto_arbol += f"{os.path.basename(directorio_raiz)}/ (Directorio Raiz)\n"
    recorrer_subdirectorio(directorio_raiz)
    return texto_arbol