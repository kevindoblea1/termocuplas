# Guía de operaciones y despliegue

## 1. Entornos recomendados

| Entorno   | Base de datos | Objetivo                        |
|-----------|---------------|---------------------------------|
| Desarrollo| SQLite        | Puesta en marcha rápida, demos  |
| Staging   | MySQL 8       | Pruebas integradas y de carga   |
| Producción| MySQL 8       | Operación continua              |

> SQLite funciona para pruebas locales, pero no es adecuada para concurrencia alta ni escrituras rápidas (p. ej. simulación con `--hz` elevado). Para entornos serios usa MySQL.

## 2. Variables de entorno clave

| Variable                      | Descripción                                      | Valor ejemplo                 |
|-------------------------------|--------------------------------------------------|-------------------------------|
| `DJANGO_SECRET_KEY`           | Clave secreta para Django                        | `django-insecure-...`         |
| `DEBUG`                       | Activa modo debug (`True/False`)                 | `False` en producción         |
| `ALLOWED_HOSTS`               | Hosts permitidos (lista separada por comas)      | `termocuplas.example.com`     |
| `DB_ENGINE`                   | Motor de base de datos                           | `django.db.backends.mysql`    |
| `DB_NAME`                     | Nombre de la base                                | `termocuplas`                 |
| `DB_USER` / `DB_PASSWORD`     | Credenciales DB                                  | `termocuplas_user` / `***`    |
| `DB_HOST` / `DB_PORT`         | Host y puerto DB                                 | `127.0.0.1` / `3306`          |
| `DEFAULT_TANK_INITIAL_LEVEL`  | Nivel inicial por defecto (litros)               | `120`                         |
| `DEFAULT_TANK_INITIAL_TEMPERATURE` | Temperatura inicial (°C)                    | `28`                          |
| `ALLOWED_ORIGINS`             | Orígenes CORS autorizados                        | `http://localhost:5173`       |

## 3. Despliegue backend (Gunicorn + Nginx)

1. Crear y activar entorno virtual.
2. Instalar dependencias (`pip install -r requirements.txt`).
3. Ejecutar migraciones (`python manage.py migrate`).
4. Crear superusuario si se necesita acceso admin (`python manage.py createsuperuser`).
5. Ejecutar Gunicorn:
   ```bash
   gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 3
   ```
6. Configurar Nginx como proxy inverso, sirviendo `/static/` si se recolectan archivos.

### Archivos estáticos

Ejecutar `python manage.py collectstatic` y configurar la ruta en Nginx (o CDN). Usa `STATIC_ROOT=/var/www/termocuplas/static/`.

## 4. Despliegue frontend

1. `npm install`
2. `npm run build`
3. Servir el contenido de `frontend/dist` con Nginx, Apache o un servicio estático (Netlify, Vercel). Ajustar `VITE_API_BASE_URL` en build o `.env.production`.

## 5. Simulación en entornos gestionados

- Evita ejecutar la simulación en producción salvo que sea un entorno de demo controlado.
- En staging, utiliza MySQL para evitar bloqueos y limita la frecuencia (`--hz 1` o `--hz 2`) para reducir carga.
- Considera ejecutar la simulación en un servicio separado con `systemd`:
  ```ini
  [Unit]
  Description=Termocuplas simulation

  [Service]
  WorkingDirectory=/opt/termocuplas/backend
  ExecStart=/opt/termocuplas/backend/.venv/bin/python manage.py run_simulation --iterations 0 --hz 2
  Restart=on-failure

  [Install]
  WantedBy=multi-user.target
  ```

## 6. Backups y retención

- Programar `mysqldump` o snapshots diarios.
- Limpiar periódicamente `TankState` y `EventLog` si crecen demasiado (p. ej. job semanal borrando registros >90 días).
- Para SQLite, realiza copias del archivo `db.sqlite3` con el servicio detenido para evitar corrupción.

## 7. Monitoreo y alertas

- Activar logging estructurado en Django (`LOGGING` en `settings.py`).
- Exportar métricas con Prometheus (`prometheus_client`) o integrar con herramientas como Grafana.
- Alertar sobre:
  - Eventos `SAFE_MODE` repetitivos.
  - Estado de la simulación (que siga corriendo si es esperada).
  - Recursos del host (CPU/memoria) cuando se ejecuta la simulación a alta frecuencia.

## 8. Procedimientos de emergencia

- **Modo seguro persistente:** revisar sensores reales o parámetros de simulación; verificar si las lecturas están fuera de rango.
- **Base de datos bloqueada:** reiniciar el servicio que ejecuta la simulación o migrar a MySQL.
- **Cambio de setpoint no aplicado:** comprobar modo (manual/auto) y que la API no haya devuelto errores (mirar logs y eventos).

## 9. Checklist previo a producción

- [ ] Configurar `DEBUG=False` y `ALLOWED_HOSTS`.
- [ ] Activar HTTPS en el proxy inverso.
- [ ] Definir políticas de backup.
- [ ] Revisar límites de tamaño del log y rotación.
- [ ] Validar que el frontend apunte al backend correcto (`VITE_API_BASE_URL`).
- [ ] Registrar cuentas de soporte/observabilidad.
