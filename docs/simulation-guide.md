# Guía de simulación

## 1. Propósito

La simulación emula sensores de nivel y temperatura para validar la lógica de control sin hardware físico. Es ideal para demostraciones, pruebas de regresión y tunning de parámetros.

## 2. Comando principal

```bash
cd backend
source .venv/bin/activate
python manage.py run_simulation --iterations 0 --hz 1
```

Parámetros:

| Parámetro     | Descripción                                              | Valor por defecto |
|---------------|-----------------------------------------------------------|-------------------|
| `--iterations`| Número de ciclos. `0` ejecuta indefinidamente.            | `0`               |
| `--hz`        | Frecuencia de simulación (ciclos por segundo).            | `1.0`             |

## 3. Modelo físico simplificado

### Nivel (`level_l`)

```
nivel_siguiente = nivel_actual
                  + (válvula_llenado ? 5.0 : 0) * intervalo
                  - (1.5 + (válvula_vaciado ? 3.5 : 0)) * intervalo
```

El resultado se limita a `[0, capacidad]` (capacidad ajustada a 200 L si fuese menor).

### Temperatura (`temp_c`)

```
temp_siguiente = temp_actual
                 + (resistencia ? 0.8 : -0.4) * intervalo
```

El valor se constriñe a `[temp_min - 5, temp_max + 10]` para evitar extremos irreales.

### Intervalo

`intervalo = 1 / hz` (en segundos). Todos los caudales y variaciones térmicas se multiplican por ese intervalo para mantener consistencia con la frecuencia elegida.

## 4. Interacción con el controlador

1. El simulador calcula `level_l` y `temp_c` estimados.
2. Invoca `ControlService.step()` pasando dichos valores, lo que provoca:
   - Evaluación de umbrales (mínimo/máximo) y setpoints.
   - Apertura/cierre de válvulas y activación de la resistencia según modo automático o manual.
   - Registro de eventos (`EventLog`) si hay transiciones.
3. Se imprime el estado resultante en consola:
   ```
   [HH:MM:SS] nivel=XXX.XL temp=YY.Y°C válvula_llenado=... válvula_vaciado=... resistencia=...
   ```

## 5. Ajuste de la configuración

- Antes de iniciar, el comando asegura que la configuración activa tenga:
  - `capacity_l = 200`
  - `max_level_l = 200`
  - `min_level_l = 90`
- Cambia únicamente los campos necesarios vía `UPDATE` directo sobre `TankConfig`, minimizando locks en la base.
- Para restaurar otros valores, actualiza la configuración desde la UI o vía API una vez finalizada la simulación.

## 6. Manejo de bloqueos (SQLite)

- La simulación captura `sqlite3.OperationalError` y reintenta hasta 5 veces con una espera de 0.5 s.
- Si el bloqueo persiste, se lanza un `CommandError`. En ese caso:
  - Revisa si hay otra instancia de simulación o `runserver` accediendo a la misma base.
  - Considera migrar a MySQL para cargas mayores o reducir `--hz`.

## 7. Escenarios de prueba recomendados

| Escenario                          | Pasos                                                                 | Resultado esperado                                 |
|------------------------------------|-----------------------------------------------------------------------|----------------------------------------------------|
| Recuperación de nivel              | Arranca simulación en modo automático. Observa cómo la válvula de llenado se activa bajo el mínimo y se apaga al acercarse al máximo. | Nivel oscila entre `min_level` y `max_level`.      |
| Modo manual con drenaje            | Cambia a modo manual y abre válvula de vaciado.                       | Nivel desciende; si cae por debajo del mínimo la resistencia se apaga y pueden generarse eventos de seguridad. |
| Alta frecuencia (stress test)      | Ejecuta `--hz 10` durante varios minutos.                            | Sistema mantiene coherencia; si aparecen avisos de bloqueo, los reintentos deben mitigarlos (o migrar a MySQL). |
| Cambio de setpoint                 | Eleva el setpoint de temperatura desde la UI.                         | Resistencia permanece encendida hasta alcanzar el nuevo setpoint; eventos `HEATER_ON/HEATER_OFF`. |
| Lectura inválida                   | Invoca `/api/state?level=-5` desde otra consola.                      | Se activa `SAFE_MODE`; simulación continúa con válvulas cerradas hasta recibir lecturas válidas. |

## 8. Integración con la UI

- El frontend refresca `/api/state` cada segundo por defecto. Si la simulación corre a `--hz` alto, se verán varias transiciones entre refrescos; ajustar el intervalo en `frontend/src/App.tsx` si se necesita mayor resolución.
- Los eventos generados durante la simulación aparecen en la pestaña de historial con severidad y timestamp.

## 9. Buenas prácticas

- Ejecuta la simulación en una terminal dedicada para poder detenerla rápidamente con `Ctrl+C`.
- Evita ejecutar múltiples simulaciones simultáneas contra la misma base.
- Documenta el valor de `--hz` utilizado durante pruebas para replicar resultados.
- Antes de releases, corre al menos un escenario en modo automático y otro en manual para validar regresiones.
