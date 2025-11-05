from __future__ import annotations

import time

from django.core.management.base import BaseCommand

from control.services import ControlService


class Command(BaseCommand):
    help = (
        'Simula el comportamiento del tanque a 1 Hz, aplicando la lógica de control '
        'y generando registros de eventos.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--iterations',
            type=int,
            default=0,
            help='Número de ciclos a ejecutar. 0 significa ejecución continua.',
        )

    def handle(self, *args, **options):
        iterations = options['iterations']
        service = ControlService()
        service.ensure_initial_state()
        self.stdout.write(self.style.SUCCESS('Iniciando simulación de tanque (1 Hz).'))
        count = 0
        try:
            while iterations == 0 or count < iterations:
                latest_state = service.get_latest_state() or service.ensure_initial_state()
                next_level = self._simulate_level_change(
                    service,
                    latest_state.level_l,
                    latest_state.valve_open,
                    latest_state.drain_valve_open,
                )
                next_temp = self._simulate_temperature_change(service, latest_state.temp_c, latest_state.heater_on)
                result = service.step(level_l=next_level, temp_c=next_temp)
                self._print_state(result.state)
                count += 1
                time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Simulación interrumpida por el usuario.'))

    def _simulate_level_change(
        self,
        service: ControlService,
        level: float,
        fill_valve_open: bool,
        drain_valve_open: bool,
    ) -> float:
        if fill_valve_open:
            level += 5.0
        consumption = 1.5
        if drain_valve_open:
            consumption += 3.5
        level -= consumption
        level = max(0.0, min(service.config.capacity_l, level))
        return level

    def _simulate_temperature_change(self, service: ControlService, temp: float, heater_on: bool) -> float:
        if heater_on:
            temp += 0.8
        else:
            temp -= 0.4
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
