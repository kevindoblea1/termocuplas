import { useEffect, useMemo, useState } from 'react';
import { apiClient, endpoints } from './api/client';
import { ConfigForm } from './components/ConfigForm';
import { EventsList } from './components/EventsList';
import { LevelIndicator } from './components/LevelIndicator';
import { ManualControls } from './components/ManualControls';
import { StateBadge } from './components/StateBadge';
import { EventLog, TankConfig, TankState } from './types';
import './App.css';

const POLLING_INTERVAL = 1000;

export default function App() {
  const [tankState, setTankState] = useState<TankState | null>(null);
  const [config, setConfig] = useState<TankConfig | null>(null);
  const [events, setEvents] = useState<EventLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchConfig = async () => {
    try {
      const response = await apiClient.get<TankConfig>(endpoints.config);
      setConfig(response.data);
    } catch (err: unknown) {
      setError('No se pudo obtener la configuración.');
    }
  };

  const fetchData = async () => {
    try {
      const [stateResponse, eventsResponse] = await Promise.all([
        apiClient.get<TankState>(endpoints.state),
        apiClient.get<EventLog[]>(`${endpoints.events}?limit=50`),
      ]);
      setTankState(stateResponse.data);
      setEvents(eventsResponse.data);
      setLastUpdated(new Date());
      setError(null);
    } catch (err: unknown) {
      setError('Sin conexión con el backend. Reintentando...');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConfig();
    fetchData();
    const timer = window.setInterval(fetchData, POLLING_INTERVAL);
    return () => window.clearInterval(timer);
  }, []);

  const handleConfigUpdate = async (
    payload: Pick<TankConfig, 'capacity_l' | 'temp_set_c'>,
  ) => {
    await apiClient.patch<TankConfig>(endpoints.config, payload);
    await fetchConfig();
  };

  const handleManualUpdate = async (
    payload: Partial<
      Pick<
        TankConfig,
        |
          'control_mode'
          | 'manual_valve_open'
          | 'manual_drain_valve_open'
          | 'manual_heater_on'
          | 'manual_heater_150_on'
          | 'manual_heater_500_on'
      >
    >,
  ) => {
    await apiClient.patch<TankConfig>(endpoints.config, payload);
    await fetchConfig();
  };

  const levelPercent = useMemo(() => {
    if (!tankState || !config) {
      return 0;
    }
    const percentage = (tankState.level_l / config.capacity_l) * 100;
    return Math.round(Math.max(0, Math.min(percentage, 100)));
  }, [tankState, config]);

  const temperatureDisplay = tankState ? `${tankState.temp_c.toFixed(1)} °C` : '--';
  const targetDisplay = config
    ? `${config.temp_set_c.toFixed(1)} °C (±${config.hysteresis_c.toFixed(1)})`
    : '--';
  const fillValveActive = Boolean(tankState?.valve_open);
  const drainValveActive = Boolean(tankState?.drain_valve_open);
  const heaterActive = Boolean(tankState?.heater_on);
  const safeModeActive = Boolean(tankState?.safe_mode);

  return (
    <div className="app">
      <header className="app__header">
        <div>
          <h1>Sistema de control de tanque</h1>
          <p>Monitoreo de nivel y temperatura con histéresis y modo seguro.</p>
        </div>
        <div className="app__meta">
          <span>Refresco: 1 Hz</span>
          {lastUpdated && <span>Actualizado: {lastUpdated.toLocaleTimeString()}</span>}
        </div>
      </header>
      {error && <div className="app__error">{error}</div>}
      <main className="app__layout">
        <section className="app__status">
          <div className="app__panel">
            <LevelIndicator level={tankState?.level_l ?? 0} capacity={config?.capacity_l ?? 100} />
            <div className="app__metrics">
              <div className="app__temperature">
                <span className="app__temperature-value">{temperatureDisplay}</span>
                <span className="app__temperature-target">Objetivo: {targetDisplay}</span>
                {config && tankState && (
                  <span className="app__level-percent">{levelPercent}% del tanque</span>
                )}
                {config && (
                  <span className={`app__control-mode app__control-mode--${config.control_mode.toLowerCase()}`}>
                    Modo {config.control_mode === 'MANUAL' ? 'manual' : 'automático'}
                  </span>
                )}
              </div>
              <div className="app__actuators">
                <div className="app__actuators-group">
                  <h3>Válvulas</h3>
                  <div className="app__badges-row">
                    <StateBadge
                      label={fillValveActive ? 'Válvula de llenado abierta' : 'Válvula de llenado cerrada'}
                      active={fillValveActive}
                      type="fill"
                    />
                    <StateBadge
                      label={drainValveActive ? 'Válvula de vaciado abierta' : 'Válvula de vaciado cerrada'}
                      active={drainValveActive}
                      type="drain"
                    />
                  </div>
                </div>
                <div className="app__actuators-group">
                  <h3>Seguridad y calefacción</h3>
                  <div className="app__badges-row">
                    <StateBadge
                      label={heaterActive ? 'Resistencia encendida' : 'Resistencia apagada'}
                      active={heaterActive}
                      type="heater"
                    />
                    <StateBadge
                      label={safeModeActive ? 'Modo seguro activo' : 'Modo seguro inactivo'}
                      active={safeModeActive}
                      type="safe"
                    />
                  </div>
                </div>
                <ManualControls config={config} onUpdate={handleManualUpdate} />
              </div>
            </div>
          </div>
        </section>
        <section className="app__sidebar">
          <ConfigForm config={config} onSubmit={handleConfigUpdate} />
          <EventsList events={events} />
        </section>
      </main>
      {loading && <div className="app__loading">Conectando con el backend...</div>}
    </div>
  );
}
