from django.contrib import admin

from .models import EventLog, TankConfig, TankState


@admin.register(TankConfig)
class TankConfigAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'capacity_l',
        'min_level_l',
        'max_level_l',
        'temp_set_c',
        'hysteresis_c',
        'control_mode',
        'manual_valve_open',
        'manual_drain_valve_open',
        'manual_heater_on',
        'manual_heater_150_on',
        'manual_heater_500_on',
        'active',
        'updated_at',
    )
    list_filter = ('active', 'control_mode')
    search_fields = ('id',)
    readonly_fields = ('created_at', 'updated_at')
    list_editable = (
        'control_mode',
        'manual_valve_open',
        'manual_drain_valve_open',
        'manual_heater_on',
        'manual_heater_150_on',
        'manual_heater_500_on',
    )


@admin.register(TankState)
class TankStateAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'config',
        'level_l',
        'temp_c',
        'valve_open',
        'drain_valve_open',
        'heater_on',
        'safe_mode',
        'ts',
    )
    list_filter = ('safe_mode', 'valve_open', 'drain_valve_open', 'heater_on')
    search_fields = ('config__id',)
    ordering = ('-ts',)


@admin.register(EventLog)
class EventLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'severity', 'ts', 'message')
    list_filter = ('code', 'severity')
    search_fields = ('message',)
    ordering = ('-ts',)
