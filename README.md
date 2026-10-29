# Calculadora de composición Aglurep v1

Aplicación web en Python 3.12 y Flask para formular mezclas de laminados, calcular su composición másica de PET, PE, PA y EVOH, evaluar límites técnicos y exportar cálculos trazables.

## Despliegue en Render

El proyecto incluye Gunicorn, entrada WSGI, configuracion HTTPS, endpoint de salud y Blueprint. Sigue [RENDER.md](RENDER.md) para subirlo a GitHub y desplegarlo, sin usuarios ni base de datos.

## Instalación y ejecución

Requisito: **Python 3.12** con `pip` y `venv`. Comprueba que `python --version` invoque una instalación real de Python; el alias de Microsoft Store no es suficiente. Ejecuta desde la raíz de este proyecto.

### Windows / PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m flask --app app:create_app run --host 127.0.0.1 --port 5000
```

Abre [http://127.0.0.1:5000](http://127.0.0.1:5000). Para detener el servidor, pulsa Ctrl+C. No es necesario activar el entorno virtual ni cambiar la política de ejecución de PowerShell.

En el entorno de Codex de esta entrega ya existe `.venv`; puedes ejecutar directamente los dos últimos comandos. Si `python` no está en PATH, sustituye el primer comando por la ruta absoluta a tu ejecutable real de Python seguida de `-m venv .venv`.

### Linux / macOS

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m flask --app app:create_app run --host 127.0.0.1 --port 5000
```

Las dependencias están fijadas en `requirements.txt`, incluidas las transitivas, para reproducir el entorno verificado. Instalar requiere acceso al índice de paquetes; ejecutar la aplicación y las pruebas no requiere Internet.

### Configuración de ejecución opcional

No se requieren secretos para iniciar localmente. Si no se define `AGLUREP_SECRET_KEY`, se genera una clave aleatoria por proceso; reiniciar el servidor invalida las instantáneas calculadas y requiere recalcular.

`.env.example` describe la variable. **El archivo .env no se carga automáticamente.** Para conservar firmas entre reinicios, establece una clave privada estable en el entorno:

```powershell
$env:AGLUREP_SECRET_KEY = 'una-clave-aleatoria-privada-de-al-menos-32-caracteres'
.\.venv\Scripts\python.exe -m flask --app app:create_app run
```

No guardes una clave real en el repositorio. El servidor incorporado se utiliza para ejecución local; un despliegue compartido requeriría un servidor WSGI y decisiones adicionales de acceso.

## Uso de la interfaz

1. Pulsa **Agregar laminado**. El backend genera un UUID y carga los espesores estándar.
2. Completa el ID de parte ERP, el nombre libre del material, su masa en kg y el espesor total en µm. ERP y material son campos diferentes; varias filas pueden compartir ambos.
3. Ajusta PET, PA y EVOH. Usa cero cuando una capa no exista. El material escrito no determina automáticamente qué capas existen.
El espesor de PE se actualiza automáticamente al editar el total o las capas, incluso antes de completar ERP y masa.

4. Pulsa **Recalcular composición**. El backend calcula PE, resultados individuales y consolidación, y evalúa cada criterio.
5. Revisa masas, porcentajes, objetivos, límites, diferencias y estados. Los incumplimientos incluyen una explicación visible. Abre el detalle individual para consultar cada laminado.
6. Pulsa **Exportar CSV** para conservar entradas, configuración y resultados en un archivo descargable. También se permiten formulaciones con estado **NO CUMPLE**.
7. **Retirar** elimina una fila de la mezcla activa. **Restablecer mezcla** abre una confirmación con opciones de cancelar y restablecer; conserva la configuración técnica.

Agregar, editar, retirar o cambiar parámetros borra la evaluación vigente y bloquea exportar hasta recalcular. Las respuestas de cálculos anteriores se descartan si hubo cambios durante la solicitud.

La interfaz acepta punto o una sola coma como separador decimal; no admite separadores de miles. El JSON de la API utiliza punto decimal. Los resultados se muestran con hasta seis decimales, pero los valores completos están disponibles en el atributo de ayuda de cada cifra y en el CSV. El cumplimiento siempre se determina antes del redondeo de presentación.

En pantallas estrechas, desplaza horizontalmente las tablas para acceder a todas las columnas.

### Ejemplo comprobable

Un laminado con masa **20 kg**, espesor total **200 µm**, PET **10 µm**, PA **12 µm** y EVOH **3 µm** produce PE **175 µm**. Con las densidades iniciales, sus porcentajes aproximados son PET **6,940589 %**, PE **85,803026 %**, PA **5,847942 %** y EVOH **1,408444 %**: **CUMPLE**.

## Fórmulas y unidades

Solo se consideran PET, PE, PA y EVOH, con la misma área de capas como hipótesis del modelo. El nombre comercial es descriptivo; adhesivos u otros componentes no se modelan como polímeros adicionales.

```text
t_PE = t_total - t_PET - t_PA - t_EVOH
contribucion_i = t_i * densidad_i
fraccion_i = contribucion_i / suma(contribuciones)
masa_i_kg = masa_laminado_kg * fraccion_i
masa_total_i_kg = suma(masa_i_kg de laminados activos)
masa_total_kg = suma(masas disponibles)
porcentaje_i = 100 * masa_total_i_kg / masa_total_kg
```

Los espesores están en µm, las densidades en kg/m³ y las masas en kg. El factor común de conversión de µm a m se cancela al calcular fracciones. La contribución es un peso relativo, no una masa absoluta. Las capas ausentes aportan cero.

El motor usa `Decimal` con contexto local de **50 dígitos**, sin cuantizar ni redondear resultados intermedios. Las divisiones periódicas conservan la precisión del contexto. Se verifica la masa individual, la masa consolidada y la suma de porcentajes con tolerancia relativa **1e-12**. Esta tolerancia se usa solo para consistencia matemática; no flexibiliza los límites de cumplimiento.

## Configuración técnica

| Polímero | Densidad inicial (kg/m³) | Espesor estándar (µm) | Objetivo (%) | Intervalo inicial permitido (%) |
|---|---:|---:|---:|---|
| PET | 1400 | 10 | 9,5 | 0 a 10, inclusive |
| PE | 989 | Calculado | 83,5 | 78,5 a 88,5, inclusive |
| PA | 983 | 12 | 4 | 0 a 9, inclusive |
| EVOH | 947 | 3 | 3 | 0 a 8, inclusive |

PE, PA y EVOH utilizan ±5 puntos porcentuales, con mínimo recortado a cero y máximo a 100. PET tiene un límite máximo independiente: **10 % cumple; 10,1 % no cumple**. El resultado global es CUMPLE únicamente si pasan los cuatro criterios. No existe compensación entre polímeros.

La sección de configuración permite cambiar densidades, espesores estándar, objetivos, tolerancias y límite PET. Los objetivos deben sumar 100 %, y el objetivo PET no puede superar su límite. Las densidades deben ser positivas; los espesores estándar y tolerancias no negativos. Porcentajes y límite deben estar entre 0 y 100.

Cualquier diferencia numérica respecto de la configuración inicial marca la evaluación y el CSV como **Personalizada**. En ese caso el cumplimiento se refiere a los parámetros personalizados, no certifica la receta inicial de Aglurep v1. La metodología de cálculo continúa siendo la misma. Restaurar parámetros iniciales no sobrescribe los espesores ya editados por laminado; los valores estándar solo se aplican a filas nuevas.

### Validación de entradas

- ID de registro UUID canónico y único dentro de la mezcla.
- ID ERP y material: texto obligatorio, hasta 250 caracteres, sin controles ni saltos de línea. Se conserva el texto original, incluidos espacios significativos.
- Espesor total y masa mayores que cero; capas conocidas no negativas y suma no superior al total.
- Números finitos, hasta 28 cifras significativas; magnitudes no nulas entre 1e-12 y menores de 1e13. Estos límites técnicos evitan magnitudes o precisiones que excedan el contrato de cálculo. El cero se normaliza y es válido en capas, tolerancias y objetivos.
- No se aceptan booleanos, floats JSON, campos inesperados, parámetros ausentes ni polímeros adicionales. Los decimales de la API se envían como cadenas; se aceptan también enteros JSON.
- Hasta 500 laminados por mezcla y 2 MiB por solicitud.
- Una mezcla vacía o con datos inválidos produce **SIN RESULTADOS**, nunca CUMPLE. No se consolida un subconjunto silencioso de filas válidas.

## Arquitectura y estructura

```text
app/
  __init__.py              Factoría e inyección de servicios
  config.py                Configuración de ejecución
  api/routes.py            HTTP, firmas y respuestas controladas
  domain/
    models.py              DTO y serialización decimal
    parsing.py             Validación de tipos y números
    contracts.py           Protocol de los cinco servicios
  services/
    configuration_service.py
    laminate_service.py
    composition_service.py
    validation_service.py
    calculation_service.py Coordinación síncrona
    export_service.py
  templates/index.html
  static/app.js
  static/styles.css
tests/
  conftest.py
  unit/
  integration/
  functional/
docs/VERIFICATION.md
requirements.txt
pytest.ini
.env.example
.gitignore
```

| Servicio | Responsabilidad y contrato |
|---|---|
| ConfigurationService | `defaults`, `validate`, `profile`: parámetros técnicos tipados y perfil. |
| LaminateService | `create`, `selected`, `edit`, `remove`: UUID, validación, edición y retirada sobre colecciones de DTO. |
| CompositionService | `calculate`: laminados validados + configuración → composición individual y consolidada. |
| ValidationService | `validate`: composición + configuración → evaluación individual y global. |
| ExportService | `export`: cálculo verificado → bytes CSV. El reloj se puede inyectar para pruebas. |
| CalculationService | Coordina validación de configuración y filas, cálculo y evaluación. No depende de Flask. |

La gestión de edición y retirada ocurre sobre el estado del navegador. El backend recibe y valida el conjunto activo completo para cada cálculo; el servicio de gestión también expone operaciones puras de edición y retirada para integraciones futuras. Ninguna operación supone persistencia de filas en el servidor.

El dominio y los servicios no importan Flask, plantillas, sesiones ni solicitudes HTTP. La factoría acepta implementaciones alternativas mediante `create_app(services={...})`; las rutas dependen de la coordinación, no de fórmulas duplicadas.

### Contratos HTTP

| Método y ruta | Entrada / salida |
|---|---|
| GET / | HTML de la calculadora. |
| GET /api/configuration | `configuration`, `version`, `methodology`. |
| POST /api/laminates | `{configuration}` → `{laminate}` con UUID y borrador. |
| POST /api/pe-thickness | Espesor total y capas PET/PA/EVOH → PE calculado automáticamente. |
| POST /api/calculate | `{configuration, laminates}` → `{result, snapshot}`. |
| POST /api/export | `{snapshot, inputs: {configuration, laminates}}` → descarga CSV. |

Una fila utiliza `record_id`, `erp_id`, `material`, `total_thickness_um`, `mass_kg` y `thicknesses: {PET, PA, EVOH}`. PE no es una entrada aceptada. La configuración contiene `densities`, `default_thicknesses`, `targets`, `tolerances` y `pet_limit`; consulta GET /api/configuration para obtener el contrato completo.

Todos los POST requieren `Content-Type: application/json`. Los resultados decimales se serializan como cadenas, sin pasar por float. Los errores de dominio responden HTTP 422 con:

```json
{
  "status": "SIN RESULTADOS",
  "errors": [{
    "code": "invalid_data",
    "message": "Las capas PET, PA y EVOH superan el espesor total.",
    "field": "total_thickness_um",
    "record_id": "UUID del registro"
  }]
}
```

También se controlan JSON mal formado (400), ruta inexistente (404), método incorrecto (405), solicitud demasiado grande (413) y errores internos (500, con detalle solo en el log del servidor). Se devuelve el primer error detectado; después de corregirlo, pueden aparecer otros.

## Exportación CSV y trazabilidad

Un único CSV UTF-8 con BOM y separador coma, con una fila por laminado activo. Las comas o comillas dentro de textos se escapan mediante el módulo estándar `csv`.

Cada fila contiene:
- ID del cálculo, fecha ISO 8601 con offset, zona America/Bogota, versión de aplicación y metodología.
- Perfil técnico y estrategia de codificación de textos.
- UUID del registro, ERP y material; masa y espesores originales, más PE calculado.
- Densidades, espesores estándar, objetivos, tolerancias y límites utilizados.
- Contribuciones, fracciones y kilogramos de cada polímero por laminado.
- Cantidad de laminados, masa total, masas y porcentajes consolidados.
- Diferencias respecto al objetivo, explicaciones, estados individuales y global.

Los consolidados se repiten para hacer cada archivo autocontenido. Todos los registros comparten el mismo ID de cálculo. La marca temporal corresponde a cada exportación; descargar de nuevo el mismo cálculo conserva su ID y actualiza la hora de exportación.

La instantánea firmada incluye entradas normalizadas, configuración, ID de cálculo y versión metodológica. Exportar requiere firma válida y coincidencia con la mezcla vigente. El servidor reconstruye los cálculos; no acepta masas, porcentajes o estados calculados por el cliente. Si cambia el contenido, el orden de las filas o la representación decimal conservada por el contrato, hay que recalcular. No hay un historial persistente de firmas ni cálculos.

### Protección frente a fórmulas e identificadores

**Todos** los textos procedentes del usuario (ERP y material, además del identificador de fila) se prefijan con un apóstrofo ASCII. Por ejemplo:

```text
ERP original:       000123
ERP en el CSV:      '000123
Material original: =SUM(1,2)
Material en CSV:    '=SUM(1,2)
Texto original:    'prefijo
Texto en CSV:      ''prefijo
```

La columna `codificacion_textos` declara `apostrofo_prefijado_v1`. Para reconstruir el valor original con un lector CSV, **retira exactamente el primer apóstrofo** de esas tres columnas; no uses `lstrip`, porque podría eliminar apóstrofos originales. No se modifica el contenido original en memoria ni se evalúan fórmulas.

Para abrir en Excel o LibreOffice, importa como UTF-8, con separador coma y las columnas identificadoras y de texto configuradas explícitamente como **Texto**. Si necesitas conservar todas las cifras decimales, impórtalas también como texto; las hojas de cálculo tienen una precisión menor que Decimal. El prefijo puede aparecer visible según el programa y el método de importación. Evita convertir identificadores a números o retirar la protección antes de una apertura automática en una hoja de cálculo.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pytest tests/unit -q
.\.venv\Scripts\python.exe -m pytest tests/integration tests/functional -q
.\.venv\Scripts\python.exe -m pip check
```

En Linux/macOS sustituye el ejecutable por `.venv/bin/python`.

La suite usa pytest y el cliente de pruebas de Flask; las fixtures numéricas y el reloj de exportación son deterministas. Cubre fórmulas independientes, capas ausentes, todos los polímeros únicos, conservación y precisión, límites, gestión, entradas inválidas, exportación segura, firmas y rutas. El flujo funcional HTTP cubre agregar, editar, retirar, recalcular, exportar y mezclar vacío. No depende de servicios externos ni de un navegador instalado.

La inspección interactiva del DOM, descargas y comportamiento responsive se verifica adicionalmente en navegador; no se presenta como prueba automatizada de pytest. El resultado ejecutado y los escenarios comprobados están en [docs/VERIFICATION.md](docs/VERIFICATION.md).

## Persistencia, seguridad y evolución

- La mezcla y configuración de trabajo viven únicamente en la memoria de la página. **Recargar o cerrar la pestaña pierde los datos.** El CSV es el mecanismo de conservación de esta versión; no se implementa importación.
- No hay base de datos, historial, catálogo ERP, autenticación, permisos ni versionado permanente de formulaciones. El UUID identifica registros de una mezcla, no autentica a una persona.
- Los POST son operaciones sin estado persistente, sin sesiones ni cookies. Por eso no requieren un token CSRF basado en sesión. Se exige JSON, se rechaza Origin ajeno cuando está presente y no se habilita CORS.
- Jinja escapa HTML, JavaScript inserta textos mediante textContent, y se envían CSP, nosniff, política de referencias y no-store. Los errores internos se registran sin devolver detalles al navegador.
- Los puertos síncronos permiten extraer configuración, gestión, cálculo, validación y exportación a servicios HTTP independientes. El coordinador puede recibir adaptadores que serialicen los mismos DTO y mantengan errores explícitos.
- Para añadir persistencia, introducir una interfaz de repositorio y adaptar la gestión a mezclas identificadas. Para un historial trazable, guardar una instantánea inmutable de entradas, configuración, versión y resultados; no depender de la configuración actual para reconstruir cálculos históricos.
- Autenticación y autorización se añadirían en el borde HTTP; un catálogo ERP y versionado de recetas serían módulos separados. Las firmas necesitarían una clave gestionada común si se usan varios procesos.
- No se incluyen colas, Celery, Redis, Kafka, RabbitMQ ni orquestadores. No son necesarios para este flujo síncrono.
