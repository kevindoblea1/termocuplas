import './ManualControls.css';
import { TankConfig } from '../types';

type ManualUpdate = Partial<Pick<
  TankConfig,
  |
    'control_mode'
    | 'manual_valve_open'
    | 'manual_drain_valve_open'
    | 'manual_heater_on'
    | 'manual_heater_150_on'
    | 'manual_heater_500_on'
>>;

interface ManualControlsProps {
  config: TankConfig | null;
  onUpdate: (payload: ManualUpdate) => Promise<void>;
}

type ManualToggleField = keyof Pick<
  TankConfig,
  | 'manual_valve_open'
  | 'manual_drain_valve_open'
  | 'manual_heater_on'
  | 'manual_heater_150_on'
  | 'manual_heater_500_on'
>;

interface ToggleDescriptor {
  field: ManualToggleField;
  label: string;
}

const VALVE_TOGGLES: ToggleDescriptor[] = [
  {
    field: 'manual_valve_open',
    label: 'Válvula de llenado abierta',
  },
  {
    field: 'manual_drain_valve_open',
    label: 'Válvula de vaciado abierta',
  },
];

const HEATER_TOGGLES: ToggleDescriptor[] = [
  {
    field: 'manual_heater_on',
    label: 'Resistencia 50 W',
  },
  {
    field: 'manual_heater_150_on',
    label: 'Resistencia 150 W',
  },
  {
    field: 'manual_heater_500_on',
    label: 'Resistencia 500 W',
  },
];

export function ManualControls({ config, onUpdate }: ManualControlsProps) {
  if (!config) {
    return (
      <div className="manual-controls">
        <h3>Control manual</h3>
        <p className="manual-controls__hint">Cargando controles manuales...</p>
      </div>
    );
  }

  const isManual = config.control_mode === 'MANUAL';

  const handleToggle = async (descriptor: ToggleDescriptor) => {
    if (!isManual) {
      return;
    }
    const nextValue = !config[descriptor.field];
    await onUpdate({ [descriptor.field]: nextValue } as ManualUpdate);
  };

  const handleModeChange = async (mode: 'AUTO' | 'MANUAL') => {
    if (config.control_mode === mode) {
      return;
    }
    await onUpdate({ control_mode: mode } as ManualUpdate);
  };

  return (
    <div className="manual-controls">
      <div className="manual-controls__mode">
        <h3>Modo de operación</h3>
        <div className="manual-controls__mode-options">
          <button
            type="button"
            className={`manual-mode ${config.control_mode === 'AUTO' ? 'manual-mode--active' : ''}`}
            onClick={() => handleModeChange('AUTO')}
          >
            Automático
          </button>
          <button
            type="button"
            className={`manual-mode ${config.control_mode === 'MANUAL' ? 'manual-mode--active' : ''}`}
            onClick={() => handleModeChange('MANUAL')}
          >
            Manual
          </button>
        </div>
      </div>
      <div className="manual-controls__body">
        <h3>Control manual</h3>
        <p className="manual-controls__hint">
          Disponible cuando el modo es manual. Las protecciones siguen activas.
        </p>
      </div>
      <div className="manual-controls__group">
        <h4 className="manual-controls__subtitle">Válvulas</h4>
        <div className="manual-controls__grid">
          {VALVE_TOGGLES.map((toggle) => {
            const active = Boolean(config[toggle.field]);
            return (
              <button
                key={toggle.field}
                type="button"
                className={`manual-toggle ${active ? 'manual-toggle--on' : ''}`}
                onClick={() => handleToggle(toggle)}
                disabled={!isManual}
                aria-pressed={active}
              >
                <span className="manual-toggle__track">
                  <span className="manual-toggle__thumb" />
                </span>
                <span className="manual-toggle__label">{toggle.label}</span>
              </button>
            );
          })}
        </div>
      </div>
      <div className="manual-controls__group">
        <h4 className="manual-controls__subtitle">Resistencias</h4>
        <div className="manual-controls__grid">
          {HEATER_TOGGLES.map((toggle) => {
            const active = Boolean(config[toggle.field]);
            return (
              <button
                key={toggle.field}
                type="button"
                className={`manual-toggle ${active ? 'manual-toggle--on' : ''}`}
                onClick={() => handleToggle(toggle)}
                disabled={!isManual}
                aria-pressed={active}
              >
                <span className="manual-toggle__track">
                  <span className="manual-toggle__thumb" />
                </span>
                <span className="manual-toggle__label">{toggle.label}</span>
              </button>
            );
          })}
        </div>
      </div>
      {!isManual && (
        <p className="manual-controls__note">
          Cambia a modo manual para habilitar los controles.
        </p>
      )}
    </div>
  );
}
