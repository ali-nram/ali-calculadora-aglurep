# Verificación de entrega

Fecha: **29 de octubre de 2026**, zona del usuario **America/Bogota**.

## Entorno y comprobaciones ejecutadas

- Python **3.12.14**, Windows, entorno virtual local `.venv`.
- Flask **3.1.3**, pytest **9.2.0**, tzdata **2026.6**.
- Comando ejecutado desde la raíz del proyecto:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Resultado real de la última ejecución de la suite:

```text
112 passed in 1.15s
```

También se ejecutaron:

```text
python -m pip check
No broken requirements found.
```

El comando real utilizó `.venv\Scripts\python.exe`. Se comprobó la sintaxis de `app/static/app.js` mediante `node --check` usando Node del runtime integrado; terminó sin errores.

## Cobertura funcional comprobada por pytest

- PE por diferencia, contribuciones contrastadas con constantes independientes, fracciones y masas.
- Mezclas de varios laminados y masas; ausencia de capas y casos de cada polímero único.
- Conservación de masa y porcentajes; precisión superior a 28 dígitos en resultados intermedios.
- Objetivos, todos los límites inclusivos y violaciones individuales.
- PET exactamente 10 % en una mezcla real de cuatro polímeros: CUMPLE. Valores superiores: NO CUMPLE.
- Mezcla vacía, masas y capas inválidas, densidades inválidas, campos ausentes, tipos incorrectos, límites numéricos y caracteres de control.
- Crear, editar y retirar mediante servicios de gestión, identidad estable, ERP duplicados, nombres libres y espesores personalizados.
- CSV UTF-8 con BOM, números completos, tildes, eñes, identificadores y prefijo textual reversible contra fórmulas.
- Filas activas, exclusión de retiradas, consolidación, parámetros y un único ID de cálculo.
- Rutas Flask, inyección de dependencias, errores HTTP y error interno controlado.
- Rechazo de firma alterada, configuración cambiada y mezcla obsoleta.
- Flujo HTTP agregar–editar–calcular–retirar–recalcular–exportar y rechazo de mezcla restablecida.

Los tests son locales y no consultan servicios externos. Las verificaciones de navegador siguientes son adicionales y no están incluidas en el contador de pytest.

## Verificación interactiva del navegador

Se arrancó realmente el servidor con:

```powershell
.\.venv\Scripts\python.exe -m flask --app app:create_app run --host 127.0.0.1 --port 5000
```

Se abrió la aplicación en el navegador integrado y se comprobaron:

1. Alta de dos registros con el mismo ERP **000123**, materiales diferentes y UUID distintos.
2. Primer laminado: 20 kg, espesor total 200 µm y capas PET/PA/EVOH de 10/12/3 µm. PE calculado: 175 µm; estado CUMPLE.
3. Segundo laminado: 7,5 kg, total 100 µm, capas 10/0/3 µm. PE calculado: 87 µm.
4. Consolidación: **2 laminados, 27,5 kg, CUMPLE**.
5. Cambio a espesor total insuficiente: error con registro y campo identificados; exportación bloqueada.
6. Cambio a un caso de incumplimiento: estado NO CUMPLE y explicaciones visibles de PET, PE y PA.
7. Descarga real de CSV mediante el botón. El archivo se leyó además con el módulo csv de Python: **dos filas**, masa consolidada **27,5 kg**, ERP preservados como `'000123`, estado CUMPLE y un solo ID de cálculo.
8. Retirada del segundo laminado y recálculo: **1 laminado, 20 kg**.
9. Restablecimiento: cancelar mantiene el registro; confirmar deja **0 laminados, SIN RESULTADOS** y exportación deshabilitada.
10. Cambio de densidad PE a 950: perfil **Personalizada**. Restaurar configuración invalida el cálculo y bloquea exportar; recalcular devuelve perfil **Aglurep v1**.
11. Prueba responsive con viewport solicitado de **390 × 844**. La anchura del documento coincidió con su anchura disponible (**375 px**, descontando la barra de desplazamiento); las tablas de mayor tamaño permanecen dentro de sus contenedores desplazables.
12. Capturas de escritorio y móvil guardadas como evidencia visual de la entrega.

El servidor de verificación es temporal y se detiene al finalizar la entrega. Para utilizar la herramienta, vuelve a iniciarlo con el comando documentado.

## Limitaciones conocidas

- Estado únicamente en memoria del navegador; recargar pierde la mezcla y configuración de trabajo.
- Sin importación de CSV, historial ni base de datos. Las exportaciones conservan los datos necesarios para reconstruir cálculos.
- Sin autenticación. Preparada para uso local y despliegue en Render mediante RENDER.md.
- La automatización de pytest verifica el flujo HTTP; la interacción del DOM y el diseño responsive se comprobaron manualmente mediante herramientas de navegador.
- Los programas de hojas de cálculo pueden mostrar el apóstrofo protector. Importar identificadores como Texto y seguir la estrategia reversible documentada en el README.

## Actualizacion: orden de campos y PE automatico

- Espesor total (um) aparece antes de Masa total (kg).
- Nueva ruta POST /api/pe-thickness: usa la misma formula decimal del motor, sin exigir ERP ni masa.
- Verificado en navegador: total 100 y capas 10/12/3 muestran PE 75 automaticamente; cambiar PET a 20 actualiza PE a 65 sin pulsar Recalcular.
- La exportacion sigue bloqueada hasta recalcular la composicion completa.
- Suite ejecutada tras el cambio: 119 passed in 1.92s. Sintaxis JavaScript comprobada con node --check.


## Preparacion para Render

- Entrada WSGI wsgi.py, Python 3.12.14 fijado, Gunicorn 26.2.0 para Linux y render.yaml con comprobacion de salud /health.
- Clave estable obligatoria en produccion; el Blueprint la genera en Render. Proxy HTTPS habilitado explicitamente; se mantiene el rechazo de origen ajeno.
- Suite ejecutada: 128 passed in 1.58s en modo local; 128 passed in 1.56s con las variables de produccion de Render (clave ficticia solo para pruebas).
- pip check: No broken requirements found. Dependencias locales instaladas desde requirements.txt.
- Flujo HTTPS de calculo y CSV verificado entre dos instancias independientes de la factoria con clave compartida.
- Gunicorn se omite en Windows por marcador de plataforma. Su arranque Linux y el despliegue real quedan pendientes de ejecutarse en Render; no se afirma que se hayan probado aqui.
- No se ha hecho commit, push ni creacion de servicios. Los pasos estan en RENDER.md.
