# Guía de resolución de problemas

## 1. `sqlite3.OperationalError: database is locked`

### Síntomas

- Mensajes en consola similares a:
  ```
  Base de datos bloqueada, reintentando (1/5)...
  ```
- La simulación (`run_simulation`) parece “pausarse” por fracciones de segundo, pero luego continúa.
- En casos extremos, el comando aborta con `CommandError` después de agotar los reintentos.

### Causa raíz

SQLite bloquea la base completa durante operaciones de escritura. Cuando la simulación intenta registrar un nuevo `TankState` al mismo tiempo que otro proceso (por ejemplo `runserver` atendiendo el dashboard o una segunda simulación) también está escribiendo, se produce un conflicto y Django recibe el error `database is locked`.

### Comportamiento del sistema

- El comando `run_simulation` atrapa la excepción y reintenta hasta 5 veces (`DB_MAX_RETRIES`) con esperas de 0.5 s (`DB_RETRY_SLEEP_S`). Por eso se imprime la advertencia y, tras unas pausas, el flujo suele recuperarse solo.
- Si los 5 reintentos fallan, se lanza `CommandError` y la simulación finaliza para evitar inconsistencias.

### Cómo mitigarlo

1. **Reducir concurrencia**
   - Cerrar pestañas del dashboard mientras se ejecuta la simulación a alta frecuencia (`--hz` elevado), ya que cada request a `/api/state` también escribe.
   - Evitar correr múltiples instancias de `run_simulation` sobre la misma base.
2. **Disminuir la frecuencia**
   - Usar valores modestos de `--hz` (1–2 Hz) cuando se prueba con SQLite.
3. **Cambiar de motor**
   - Para escenarios con muchas escrituras simultáneas (demos prolongadas, estrés, producción) despliega con MySQL 8, configurado mediante las variables `DB_ENGINE`, `DB_HOST`, etc. MySQL maneja mejor la concurrencia y elimina los bloqueos globales.
4. **Ajustar reintentos (opcional)**
   - Si necesitás más tolerancia con SQLite, modifica `DB_MAX_RETRIES` o `DB_RETRY_SLEEP_S` en `run_simulation.py`. Esto no resuelve la causa pero amplía el margen antes de abortar.

### Verificación

Tras aplicar alguna mitigación, vuelve a ejecutar:

```bash
python manage.py run_simulation --iterations 0 --hz 5
```

El comando debería avanzar sin agotar los 5 reintentos. Si el problema persiste, confirma que no existan otros procesos escribiendo y considera migrar la base cuanto antes.
