# Sistema de control de nivel y temperatura (Termocuplas)

Solución completa para controlar el nivel y la temperatura de un tanque de agua. Incluye API REST en Django + DRF, panel de monitoreo en React (Vite) y comando de simulación para emular sensores a 1 Hz.

## Características clave

- Control de nivel con histéresis en modo automático: abre/cierra la válvula de llenado dentro de los umbrales configurados y activa la válvula de vaciado al exceder el máximo.
- Modo manual opcional desde la UI para abrir/cerrar válvulas y encender hasta tres resistencias (50 W base + opcionales de 150 W y 500 W) con protecciones de seguridad (llenado/vaciado a 0.2 L/s).
- Simulación térmica basada en potencia de la resistencia (50 W térmicos), volumen de agua y pérdidas a ambiente para un ajuste gradual de temperatura.
- Control de temperatura con protección por nivel mínimo y modo seguro ante lecturas inválidas.
- Registro de eventos críticos (`VALVE_*`, `HEATER_*`, `SAFE_MODE`) con marcas de tiempo.
- API REST documentada con OpenAPI/Swagger en `/api/docs`.
- Dashboard React en tiempo real (refresco 1 Hz) con barra de nivel, estado de actuadores, alarma de modo seguro y formulario de configuración.
- Comando `run_simulation` que modifica nivel/temperatura cada segundo para demostrar el bucle de control.
- Pruebas automatizadas de la lógica de control y validación de configuración.

## Estructura del proyecto

```
├── backend/        # Proyecto Django + DRF
├── frontend/       # Dashboard React (Vite + TypeScript)
├── docs/           # Documentación adicional
└── README.md
```

## Requisitos

- Python 3.12+
- Node.js 18+
- MySQL 8 (o SQLite para desarrollo rápido)

## Configuración del backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Variables de entorno recomendadas (MySQL)
export DB_ENGINE=django.db.backends.mysql
export DB_NAME=termocuplas
export DB_USER=usuario
export DB_PASSWORD=secreto
export DB_HOST=localhost
export DB_PORT=3306

python manage.py migrate

# Servidor de desarrollo (Ctrl+C para detenerlo)
python manage.py runserver
```

> Tip: Cuando termines de trabajar podés salir del entorno virtual con `deactivate`.

### Pruebas

```bash
cd backend
source .venv/bin/activate
python manage.py test control
```

### Comando de simulación (1 Hz)

```bash
cd backend
source .venv/bin/activate
python manage.py run_simulation --iterations 0
# Para acelerar la simulación (p.ej. 5 Hz → paso de 0.2 s)
python manage.py run_simulation --iterations 0 --hz 5
```

Con el servidor levantado, la simulación actualiza nivel y temperatura cada segundo para observar cómo el controlador mantiene los rangos objetivo.
Al arrancar la simulación, la configuración activa del tanque se ajusta automáticamente a un rango amplio (mínimo 90 L, máximo/capacidad 200 L) para emular un depósito de mayor tamaño. Durante la ejecución, el consumo base y la válvula de vaciado reducen el nivel, mientras la válvula de llenado y la resistencia se encienden o apagan según lo requiera la lógica de control. Si querés regresar a valores anteriores, actualizá la configuración desde el panel o la base de datos.

## Configuración del frontend

```bash
cd frontend
npm install
# Opcional: definir el backend
# echo "VITE_API_BASE_URL=http://localhost:8000/api" > .env.local
npm run dev
```

El panel se servirá por defecto en `http://localhost:5173`.

## Endpoints principales

- `GET /api/state` – Retorna el estado actual del tanque y aplica un paso de control.
- `GET /api/events?limit=25` – Últimos eventos ordenados (desc).
- `GET/PUT /api/config` – Obtiene o actualiza la configuración activa.
- `GET /api/schema` – Esquema OpenAPI (JSON).
- `GET /api/docs` – Explorador Swagger.

Las peticiones admiten parámetros `level` y `temp` en `/api/state` para inyectar lecturas manuales durante pruebas.

## Arquitectura y decisiones

- Modelo de datos minimalista: `TankConfig`, `TankState`, `EventLog`.
- Servicio `ControlService` encapsula la lógica de control y la escritura de eventos.
- Middleware CORS ligero (`core.middleware.SimpleCorsMiddleware`) para el dashboard.
- Simulación interna mantiene demostración sin hardware.

Consulta `docs/arquitectura.md` para un diagrama textual y decisiones detalladas.

## Próximos pasos sugeridos

1. Desplegar el backend en un servidor con MySQL y configurar variables de entorno seguras.
2. Añadir autenticación (JWT o token) si se planea exponer el panel en redes públicas.
3. Instrumentar métricas o alertas externas (Prometheus, syslog) usando los eventos registrados.
