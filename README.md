# Copiar Entrevistas (23.98 / 25 fps)

Scripts para **Avid Media Composer** (Windows y Mac).

## Qué hace

Busca en todos los bins (`.avb`) de una carpeta de proyecto los clips visibles (master clips, subclips y group clips) cuyo nombre contiene **"ENTREVISTA"** y que tienen un FPS determinado, y los **copia a un bin destino de otro proyecto** (por ejemplo, un proyecto a 23.98 para desgrabar).

Hay dos variantes:
- `copiar_entrevistas_2398`: copia las entrevistas a **23.98 fps**.
- `copiar_entrevistas_25`: copia las entrevistas a **25 fps**.

Los bins de origen solo se leen. Excluye los clips con ciertas etiquetas entre corchetes en el nombre (por defecto `[MC]` y `[B]`).

## Requisitos

- Python 3.8+ y la librería `pyavb` (`pip install pyavb`).
- El **bin destino tiene que estar cerrado** en Avid mientras corre (idealmente, con el proyecto destino cerrado).

## Configuración

Al principio de cada `.py` hay un bloque **CONFIGURACIÓN** con la carpeta de origen, el bin destino, la palabra clave, el FPS buscado y las etiquetas excluidas.

- La versión de **Windows** tiene rutas fijas (`F:\...`) armadas para el proyecto SOLRAC: hay que cambiarlas para otro proyecto.
- La versión de **Mac** busca sola el disco donde está la carpeta del proyecto. Si hay dos discos con esa carpeta (por ejemplo, el original y un clon), completá `DISCO` en el `.py`. Estos `.py` también corren en Windows.

## Cómo se usa

Primero muestra una vista previa de lo que va a copiar y después pregunta si copia.

- **Windows:** doble clic en `Windows/copiar_entrevistas_2398.bat` o `copiar_entrevistas_25.bat`.
- **Mac:** doble clic en `Mac/copiar_entrevistas_2398.command` o `copiar_entrevistas_25.command`. Ver `Mac/LEEME.txt` para habilitar los scripts la primera vez.
- Por línea de comandos: `python copiar_entrevistas_2398.py --dry-run` solo lista lo que copiaría.
