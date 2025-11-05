export interface TankState {
  id: number;
  config: number;
  level_l: number;
  temp_c: number;
  valve_open: boolean;
  drain_valve_open: boolean;
  heater_on: boolean;
  safe_mode: boolean;
  ts: string;
}

export interface TankConfig {
  id: number;
  capacity_l: number;
  min_level_l: number;
  max_level_l: number;
  temp_set_c: number;
  temp_min_c: number;
  temp_max_c: number;
  hysteresis_c: number;
   control_mode: 'AUTO' | 'MANUAL';
  manual_valve_open: boolean;
  manual_drain_valve_open: boolean;
  manual_heater_on: boolean;
  manual_heater_150_on: boolean;
  manual_heater_500_on: boolean;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface EventLog {
  id: number;
  code: string;
  message: string;
  severity: 'INFO' | 'WARNING' | 'ERROR';
  ts: string;
}
