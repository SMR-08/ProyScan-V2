# ProyScan V2: Escáner de Estructura, Contenido y Dependencias de Proyectos

**ProyScan V2** (`proyscan.py`) es una herramienta de línea de comandos escrita en Python diseñada para analizar recursivamente un directorio de proyecto. Genera una representación visual de la estructura de archivos y un archivo JSON detallado que contiene metadatos, el contenido de los archivos de texto y un análisis básico de las dependencias entre archivos para lenguajes soportados.

El objetivo principal es proporcionar una instantánea comprensible de la organización y las interconexiones de un proyecto, útil para análisis, documentación o como entrada para otras herramientas (Principalmente modelos de lenguaje de IA, como herramienta para migrar un proyecto que hayas echo con por ejempl,o ChatGPT a Gemini 2.5 sin tener que pasar 1000 archivos, solo 2).

## Características Principales

*   **Escaneo de Directorios:** Analiza un directorio objetivo especificado por el usuario, incluyendo todos sus subdirectorios.
*   **Salida Configurable:** Permite especificar un directorio de salida para los resultados. Por defecto, crea una carpeta `ProyScan_Resultados` en el directorio actual.
*   **Salida Única por Escaneo:** Cada ejecución genera un subdirectorio único dentro del directorio de salida (usando el nombre del proyecto + ID aleatorio), permitiendo conservar históricos.
*   **Generación de Árbol de Estructura:** Crea un archivo de texto (`estructura_archivos.txt`) que muestra la jerarquía de carpetas y archivos, similar al comando `tree`, respetando las exclusiones.
*   **Salida JSON Detallada:** Genera un archivo (`contenido_archivos.json`) con una lista de objetos, cada uno representando un archivo procesado y **no ignorado**.
*   **Metadatos Completos:** Para cada archivo en JSON:
    *   `path`: Ruta relativa normalizada (usando `/`) desde la raíz del proyecto escaneado.
    *   `size_bytes`: Tamaño en bytes.
    *   `status`: Resultado del procesamiento (`ok`, `binary`, `read_error`, `too_large`, `access_error`).
    *   `encoding`: Codificación de caracteres detectada (usando `chardet`).
    *   `language`: Lenguaje/tipo inferido por extensión (Python, JavaScript, HTML, CSS, PHP, Texto, etc.).
    *   `line_count`: Número de líneas para archivos de texto leídos.
    *   `dependencias`: (Si aplica) Una lista de dependencias detectadas.
*   **Contenido como Lista de Líneas:** El contenido de archivos de texto se incluye como una lista de strings (`content_lines`).
*   **Exclusión Personalizable (`.ignore`):** Permite excluir archivos, directorios y patrones mediante un archivo `.ignore` (sintaxis similar a `.gitignore`) ubicado en la **raíz del directorio objetivo escaneado**.
*   **Análisis de Dependencias (Multilenguaje Básico):**
    *   **Python:** Alta precisión usando análisis AST (`import`, `from ... import`). Detecta dependencias internas (con resolución de rutas relativas/absolutas), de la biblioteca estándar (`stdlib`) y externas (`biblioteca`).
    *   **HTML:** Buena precisión usando parser DOM (`BeautifulSoup`). Detecta `src`/`href` en tags comunes (`script`, `link[stylesheet]`, `img`, `form`, etc.) y `url()` en atributos `style`.
    *   **CSS:** Buena precisión usando parser CSS (`tinycss2`). Detecta `@import` y `url()` en propiedades.
    *   **JavaScript (Básico):** Precisión limitada usando Regex. Detecta `import '...'`, `import ... from '...'`, `require('...')`, `importScripts('...')`, `new Worker('...')` y `fetch('...')` **cuando la ruta/URL es una cadena literal**.
    *   **PHP (Básico):** Precisión limitada usando Regex. Detecta `include`/`require`/`_once` cuando la ruta es una cadena literal y termina en `.php`.
*   **Clasificación de Dependencias:** Las dependencias detectadas se clasifican por `tipo`:
    *   `interna`: Referencia a otro archivo válido dentro del proyecto escaneado.
    *   `interna_rota`: Referencia a un archivo que parece interno pero no se encontró en el escaneo (puede llegar a fallar).
    *   `stdlib`: Módulo de la biblioteca estándar de Python.
    *   `biblioteca`: Módulo/paquete externo (Python no stdlib, JS require/import sin ruta, etc.).
    *   `url`: Una URL completa (http, https, data).
    *   `externa`: Otros casos no clasificados (ej: referencia sin indicadores de ruta en CSS/HTML).
*   **Modo Debug:** Opción `--debug` para salida detallada del proceso interno (usa `logging`).

## Idiomas Soportados (Análisis de Dependencias)

ProyScan intenta analizar dependencias para los siguientes lenguajes con diferentes niveles de precisión:

*   **Alta Precisión (AST/DOM/CSSOM):** Python, HTML, CSS.
*   **Precisión Limitada (Regex):** JavaScript, PHP.
*   **Detección de Lenguaje (por extensión):** Amplia variedad (ver `MAPA_LENGUAJES` en `config.py`). Para lenguajes no listados arriba, solo se extraerán metadatos y contenido, pero no dependencias.

*(Hoja de Ruta Futura: Se podría considerar añadir soporte más preciso para JavaScript/PHP (Fase 4) o soporte para otros lenguajes como Java, C#, etc., si hay demanda {AKA: Yo lo necesite}).*

## Limitaciones

*   **Análisis Estático:** ProyScan realiza un análisis estático. No ejecuta código, por lo que no puede detectar dependencias generadas dinámicamente (ej: `importlib` en Python, nombres de archivo construidos en JS/PHP, carga condicional compleja).
*   **Precisión Regex (JS/PHP):** El análisis de dependencias para JS y PHP se basa en expresiones regulares y puede fallar en casos complejos o no detectar todas las referencias (especialmente si no son cadenas literales).
*   **Resolución de Rutas (Simplificada):** La resolución de rutas internas (especialmente para `import` de Python) es una aproximación y puede no cubrir todos los casos extremos de configuración de `sys.path` o paquetes namespace.
*   **Detección de Codificación:** `chardet` es bueno pero no infalible; puede fallar con codificaciones ambiguas o archivos mixtos.
*   **Archivos Grandes:** El contenido de archivos de texto muy grandes (configurable, osea se puede aumentar) no se lee para evitar consumo excesivo de memoria.
*   **Contexto Ignorado:** El análisis de dependencias no siempre (depende el lenguaje) considera el contexto (ej: código comentado). Los parsers AST/DOM son mejores en esto que Regex.

## Archivos Generados

Los archivos de salida se generan dentro de un **subdirectorio único** (con el formato `nombre-proyecto-IDaleatorio`) ubicado en el directorio de salida especificado (o en `ProyScan_Resultados/` por defecto).

1.  **`estructura_archivos.txt`**: Árbol de directorios/archivos del proyecto escaneado (excluyendo ignorados).
2.  **`contenido_archivos.json`**: Archivo principal con la siguiente estructura:
    ```json
    {
      "archivos": [
        {
          "metadata": {
            "path": "ruta/relativa/al/archivo.py",
            "size_bytes": 1024,
            "status": "ok",
            "encoding": "utf-8",
            "language": "python",
            "line_count": 50,
            "dependencias": [
              {"tipo": "interna", "path": "ruta/relativa/modulo.py"},
              {"tipo": "stdlib", "path": "os"},
              {"tipo": "biblioteca", "path": "requests"}
            ]
          },
          "content_lines": [
            "linea 1 del codigo",
            "linea 2 del codigo",
            // ...
          ],
          "error_message": null // o un mensaje si hubo problemas
        },
        // ... más objetos de archivo ...
      ]
    }
    ```

## Uso

### Requisitos Previos

*   Python 3.x (Yo con 3.13 va bien)
*   `pip` (gestor de paquetes de Python)
*   Bibliotecas externas: Instalar con `pip install -r requirements.txt`. El archivo `requirements.txt` contiene:
    ```text
    chardet
    beautifulsoup4
    lxml
    tinycss2
    ```

### Ejecución

1.  **Navega** en tu terminal al directorio donde tienes el script `proyscan.py`.
2.  **Ejecuta** el script, pasando como argumento obligatorio la ruta al directorio que quieres escanear.

    **Comando Básico:**
    ```bash
    python proyscan.py /ruta/al/proyecto/a/escanear
    ```
    (Los resultados se guardarán en `./ProyScan_Resultados/nombre_proyecto-XXXXXX/`)

    **Especificando Directorio de Salida:**
    ```bash
    python proyscan.py /ruta/al/proyecto/a/escanear -o /ruta/deseada/para/salida
    ```
    (Los resultados se guardarán en `/ruta/deseada/para/salida/nombre_proyecto-XXXXXX/`)

    **Habilitando Modo Debug:**
    ```bash
    python proyscan.py /ruta/al/proyecto/a/escanear --debug
    ```
    (Mostrará mensajes detallados del proceso en la consola).

    **Combinando Opciones:**
    ```bash
    python proyscan.py --debug /ruta/al/proyecto/a/escanear -o /ruta/salida
    ```

### Archivo `.ignore`

*   Crea un archivo llamado `.ignore` en la **raíz del directorio que vas a escanear**.
*   Añade patrones (uno por línea) para excluir archivos/directorios.
*   Sintaxis similar a `.gitignore` (nombres exactos, `*.log`, `node_modules/`, etc.).
*   Las líneas que empiezan con `#` son comentarios.

## Dependencias (Bibliotecas Python)

*   **chardet:** Detección de codificación.
*   **beautifulsoup4:** Parseo de HTML.
*   **lxml:** Parser HTML/XML rápido (recomendado para `beautifulsoup4`).
*   **tinycss2:** Parseo de CSS.

## Contribuciones y Futuro

Ummm.... bueno...actualmente, este proyecto es de uso personal, si eso sube algun issue o pull request.

Planes futuros incluyen:

*   **Interfaz Gráfica (GUI):** Desarrollo de una interfaz gráfica para facilitar la interacción con ProyScan V2.
*   **Mejoras en la Línea de Comandos:** Ampliación del sistema de argumentos y, posiblemente, la implementación de un menú CLI para una experiencia de usuario más intuitiva.
*   **Gestión de Resultados:** Incorporación de funcionalidades para gestionar, filtrar y analizar los resultados del escaneo.  El objetivo es hacer la herramienta más versátil y menos centrada exclusivamente en alimentar modelos de IA.
