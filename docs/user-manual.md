# Manual de usuario

## 1. Público objetivo

Este documento está dirigido a operadores, testers y miembros de negocio que necesitan arrancar el sistema, monitorear el tanque y validar escenarios usando la simulación incluida.

## 2. Requisitos previos

- Python 3.12 o superior
- Node.js 18 o superior
- (Opcional) MySQL 8 si se desea usar la base relacional en lugar de SQLite
- Git y acceso al repositorio `kevindoblea1/termocuplas`

## 3. Instalación rápida

### Backend

```bash
git clone git@github.com:kevindoblea1/termocuplas.git
cd termocuplas/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
```

> Si usas MySQL, configura las variables de entorno (`DB_ENGINE`, `DB_NAME`, etc.) antes de ejecutar `migrate`.

### Frontend

```bash
cd ../frontend
npm install
```

## 4. Arranque del sistema

1. **Levantar backend**
   ```bash
   cd backend
   source .venv/bin/activate
   python manage.py runserver 0.0.0.0:8000
   ```
2. **Levantar frontend**
   ```bash
   cd ../frontend
   npm run dev -- --host 0.0.0.0 --port 5173
   ```
3. Accede al dashboard en `http://localhost:5173` (o la IP/puerto expuestos). Si el backend vive en otra URL, crea un archivo `.env.local` con `VITE_API_BASE_URL`.

## 5. Uso del dashboard

- **Panel principal:** muestra nivel actual, temperatura, estado de válvulas, resistencia y alertas de modo seguro.
- **Historial de eventos:** lista códigos (`VALVE_*`, `HEATER_*`, `SAFE_MODE`, etc.) con severidad.
- **Formularios:**
  - *Configuración automática:* ajusta mínimos, máximos, setpoint y histéresis.
  - *Operación manual:* permite abrir válvulas o activar resistencias individuales (50 W, 150 W, 500 W). Las protecciones desactivan la resistencia si el nivel cae por debajo del mínimo.

Los cambios se reflejan en la API y quedan registrados en `EventLog`.

## 6. Ejecución de la simulación

1. Desde `backend`, activa el entorno virtual y ejecuta:
   ```bash
   python manage.py run_simulation --iterations 0
   ```
   Deja la simulación corriendo y observa el comportamiento en la UI.
2. Para acelerar o desacelerar:
   ```bash
   python manage.py run_simulation --iterations 0 --hz 5
   ```
   Esto ejecuta 5 ciclos por segundo (intervalo de 0.2 s).
3. Detén la simulación con `Ctrl+C`.

### Escenarios sugeridos

- **Estabilización automática:** deja la simulación corriendo para ver cómo el nivel oscila entre el mínimo y el máximo, mientras la resistencia mantiene la temperatura en torno al setpoint.
- **Modo manual:** cambia el control a manual desde la UI y abre la válvula de vaciado; el nivel bajará hasta que las protecciones activen modo seguro o desenganchen la resistencia.
- **Sobrecarga de temperatura:** eleva el setpoint para observar la activación/deactivación de la resistencia y los eventos asociados.

## 7. Comandos útiles

| Acción                       | Comando                                                  |
|------------------------------|-----------------------------------------------------------|
| Ejecutar pruebas backend     | `python manage.py test control`                           |
| Generar documentación OpenAPI| `curl http://localhost:8000/api/schema`                  |
| Simulación 10 Hz             | `python manage.py run_simulation --iterations 0 --hz 10` |

## 8. Problemas frecuentes

- **`database is locked` (SQLite):** esperar unos segundos; el simulador reintenta automáticamente. Para escenarios exigentes usa MySQL.
- **Front sin datos:** verifica `VITE_API_BASE_URL` y que el backend esté accesible desde el navegador.
- **Resistencia siempre apagada:** comprueba que el nivel actual sea ≥ mínimo; la lógica de seguridad forza el apagado si no hay suficiente agua.

## 9. Cierre

Cuando termines:

```bash
Ctrl+C           # Detener servidores
deactivate       # Salir del entorno virtual
```

Las simulaciones y eventos quedan guardados en la base de datos seleccionada, permitiendo revisar la actividad más tarde.
