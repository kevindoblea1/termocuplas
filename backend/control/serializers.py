from __future__ import annotations

from rest_framework import serializers

from .models import EventLog, TankConfig, TankState


class TankConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = TankConfig
        fields = (
            'id',
            'capacity_l',
            'min_level_l',
            'max_level_l',
            'temp_set_c',
            'temp_min_c',
            'temp_max_c',
            'hysteresis_c',
            'active',
            'control_mode',
            'manual_valve_open',
            'manual_drain_valve_open',
            'manual_heater_on',
            'manual_heater_150_on',
            'manual_heater_500_on',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'active', 'created_at', 'updated_at')

    def validate(self, attrs):
        instance = self.instance or TankConfig()
        for key, value in attrs.items():
            setattr(instance, key, value)
        instance.clean()
        return attrs


class TankStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TankState
        fields = (
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
        read_only_fields = fields


class EventLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventLog
        fields = ('id', 'code', 'message', 'severity', 'ts')
        read_only_fields = fields
