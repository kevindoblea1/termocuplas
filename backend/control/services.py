from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import (
    ControlMode,
    EventCode,
    EventLog,
    EventSeverity,
    TankConfig,
    TankState,
)


@dataclass
class ControlResult:
    state: TankState
    created: bool


class ControlService:
    """Encapsula la lógica de control y registro de eventos."""

    MANUAL_FILL_RATE_LPS = 0.2  # 200 ml/s
    MANUAL_DRAIN_RATE_LPS = 0.2
    MAX_ELAPSED_SECONDS = 5.0
    HEATER_POWER_W = 50
    AUX_HEATER_150_POWER_W = 150
    AUX_HEATER_500_POWER_W = 500
    SPECIFIC_HEAT_J_PER_KG_C = 4186
    WATER_DENSITY_KG_PER_L = 1.0
    AMBIENT_TEMP_C = 22.0
    COOLING_RATE_PER_SEC = 0.003

    def __init__(self, config: Optional[TankConfig] = None):
        self.config = config or TankConfig.get_active()

    def get_latest_state(self) -> Optional[TankState]:
        return TankState.objects.filter(config=self.config).order_by('-ts').first()

    def ensure_initial_state(self) -> TankState:
        latest = self.get_latest_state()
        if latest:
            return latest
        return TankState.objects.create(
            config=self.config,
            level_l=settings.DEFAULT_TANK_INITIAL_LEVEL,
            temp_c=settings.DEFAULT_TANK_INITIAL_TEMPERATURE,
            valve_open=False,
            drain_valve_open=False,
            heater_on=False,
            safe_mode=False,
        )

    def sensors_invalid(self, level_l: float, temp_c: float) -> bool:
        if any(math.isnan(val) or math.isinf(val) for val in (level_l, temp_c)):
            return True
        if level_l < 0 or level_l > self.config.capacity_l:
            return True
        return False

    def step(self, level_l: Optional[float] = None, temp_c: Optional[float] = None) -> ControlResult:
        with transaction.atomic():
            config = TankConfig.objects.select_for_update().get(pk=self.config.pk)
            self.config = config
            previous_state = (
                TankState.objects.select_for_update()
                .filter(config=config)
                .order_by('-ts')
                .first()
            )

            if previous_state is None:
                previous_state = TankState(
                    config=config,
                    level_l=settings.DEFAULT_TANK_INITIAL_LEVEL,
                    temp_c=settings.DEFAULT_TANK_INITIAL_TEMPERATURE,
                    valve_open=False,
                    drain_valve_open=False,
                    heater_on=False,
                    safe_mode=False,
                )

            current_level = level_l if level_l is not None else previous_state.level_l
            current_temp = temp_c if temp_c is not None else previous_state.temp_c
            elapsed_seconds = self._elapsed_seconds(previous_state)

            invalid = self.sensors_invalid(current_level, current_temp)
            safe_mode = invalid
            valve_open = False
            heater_on = False
            forced_heater_shutdown = False
            drain_valve_open = False
            manual_mode = config.control_mode == ControlMode.MANUAL

            if manual_mode and not invalid:
                current_level = self._apply_manual_flow(
                    config=config,
                    level_l=current_level,
                    elapsed_seconds=elapsed_seconds,
                )

            power_w = 0.0
            if manual_mode:
                if current_level >= config.min_level_l:
                    if config.manual_heater_on:
                        power_w += self.HEATER_POWER_W
                    if config.manual_heater_150_on:
                        power_w += self.AUX_HEATER_150_POWER_W
                    if config.manual_heater_500_on:
                        power_w += self.AUX_HEATER_500_POWER_W
            else:
                if previous_state.pk and previous_state.heater_on:
                    power_w += self.HEATER_POWER_W

            if temp_c is None and not invalid:
                current_temp = self._simulate_temperature(
                    previous_temp=previous_state.temp_c,
                    level_l=current_level,
                    power_w=power_w,
                    elapsed_seconds=elapsed_seconds,
                )

            invalid = self.sensors_invalid(current_level, current_temp)
            safe_mode = invalid

            if invalid:
                message = (
                    'Modo seguro activado por lecturas inválidas. '
                    f'nivel={current_level:.2f}L, temp={current_temp:.2f}°C'
                )
                EventLog.log(EventCode.SAFE_MODE, message, severity=EventSeverity.WARNING)
                if previous_state.pk and previous_state.heater_on:
                    forced_heater_shutdown = True
                drain_valve_open = False
            elif manual_mode:
                safe_mode = False
                valve_open = config.manual_valve_open
                drain_valve_open = config.manual_drain_valve_open
                heater_on = config.manual_heater_on
                if current_level < config.min_level_l:
                    if heater_on:
                        forced_heater_shutdown = True
                    heater_on = False
            else:
                safe_mode = False
                if current_level < config.min_level_l:
                    valve_open = True
                    drain_valve_open = False
                elif current_level >= config.max_level_l:
                    valve_open = False
                    drain_valve_open = True
                else:
                    valve_open = False
                    drain_valve_open = False

                can_heat = current_level >= config.min_level_l
                heater_on = previous_state.heater_on if previous_state.pk else False

                if can_heat and current_temp < config.temp_set_c - config.hysteresis_c:
                    heater_on = True
                if current_temp >= config.temp_set_c:
                    heater_on = False
                if not can_heat:
                    if heater_on:
                        forced_heater_shutdown = True
                    heater_on = False

            new_state = TankState.objects.create(
                config=config,
                level_l=current_level,
                temp_c=current_temp,
                valve_open=valve_open if not safe_mode else False,
                heater_on=heater_on if not safe_mode else False,
                drain_valve_open=drain_valve_open if not safe_mode else False,
                safe_mode=safe_mode,
            )

            self._log_transitions(
                previous_state,
                new_state,
                forced_heater_shutdown,
            )
            return ControlResult(state=new_state, created=True)

    def _log_transitions(
        self,
        previous: TankState,
        current: TankState,
        forced_heater_shutdown: bool,
    ) -> None:
        if not previous.pk:
            # Se trata de la primera muestra: registrar los estados iniciales.
            if current.valve_open:
                EventLog.log(
                    EventCode.VALVE_OPEN,
                    f'Válvula iniciada en abierto. Nivel={current.level_l:.2f}L',
                )
            else:
                EventLog.log(
                    EventCode.VALVE_CLOSE,
                    f'Válvula iniciada en cerrado. Nivel={current.level_l:.2f}L',
                )
            if current.heater_on:
                EventLog.log(
                    EventCode.HEATER_ON,
                    f'Resistencia iniciada encendida. Temp={current.temp_c:.2f}°C',
                )
            else:
                EventLog.log(
                    EventCode.HEATER_OFF,
                    f'Resistencia iniciada apagada. Temp={current.temp_c:.2f}°C',
                )
            if current.drain_valve_open:
                EventLog.log(
                    EventCode.DRAIN_OPEN,
                    f'Válvula de vaciado iniciada en abierto. Nivel={current.level_l:.2f}L',
                )
            else:
                EventLog.log(
                    EventCode.DRAIN_CLOSE,
                    f'Válvula de vaciado iniciada en cerrado. Nivel={current.level_l:.2f}L',
                )
            return

        if previous.safe_mode and not current.safe_mode:
            EventLog.log(
                EventCode.SAFE_MODE,
                'Modo seguro desactivado: sensores restablecidos.',
                severity=EventSeverity.INFO,
            )

        if previous.valve_open != current.valve_open:
            if current.valve_open:
                EventLog.log(
                    EventCode.VALVE_OPEN,
                    f'Se abre la válvula. Nivel={current.level_l:.2f}L',
                )
            else:
                EventLog.log(
                    EventCode.VALVE_CLOSE,
                    f'Se cierra la válvula. Nivel={current.level_l:.2f}L',
                )
        if previous.drain_valve_open != current.drain_valve_open:
            if current.drain_valve_open:
                EventLog.log(
                    EventCode.DRAIN_OPEN,
                    f'Se abre la válvula de vaciado. Nivel={current.level_l:.2f}L',
                )
            else:
                EventLog.log(
                    EventCode.DRAIN_CLOSE,
                    f'Se cierra la válvula de vaciado. Nivel={current.level_l:.2f}L',
                )

        if previous.heater_on != current.heater_on:
            if current.heater_on:
                EventLog.log(
                    EventCode.HEATER_ON,
                    f'Se enciende la resistencia. Temp={current.temp_c:.2f}°C',
                )
            else:
                event_code = EventCode.HEATER_OFF
                if current.safe_mode or forced_heater_shutdown:
                    event_code = EventCode.HEATER_SAFE_OFF
                EventLog.log(
                    event_code,
                    f'Se apaga la resistencia. Temp={current.temp_c:.2f}°C',
                    severity=EventSeverity.WARNING if event_code == EventCode.HEATER_SAFE_OFF else EventSeverity.INFO,
                )

    def _elapsed_seconds(self, previous_state: TankState) -> float:
        if not previous_state.pk or previous_state.ts is None:
            return 1.0
        delta = timezone.now() - previous_state.ts
        elapsed = max(0.0, min(delta.total_seconds(), self.MAX_ELAPSED_SECONDS))
        return elapsed if elapsed > 0 else 1.0

    def _apply_manual_flow(
        self,
        config: TankConfig,
        level_l: float,
        elapsed_seconds: float,
    ) -> float:
        delta = 0.0
        if config.manual_valve_open:
            delta += self.MANUAL_FILL_RATE_LPS * elapsed_seconds
        if config.manual_drain_valve_open:
            delta -= self.MANUAL_DRAIN_RATE_LPS * elapsed_seconds

        new_level = level_l + delta
        return max(0.0, min(config.capacity_l, new_level))

    def _simulate_temperature(
        self,
        previous_temp: float,
        level_l: float,
        power_w: float,
        elapsed_seconds: float,
    ) -> float:
        temp = previous_temp
        mass_kg = max(level_l, 0.0) * self.WATER_DENSITY_KG_PER_L

        if power_w > 0 and mass_kg > 0:
            delta_t = (power_w * elapsed_seconds) / (
                mass_kg * self.SPECIFIC_HEAT_J_PER_KG_C
            )
            temp += delta_t

        temp -= (temp - self.AMBIENT_TEMP_C) * self.COOLING_RATE_PER_SEC * elapsed_seconds
        return temp
