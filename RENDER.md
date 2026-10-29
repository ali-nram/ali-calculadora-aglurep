# Desplegar Aglurep en Render

La aplicación está preparada como un Web Service Python, sin usuarios, base de datos ni disco persistente. El repositorio contiene `render.yaml`, `wsgi.py`, `.python-version` y dependencias fijadas. La mezcla sigue viviendo en la memoria del navegador.

## 1. Subir el proyecto a GitHub

Este directorio ya tiene su propio repositorio y un remoto `origin`. Desde la raíz del proyecto:

```powershell
git status --short
git add .env.example .gitignore .python-version requirements.txt render.yaml wsgi.py RENDER.md README.md app tests docs/VERIFICATION.md
git diff --cached --stat
git commit -m "Preparar calculadora Aglurep para Render"
git push -u origin HEAD
```

Revisa lo que vas a subir antes del commit. `.venv`, `.env`, cachés, `.vscode` y `desktop.ini` están excluidos. No subas claves reales. Estos comandos no crean un repositorio remoto: si el remoto existente no es el destino deseado, primero configura en GitHub el repositorio del proyecto y ajusta `origin`.

## 2. Desplegar con Blueprint (recomendado)

1. En Render, elige **New > Blueprint**.
2. Conecta el repositorio de GitHub y selecciona la rama a desplegar.
3. Mantén `render.yaml` como archivo de configuración, en la raíz.
4. Revisa el servicio `aglurep-calculadora` y confirma la creación en Render.

El Blueprint selecciona el plan **free**, fija Python 3.12.14, instala dependencias, ejecuta pytest y arranca Gunicorn con dos workers. También genera `AGLUREP_SECRET_KEY` automáticamente y configura HTTPS detrás del proxy. No necesita dominio propio.

Si el plan free no está disponible en tu cuenta, elige un plan desde Render antes de desplegar. Consulta las condiciones vigentes; esta preparación no contrata ni crea servicios.

## Alternativa: Web Service manual

Usa estos valores en **New > Web Service**:

| Campo | Valor |
|---|---|
| Repositorio y rama | Los que acabas de actualizar |
| Runtime | Python 3 |
| Root Directory | Vacío (el repositorio tiene app/ en su raíz) |
| Build Command | `pip install -r requirements.txt && python -m pytest -q` |
| Start Command | `gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --access-logfile - --error-logfile -` |
| Health Check Path | `/health` |

Variables de entorno:

| Variable | Valor |
|---|---|
| PYTHON_VERSION | `3.12.14` |
| AGLUREP_ENV | `production` |
| AGLUREP_BEHIND_PROXY | `1` |
| AGLUREP_SECRET_KEY | Clave aleatoria privada de al menos 32 caracteres |

Para el modo manual, genera una clave local y pégala únicamente en el campo privado de Render:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
```

No cambies la clave entre workers o reinicios. Si la rotas, los cálculos ya abiertos requerirán recalcular antes de exportar. La aplicación falla al arrancar en producción si falta la clave o es demasiado corta.

## 3. Verificar después del despliegue

- Espera a que Render marque el servicio como disponible y abra su URL HTTPS.
- `https://TU-SERVICIO.onrender.com/health` debe responder HTTP 200 con `status: ok`.
- Agrega un laminado de 20 kg, total 200 µm y PET/PA/EVOH de 10/12/3 µm.
- Sin recalcular, PE debe actualizarse automáticamente a 175 µm.
- Pulsa Recalcular: el resultado debe ser CUMPLE. Descarga el CSV y comprueba ERP, masa e ID de cálculo.
- Editar una capa debe invalidar la exportación hasta recalcular.
- Si falla el build, revisa los logs de instalación/pruebas; si falla el arranque, comprueba las variables y el comando Gunicorn.

## Notas operativas

- HTTPS se reconoce mediante `ProxyFix` solo cuando `AGLUREP_BEHIND_PROXY=1`. Se confía en un valor de X-Forwarded-Proto; no se confía en X-Forwarded-Host, X-Forwarded-For ni puertos reenviados. Activar únicamente detrás de un proxy que establezca ese encabezado. El desarrollo local no lo activa.
- Se mantiene la validación de mismo origen. No se habilita CORS ni se añaden usuarios.
- El endpoint de salud no contiene datos de mezclas ni secretos.
- El servicio no guarda mezclas ni genera archivos permanentes en el servidor. Recargar la página pierde la mezcla; conserva el CSV.
- Gunicorn se instala solo en plataformas distintas de Windows. Para trabajar en Windows sigue usando Flask local. No se requiere Docker.
- Las pruebas locales cubren la entrada WSGI, el flujo HTTPS detrás de proxy y las firmas entre dos instancias. La ejecución real de Gunicorn Linux y el despliegue deben verificarse en Render.

Documentación oficial: [Flask en Render](https://render.com/docs/deploy-flask), [Blueprint](https://render.com/docs/blueprint-spec), [versión de Python](https://render.com/docs/python-version), [proxy en Flask](https://flask.palletsprojects.com/en/stable/deploying/proxy_fix/).
