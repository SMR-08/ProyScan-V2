# ProyScan V2.1: Escáner Interactivo de Estructura, Contenido y Dependencias

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
<!-- Añadir más badges si es relevante: licencia, build status, etc. -->

**ProyScan** es una herramienta de línea de comandos (CLI) escrita en Python diseñada para analizar recursivamente directorios de proyectos. Su objetivo principal es generar una instantánea completa y estructurada del código fuente, incluyendo:

*   Un **árbol visual** de la estructura de archivos y directorios.
*   Un **archivo JSON detallado** con metadatos, contenido textual y análisis de dependencias entre archivos.
*   Información sobre **dependencias inversas** (qué archivos usan a cuál).

Esta información es ideal para la comprensión de proyectos, documentación automática, análisis de código o como contexto enriquecido para Modelos de Lenguaje Grandes (LLMs).

## ✨ Características Principales (V2.1)

*   **Interfaz CLI Interactiva:** Menús y prompts guiados (usando `rich` y `questionary`) para una experiencia de usuario amigable.
*   **Navegador de Archivos TUI:** Selector de directorios integrado en la terminal (usando `prompt_toolkit`) con navegación por teclado y soporte para cambio de unidades (Windows). Opción manual también disponible.
*   **Salida Configurable:** Elige dónde guardar los resultados. Por defecto, se crea `ProyScan_Resultados` en el directorio de ejecución, con subcarpetas únicas por escaneo.
*   **Gestor de Escaneos:** Lista escaneos previos, permite abrir sus carpetas de resultados o borrarlos.
*   **Configuración Persistente:** Guarda tus preferencias (directorio de salida, modo debug) en `~/.proyscan/config.json`.
*   **`.ignore` Interactivo:** Opción para configurar un archivo `.ignore` temporal al inicio de cada escaneo, seleccionando patrones comunes por categoría/lenguaje.
*   **Árbol de Estructura:** Genera `estructura_archivos.txt` con la jerarquía del proyecto (respeta `.ignore`).
*   **JSON Detallado (`contenido_archivos.json`):**
    *   Claves estandarizadas en **inglés** (`files`, `metadata`, `dependencies`, `type`, `path`, `referenced_by`, etc.).
    *   **Metadatos:** Ruta, tamaño, estado, codificación (chardet), lenguaje (por extensión), nº líneas.
    *   **Contenido:** `content_lines` como lista de strings para archivos de texto.
    *   **Dependencias:** Lista de archivos/bibliotecas/URLs referenciados.
    *   **Dependencias Inversas:** Lista `referenced_by` indicando qué archivos internos importan/referencian al archivo actual.
*   **Análisis de Dependencias Multilenguaje:**
    *   **Alta Precisión (AST/DOM/CSSOM):** Python, HTML, CSS.
    *   **Precisión Básica/Limitada (Regex):** JavaScript, TypeScript, PHP, Vue.js (SFC).
    *   **Precisión Alta (AST - Pure Python):** Java (imports `stdlib` y `library`).
    *   **Clasificación:** `internal`, `internal_broken`, `stdlib`, `library`, `url`, `external`.
*   **Modo Debug:** Flag `--debug` o opción en configuración para logs detallados.

## 🚀 Uso

### Requisitos Previos

1.  **Python:** Versión 3.8 o superior recomendada.
2.  **pip:** El gestor de paquetes de Python.
3.  **Instalar Dependencias:** Ejecuta en tu terminal:
    ```bash
    pip install -r requirements.txt
    ```
    (El archivo `requirements.txt` incluye `rich`, `questionary`, `prompt-toolkit`, `chardet`, `beautifulsoup4`, `lxml`, `tinycss2`, `javalang`).

### Ejecución Interactiva (Recomendada)

1.  Navega en tu terminal al directorio donde clonaste o descargaste ProyScan.
2.  Ejecuta el script principal:
    ```bash
    python proyscan.py
    ```
3.  Sigue las instrucciones del menú interactivo:
    *   **Escanear Nuevo Proyecto:** Te guiará para seleccionar el directorio objetivo (con el navegador TUI o manualmente), el directorio de salida, configurar un `.ignore` temporal (opcional) y activar el modo debug (opcional).
    *   **Gestionar Escaneos Guardados:** Lista escaneos previos y permite abrirlos o borrarlos.
    *   **Configuración:** Permite ver y establecer el directorio de salida predeterminado y el estado predeterminado del modo debug.

### Ejecución No Interactiva (Para Scripting)

Puedes ejecutar un escaneo directamente pasando argumentos:

```bash
# Escaneo básico (salida en ./ProyScan_Resultados/nombre_proyecto-ID/)
python proyscan.py /ruta/al/proyecto/a/escanear

# Especificando salida
python proyscan.py /ruta/al/proyecto -o /ruta/salida

# Con modo debug
python proyscan.py /ruta/al/proyecto --debug

# Combinando opciones
python proyscan.py /ruta/al/proyecto -o /ruta/salida -d
```

#### Archivo .ignore

Para excluir archivos/directorios de forma permanente para un proyecto, crea un archivo `.ignore` en la raíz del directorio que vas a escanear.

La sintaxis es similar a `.gitignore` (una línea por patrón: `node_modules/`, `*.log`, `.env`).

Puedes usar la opción interactiva al escanear para generar un `.ignore` temporal solo para esa ejecución.

### 📄 Formato de Salida JSON (`contenido_archivos.json`)

El archivo JSON principal contiene un objeto con la clave `files`. El valor es una lista, donde cada elemento es un objeto que representa un archivo analizado:

```json
{
  "files": [
    {
      "metadata": {
        "path": "src/component.ts", // Ruta relativa normalizada
        "size_bytes": 1024,
        "status": "ok",             // ok, binary, read_error, etc.
        "encoding": "utf-8",
        "language": "typescript",
        "line_count": 50,
        "dependencies": [           // Lista de dependencias salientes
          {"type": "internal", "path": "src/utils.ts"},
          {"type": "library", "path": "react"},
          {"type": "internal_broken", "path": "src/nonexistent.ts"}
        ],
        "referenced_by": [          // Lista de archivos internos que usan este
          "src/index.ts",
          "src/another_component.ts"
        ]
      },
      "content_lines": [            // Contenido textual línea por línea
        "import { helper } from './utils';",
        "import React from 'react';",
        "// ..."
      ],
      "error_message": null         // Mensaje si status no es 'ok'
    },
    // ... más objetos de archivo ...
  ]
}
```
```
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Json
IGNORE_WHEN_COPYING_END
```

### 🛠️ Idiomas Soportados y Precisión

| Lenguaje        | Dependencias Salientes | Dependencias Inversas | Método Análisis     | Precisión         |
| --------------- | ---------------------- | --------------------- | ------------------- | ----------------- |
| Python          | ✅                     | ✅                    | AST (ast)           | Alta              |
| HTML            | ✅                     | ✅                    | DOM (bs4)           | Alta              |
| CSS/SCSS/LESS   | ✅                     | ✅                    | CSSOM (tinycss2)    | Alta              |
| Java            | ✅                     | ❌*                   | AST (javalang)      | Alta (Imports)    |
| JavaScript      | ✅                     | ✅                    | Regex               | Básica/Limitada   |
| TypeScript      | ✅                     | ✅                    | Regex               | Básica/Limitada   |
| PHP             | ✅                     | ✅                    | Regex               | Básica/Limitada   |
| Vue.js (.vue)   | ✅                     | ✅                    | Multi-Etapa (Regex) | Baja/Limitada     |
| Otros           | ❌                     | ❌                    | N/A                 | N/A               |

*Nota Java: javalang identifica imports (stdlib/library), pero no puede resolver de forma fiable imports internos a rutas de archivo sin análisis de classpath, por lo que las dependencias inversas hacia archivos Java internos pueden no registrarse actualmente.

## ⚠️ Limitaciones Conocidas

*   **Análisis Estático:** No detecta dependencias dinámicas o condicionales complejas.
*   **Precisión Regex:** El análisis para JS/TS/PHP/Vue es limitado, especialmente con código comentado, alias de ruta, o sintaxis no estándar.
*   **Resolución Interna Java:** Limitada a clasificación stdlib/library.
*   **Codificación:** chardet puede fallar en casos ambiguos.
*   **Archivos Grandes:** Se omite el contenido de archivos de texto muy grandes.

## 🔮 Futuro / Roadmap

*   **Fase E (Completa):** Implementar el navegador de archivos TUI (¡Hecho en V2.1!).
*   **Fase F (Completa):** Añadir soporte básico para TS, Vue, Java (¡Hecho en V2.1!).
*   **Refinamiento V2.1:** Mejorar pruebas, documentación, manejo de errores.
*   **Posible V2.2 / Fase 4 (Precisión):**
    *   Investigar/Implementar análisis AST para JS/TS/PHP/Vue usando herramientas externas (subprocess, Node.js, PHP CLI) para máxima precisión.
    *   Mejorar resolución interna de Java (potencialmente complejo).
    *   Soporte Otros Lenguajes: Añadir análisis para C#, C++, Ruby, Go, etc.
    *   Visualización: Exportar grafo de dependencias.
    *   Empaquetado: Facilitar instalación con `pip install proyscan`.

#### Contribuciones

(Sección opcional para indicar cómo contribuir, reportar bugs, etc.)

#### Licencia

(Sección opcional para indicar la licencia del proyecto, ej: MIT)
```
