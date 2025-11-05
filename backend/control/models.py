from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models, transaction


class EventSeverity(models.TextChoices):
    INFO = 'INFO', 'Informativo'
    WARNING = 'WARNING', 'Advertencia'
    ERROR = 'ERROR', 'Error'


class EventCode(models.TextChoices):
    VALVE_OPEN = 'VALVE_OPEN', 'Válvula abierta'
    VALVE_CLOSE = 'VALVE_CLOSE', 'Válvula cerrada'
    HEATER_ON = 'HEATER_ON', 'Resistencia encendida'
    HEATER_OFF = 'HEATER_OFF', 'Resistencia apagada'
    HEATER_SAFE_OFF = 'HEATER_SAFE_OFF', 'Resistencia apagada por seguridad'
    SAFE_MODE = 'SAFE_MODE', 'Modo seguro activado'
    DRAIN_OPEN = 'DRAIN_OPEN', 'Válvula de vaciado abierta'
    DRAIN_CLOSE = 'DRAIN_CLOSE', 'Válvula de vaciado cerrada'


class ControlMode(models.TextChoices):
    AUTO = 'AUTO', 'Automático'
    MANUAL = 'MANUAL', 'Manual'


class TankConfig(models.Model):
    capacity_l = models.PositiveIntegerField(default=100)
    min_level_l = models.PositiveIntegerField(default=30)
    max_level_l = models.PositiveIntegerField(default=90)
    temp_set_c = models.FloatField(default=35.0)
    temp_min_c = models.FloatField(default=25.0)
    temp_max_c = models.FloatField(default=45.0)
    hysteresis_c = models.FloatField(default=2.0)
    active = models.BooleanField(default=True)
    control_mode = models.CharField(
        max_length=10,
        choices=ControlMode.choices,
        default=ControlMode.AUTO,
    )
    manual_valve_open = models.BooleanField(default=False)
    manual_drain_valve_open = models.BooleanField(default=False)
    manual_heater_on = models.BooleanField(default=False)
    manual_heater_150_on = models.BooleanField(default=False)
    manual_heater_500_on = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Configuración del tanque'
        verbose_name_plural = 'Configuraciones de tanque'
        ordering = ['-updated_at']

    def clean(self):
        errors = {}
        if self.capacity_l <= 0:
            errors['capacity_l'] = 'La capacidad debe ser positiva.'
        if not (0 < self.min_level_l < self.max_level_l <= self.capacity_l):
            errors['min_level_l'] = (
                'Los niveles deben cumplir 0 < mínimo < máximo ≤ capacidad.'
            )
        if self.hysteresis_c < 0:
            errors['hysteresis_c'] = 'La histéresis debe ser positiva.'
        if not (self.temp_min_c <= self.temp_set_c <= self.temp_max_c):
            errors['temp_set_c'] = 'El set point debe estar entre los límites permitidos.'
        if self.temp_min_c < 0:
            errors['temp_min_c'] = 'La temperatura mínima debe ser mayor o igual a 0.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.clean()
        with transaction.atomic():
            if self.active:
                TankConfig.objects.exclude(pk=self.pk).filter(active=True).update(active=False)
            super().save(*args, **kwargs)

    @classmethod
    def get_active(cls) -> 'TankConfig':
        config = cls.objects.filter(active=True).order_by('-updated_at').first()
        if config:
            return config
        return cls.objects.create()

    def __str__(self) -> str:
        return (
            f'TankConfig(id={self.pk}, active={self.active}, set={self.temp_set_c}°C, '
            f'mode={self.control_mode})'
        )


class TankState(models.Model):
    config = models.ForeignKey(TankConfig, on_delete=models.CASCADE, related_name='states')
    level_l = models.FloatField()
    temp_c = models.FloatField()
    valve_open = models.BooleanField(default=False)
    drain_valve_open = models.BooleanField(default=False)
    heater_on = models.BooleanField(default=False)
    safe_mode = models.BooleanField(default=False)
    ts = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Estado del tanque'
        verbose_name_plural = 'Estados del tanque'
        ordering = ['-ts']

    def __str__(self) -> str:
        return f'TankState(ts={self.ts}, level={self.level_l}, temp={self.temp_c})'


class EventLog(models.Model):
    code = models.CharField(max_length=32, choices=EventCode.choices)
    message = models.CharField(max_length=255)
    severity = models.CharField(
        max_length=16,
        choices=EventSeverity.choices,
        default=EventSeverity.INFO,
    )
    ts = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Evento'
        verbose_name_plural = 'Eventos'
        ordering = ['-ts']
        indexes = [
            models.Index(fields=['ts']),
            models.Index(fields=['code']),
        ]

    def __str__(self) -> str:
        return f'[{self.ts}] {self.code}'

    @classmethod
    def log(cls, code: str, message: str, severity: str = EventSeverity.INFO) -> 'EventLog':
        return cls.objects.create(code=code, message=message, severity=severity)
