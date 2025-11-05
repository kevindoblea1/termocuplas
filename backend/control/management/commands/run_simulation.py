from __future__ import annotations

import time

from django.core.management.base import BaseCommand, CommandError
from django.db import OperationalError

from control.models import TankConfig
from control.services import ControlService


class Command(BaseCommand):
    SIM_MIN_LEVEL_L = 90.0
    SIM_MAX_LEVEL_L = 200.0
    DEFAULT_HZ = 1.0
    FILL_RATE_LPS = 5.0
    BASE_CONSUMPTION_LPS = 1.5
    DRAIN_EXTRA_LPS = 3.5
    HEATING_RATE_C_PER_SEC = 0.8
    COOLING_RATE_C_PER_SEC = 0.4
    DB_RETRY_SLEEP_S = 0.5
    DB_MAX_RETRIES = 5

    help = (
        'Simula el comportamiento del tanque aplicando la lógica de control y '
        'generando registros de eventos.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--iterations',
            type=int,
            default=0,
            help='Número de ciclos a ejecutar. 0 significa ejecución continua.',
        )
        parser.add_argument(
            '--hz',
            type=float,
            default=self.DEFAULT_HZ,
            help='Frecuencia objetivo en Hertz (ciclos por segundo).',
        )

    def handle(self, *args, **options):
        iterations = options['iterations']
        hz = options['hz']
        if hz <= 0:
            raise CommandError('El parámetro --hz debe ser mayor que 0.')

        interval_s = 1.0 / hz
        service = ControlService()
        self._ensure_simulation_bounds(service)
        service.ensure_initial_state()
        self.stdout.write(
            self.style.SUCCESS(
                f'Iniciando simulación de tanque a {hz:.2f} Hz '
                f'(paso {interval_s:.3f} s).'
            )
        )
        count = 0
        try:
            while iterations == 0 or count < iterations:
                latest_state = service.get_latest_state() or service.ensure_initial_state()
                next_level = self._simulate_level_change(
                    service,
                    latest_state.level_l,
                    latest_state.valve_open,
                    latest_state.drain_valve_open,
                    interval_s,
                )
                next_temp = self._simulate_temperature_change(
                    service,
                    latest_state.temp_c,
                    latest_state.heater_on,
                    interval_s,
                )
                result = self._safe_step(service, level_l=next_level, temp_c=next_temp)
                self._print_state(result.state)
                count += 1
                time.sleep(interval_s)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Simulación interrumpida por el usuario.'))

    def _simulate_level_change(
        self,
        service: ControlService,
        level: float,
        fill_valve_open: bool,
        drain_valve_open: bool,
        interval_s: float,
    ) -> float:
        if fill_valve_open:
            level += self.FILL_RATE_LPS * interval_s
        outflow = self.BASE_CONSUMPTION_LPS * interval_s
        if drain_valve_open:
            outflow += self.DRAIN_EXTRA_LPS * interval_s
        level -= outflow
        level = max(0.0, min(service.config.capacity_l, level))
        return level

    def _simulate_temperature_change(
        self,
        service: ControlService,
        temp: float,
        heater_on: bool,
        interval_s: float,
    ) -> float:
        if heater_on:
            temp += self.HEATING_RATE_C_PER_SEC * interval_s
        else:
            temp -= self.COOLING_RATE_C_PER_SEC * interval_s
        temp = max(service.config.temp_min_c - 5, min(service.config.temp_max_c + 10, temp))
        return temp

    def _print_state(self, state):
        status_fill = 'abierta' if state.valve_open else 'cerrada'
        status_drain = 'abierta' if state.drain_valve_open else 'cerrada'
        status_heater = 'encendida' if state.heater_on else 'apagada'
        status_safe = 'sí' if state.safe_mode else 'no'
        self.stdout.write(
            f'[{state.ts:%H:%M:%S}] nivel={state.level_l:.1f}L '
            f'temp={state.temp_c:.1f}°C válvula_llenado={status_fill} '
            f'válvula_vaciado={status_drain} resistencia={status_heater} modo_seguro={status_safe}'
        )

    def _ensure_simulation_bounds(self, service: ControlService) -> None:
        config = service.config
        updates = {}
        max_level_target = int(self.SIM_MAX_LEVEL_L)
        min_level_target = int(self.SIM_MIN_LEVEL_L)
        if config.capacity_l < max_level_target:
            updates['capacity_l'] = max_level_target
        if config.max_level_l != max_level_target:
            updates['max_level_l'] = max_level_target
        if config.min_level_l != min_level_target or config.min_level_l >= max_level_target:
            updates['min_level_l'] = min_level_target
        if updates:
            TankConfig.objects.filter(pk=config.pk).update(**updates)
            service.config.refresh_from_db(fields=list(updates.keys()))

    def _safe_step(self, service: ControlService, *, level_l: float, temp_c: float):
        """Invoca service.step reintentando si SQLite queda bloqueada."""
        attempts = 0
        while True:
            try:
                return service.step(level_l=level_l, temp_c=temp_c)
            except OperationalError as exc:
                attempts += 1
                if attempts > self.DB_MAX_RETRIES:
                    raise CommandError(f'Error de base de datos tras {attempts} intentos: {exc}') from exc
                self.stderr.write(
                    self.style.WARNING(
                        f'Base de datos bloqueada, reintentando ({attempts}/{self.DB_MAX_RETRIES})...'
                    )
                )
                time.sleep(self.DB_RETRY_SLEEP_S)
