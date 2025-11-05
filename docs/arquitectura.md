# Arquitectura del sistema Termocuplas

## Visión general

El proyecto se divide en dos capas principales:

- **Backend (Django + DRF):** expone la API REST, ejecuta la lógica de control del tanque y persiste la configuración, estados y eventos.
- **Frontend (React + Vite):** consume la API cada segundo para mostrar el estado en tiempo real y permite ajustar parámetros clave.

Una simulación opcional (`run_simulation`) actualiza lecturas de nivel y temperatura a la frecuencia seleccionada (`--hz`, por defecto 1 Hz) para emular sensores físicos.

## Modelo de datos

| Tabla       | Descripción                                                                 |
|-------------|------------------------------------------------------------------------------|
| `TankConfig`| Configuración activa del tanque (capacidad, mínimos/máximos, setpoint, modo de operación y overrides manuales con caudal definido) |
| `TankState` | Historial de lecturas y salidas de control (válvulas de llenado/vaciado, resistencia, modo seguro)|
| `EventLog`  | Registro de eventos críticos generados ante cambios de estado                |

> Solo existe una configuración activa a la vez; el `save()` de `TankConfig` desactiva el resto.

## Lógica de control (`control/services.py`)

1. Recuperar la `TankConfig` activa y el último `TankState`.
2. Validar lecturas de sensores (nivel dentro de `[0, capacidad]`, valores numéricos finitos).
3. Si las lecturas son inválidas se activa **modo seguro**: válvulas cerradas, resistencia apagada y evento `SAFE_MODE`.
4. Si las lecturas son válidas:
   - En **modo manual** se respetan los overrides configurados para válvulas y resistencia, manteniendo las protecciones de seguridad (p. ej. la resistencia se fuerza a apagarse si el nivel cae por debajo del mínimo). Las válvulas manuales aplican un caudal fijo de ±0.2 L/s y la temperatura evoluciona según la potencia de la resistencia (50 W térmicos) y el volumen de agua.
   - En **modo automático**:
     - Nivel < mínimo → abrir válvula de llenado y mantener cerrada la de vaciado.
     - Nivel ≥ máximo → cerrar la válvula de llenado y abrir la de vaciado.
     - Nivel dentro del rango → ambas válvulas cerradas.
     - Temperatura < `setpoint - histéresis` y nivel ≥ mínimo → encender resistencia.
     - Temperatura ≥ `setpoint` → apagar resistencia.
     - Nivel < mínimo → apagar resistencia con evento `HEATER_SAFE_OFF`.
5. Cada transición genera eventos (`VALVE_*`, `HEATER_*`, `SAFE_MODE`).
6. Se guarda un nuevo `TankState` con las lecturas y salidas resultantes.

## API REST (DRF)

- `GET /api/state` ejecuta `ControlService.step()` y devuelve el último `TankState` (acepta parámetros opcionales `level`, `temp` para pruebas manuales).
- `GET /api/events` retorna eventos recientes, con parámetro `limit` (1–500).
- `GET/PUT /api/config` gestiona la configuración activa, el modo manual/automático y los overrides manuales, con validaciones de rango.
- `drf-spectacular` genera `/api/schema` y `/api/docs`.

## Panel React

- Polling a `/api/state` y `/api/events` cada 1000 ms.
- Visualiza:
- Barra vertical del nivel relativa a la capacidad configurada.
- Temperatura actual, setpoint e histéresis.
- Estados de válvula, resistencia y modo seguro con badges.
- Registro de eventos con código y severidad.
- Panel lateral para cambiar entre modo automático/manual, operar válvulas y habilitar resistencias de 50/150/500 W en manual, además de seleccionar tanques predefinidos.
- Formulario para actualizar el setpoint (validación en cliente).

El `API_BASE_URL` puede configurarse mediante `VITE_API_BASE_URL` para desacoplar entornos.

## Simulación (`run_simulation`)

- Parametriza la frecuencia (`--hz`) y calcula el intervalo (`1/hz`) para escalar los caudales (llenado/vaciado/consumo) y la variación térmica por segundo.
- Ajusta la configuración activa del tanque a un rango amplio (90–200 L) antes de iniciar si fuese necesario.
- Lee el último `TankState`, aplica incrementos/decrementos en nivel y temperatura en función de las salidas (válvula/resistencia) y vuelve a invocar `ControlService.step()`, lo que puede disparar eventos `VALVE_*`, `DRAIN_*`, `HEATER_*` o `SAFE_MODE`.
- Implementa reintentos frente a bloqueos de SQLite, recomendando MySQL para escenarios de alta frecuencia o concurrencia.
- Es útil para demostraciones sin hardware y para observar cómo se estabiliza el sistema alrededor del setpoint.

## Seguridad y extensiones

- Middleware `SimpleCorsMiddleware` habilita CORS básico para el dashboard (ajustable por variables de entorno).
- Para producción se recomienda agregar autenticación, límites de retención de `TankState/EventLog` y métricas externas.

## Diagrama textual

```
[Simulación / Sensores] --lecturas--> [ControlService] --nuevos estados--> TankState
                                                 │
                                                 ├--eventos--> EventLog
                                                 │
                                           [API REST /api/state]
                                                 │
                                        [React Dashboard 1 Hz]
```
