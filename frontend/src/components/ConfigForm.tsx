import { FormEvent, useEffect, useState } from 'react';
import { TankConfig } from '../types';
import './ConfigForm.css';

interface ConfigFormProps {
  config: TankConfig | null;
  onSubmit: (
    payload: Pick<TankConfig, 'capacity_l' | 'temp_set_c'>,
  ) => Promise<void>;
}

export function ConfigForm({ config, onSubmit }: ConfigFormProps) {
  const [tempSet, setTempSet] = useState<number>(config?.temp_set_c ?? 35);
  const capacityOptions = [90, 150, 200, 500, 1000];
  const [capacity, setCapacity] = useState<number>(capacityOptions.includes(config?.capacity_l ?? 0) ? (config?.capacity_l as number) : capacityOptions[0]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (!config) {
      return;
    }
    setTempSet(config.temp_set_c);
    setCapacity(capacityOptions.includes(config.capacity_l) ? config.capacity_l : capacityOptions[0]);
  }, [config]);

  if (!config) {
    return (
      <div className="config-card">
        <h2>Configuración</h2>
        <p>Cargando configuración...</p>
      </div>
    );
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setSuccess(null);

    if (tempSet < config.temp_min_c || tempSet > config.temp_max_c) {
      setError(`El setpoint debe estar entre ${config.temp_min_c} °C y ${config.temp_max_c} °C.`);
      return;
    }
    try {
      setSubmitting(true);
      await onSubmit({
        capacity_l: Math.round(capacity),
        temp_set_c: Number(tempSet.toFixed(1)),
      });
      setSuccess('Configuración actualizada.');
    } catch (err: unknown) {
      setError('No se pudo guardar la configuración.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="config-card">
      <h2>Configuración</h2>
      <form onSubmit={handleSubmit}>
        <label>
          Setpoint temperatura (°C)
          <input
            type="number"
            step="0.5"
            min={config.temp_min_c}
            max={config.temp_max_c}
            value={tempSet}
            onChange={(event) => setTempSet(Number(event.target.value))}
          />
        </label>
        <label>
          Capacidad del tanque (L)
          <select value={capacity} onChange={(event) => setCapacity(Number(event.target.value))}>
            {capacityOptions.map((value) => (
              <option key={value} value={value}>
                {value} L
              </option>
            ))}
          </select>
        </label>
        <div className="config-card__hints">
          <span>Nivel mínimo: {config.min_level_l} L</span>
          <span>Nivel máximo: {config.max_level_l} L</span>
          <span>Histéresis: {config.hysteresis_c.toFixed(1)} °C</span>
        </div>
        {error && <p className="config-card__error">{error}</p>}
        {success && <p className="config-card__success">{success}</p>}
        <button type="submit" disabled={submitting}>
          {submitting ? 'Guardando...' : 'Guardar cambios'}
        </button>
      </form>
    </div>
  );
}
