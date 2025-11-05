# Referencia técnica

## 1. Organización del repositorio

```
termocuplas/
├── backend/              # Proyecto Django
│   ├── control/          # App con lógica de negocio
│   ├── core/             # Configuración global de Django
│   ├── static/           # Archivos estáticos (placeholder)
│   └── manage.py
├── frontend/             # Dashboard React (Vite + TypeScript)
├── docs/                 # Documentación (este directorio)
└── README.md             # Guía rápida
```

## 2. App `control`

### Modelos clave (`control/models.py`)

- `TankConfig`: configuración activa del tanque (capacidad, umbrales, setpoint, modo). El método `save()` asegura una sola configuración activa.
- `TankState`: estado registrado tras cada ciclo (`level_l`, `temp_c`, actuadores). Ordenado por timestamp descendente.
- `EventLog`: auditoría de eventos; índices por fecha y código.

### Servicios (`control/services.py`)

`ControlService` encapsula el bucle de control:

1. Recupera `TankConfig` activa y el último `TankState`.
2. Valida lecturas (no NaN/Inf, nivel en rango). Si son inválidas, activa modo seguro y registra `SAFE_MODE`.
3. En modo manual aplica caudales fijos (±0.2 L/s) y controla resistencias según overrides; en modo automático abre/cierra válvulas según umbrales y aplica histéresis sobre la temperatura.
4. Simula la evolución térmica cuando no se proporcionan lecturas externas.
5. Registra eventos de transición (`VALVE_*`, `DRAIN_*`, `HEATER_*`, `SAFE_MODE`).
6. Crea un nuevo `TankState`.

### API (`control/views.py`, `control/serializers.py`, `control/urls.py`)

- `GET /api/state`: ejecuta un paso del controlador (permite query params `level`, `temp`).
- `GET /api/events`: pagina los eventos recientes (`limit`, `offset`).
- `GET/PUT /api/config`: consulta o actualiza la configuración activa con validaciones de serializador.
- Documentación OpenAPI: `/api/schema` y `/api/docs` generados por `drf-spectacular`.

### Gestión de simulación (`control/management/commands/run_simulation.py`)

- Parametriza la frecuencia con `--hz` (default 1 Hz).
- Ajusta límites 90–200 L si la configuración activa es más pequeña.
- Calcula nivel y temperatura en función de los actuadores (válvula/resistencia) y reintenta escritura si SQLite está bloqueada.

### Tests (`control/tests.py`)

Cobertura de:
- Validaciones de `TankConfig`.
- Transiciones automáticas de válvulas y resistencia.
- Modo manual y protecciones de seguridad.
- Registro de eventos en escenarios clave.

Ejecutar con `python manage.py test control`.

## 3. Configuración del proyecto (`core/settings.py`)

- Variables externas para MySQL (`DB_ENGINE`, `DB_NAME`, `DB_USER`, etc.).
- Parámetros de simulación por defecto (`DEFAULT_TANK_INITIAL_LEVEL`, `DEFAULT_TANK_INITIAL_TEMPERATURE`).
- Middleware personalizado `SimpleCorsMiddleware` para habilitar CORS simple (origen tomado de `ALLOWED_ORIGINS`).

## 4. Frontend (React + Vite)

- Entry point `src/main.tsx`.
- Componentes principales en `src/components/` (indicadores, formularios, listas).
- Cliente HTTP en `src/api/client.ts` con `fetch` y manejo básico de errores.
- Tipos compartidos en `src/types.ts`.
- Estilos globales en `src/styles/global.css` más CSS por componente.

El polling a 1 Hz se implementa con `setInterval` en `App.tsx`; se puede ajustar editando el hook correspondiente.

## 5. Dependencias

- Backend: Django 5.2, DRF 3.16, drf-spectacular, mysqlclient (opcional), PyYAML, jsonschema.
- Frontend: React 18, Vite, TypeScript, Axios (si se agrega en el futuro), CSS Modules.

## 6. Flujos críticos

| Flujo                        | Archivos principales                             |
|-----------------------------|---------------------------------------------------|
| Paso de control             | `control/services.py`, `control/views.py`         |
| Simulación                  | `control/management/commands/run_simulation.py`   |
| Configuración vía API/UI    | `control/serializers.py`, `control/tests.py`      |
| Polling frontend            | `frontend/src/App.tsx`, `frontend/src/api/client.ts` |

## 7. Extensibilidad

- **Nuevos sensores/actuadores:** ampliar `TankState` y modificar `ControlService` para incluirlos; actualizar serializers y tests.
- **Historial largo:** configurar `DEFAULT_AUTO_FIELD` o usar `BigAutoField` según necesidad, y considerar jobs de limpieza (`crontab`, Celery).
- **Autenticación:** integrar `django-rest-framework-simplejwt` y proteger vistas con permisos.
- **Observabilidad:** añadir logging estructurado (`logging.config`), métricas (`prometheus_client`) y alertas basadas en `EventLog`.

## 8. Pruebas y calidad

- `python manage.py test control` cubre lógica de negocio; ampliar con tests para vistas y serializers si se agregan features.
- Se sugiere configurar `pytest` + `pytest-django` si el proyecto crece.
- Frontend: agregar `vitest` o `jest` con `react-testing-library` para pruebas de componentes.

## 9. Estándares de contribución

- Cumplir con PEP8 (Django) y ESLint/Prettier (React).
- Incluir tests para cambios en lógica de control.
- Actualizar esta documentación cuando se modifiquen modelos, endpoints o parámetros de simulación.
