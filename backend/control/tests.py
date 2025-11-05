from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import TankConfig, TankState
from .serializers import TankConfigSerializer


class ControlLogicTestCase(APITestCase):
    def setUp(self):
        self.config = TankConfig.get_active()

    def test_valve_opens_below_min(self):
        response = self.client.get(reverse('control:state'), {'level': self.config.min_level_l - 5})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['valve_open'])

    def test_valve_closes_at_max(self):
        self.client.get(reverse('control:state'), {'level': self.config.max_level_l - 5})
        response = self.client.get(reverse('control:state'), {'level': self.config.max_level_l})
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertFalse(response.data['valve_open'])
        self.assertTrue(response.data['drain_valve_open'])

    def test_heater_turns_on_below_band(self):
        response = self.client.get(reverse('control:state'), {
            'level': self.config.min_level_l + 5,
            'temp': self.config.temp_set_c - self.config.hysteresis_c - 1,
        })
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertTrue(response.data['heater_on'])
        self.assertFalse(response.data['drain_valve_open'])

    def test_heater_turns_off_at_setpoint(self):
        self.client.get(reverse('control:state'), {
            'level': self.config.min_level_l + 5,
            'temp': self.config.temp_set_c - self.config.hysteresis_c - 1,
        })
        response = self.client.get(reverse('control:state'), {
            'level': self.config.min_level_l + 5,
            'temp': self.config.temp_set_c,
        })
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertFalse(response.data['heater_on'])

    def test_heater_forced_off_on_low_level(self):
        self.client.get(reverse('control:state'), {
            'level': self.config.max_level_l,
            'temp': self.config.temp_set_c - self.config.hysteresis_c - 1,
        })
        response = self.client.get(reverse('control:state'), {
            'level': self.config.min_level_l - 1,
            'temp': self.config.temp_set_c - self.config.hysteresis_c - 1,
        })
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertFalse(response.data['heater_on'])
        self.assertFalse(response.data['safe_mode'])
        self.assertFalse(response.data['drain_valve_open'])

    def test_safe_mode_triggers_on_invalid_level(self):
        response = self.client.get(reverse('control:state'), {
            'level': self.config.capacity_l + 10,
            'temp': self.config.temp_set_c,
        })
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertTrue(response.data['safe_mode'])
        self.assertFalse(response.data['valve_open'])
        self.assertFalse(response.data['heater_on'])
        self.assertFalse(response.data['drain_valve_open'])

    def test_drain_valve_closes_within_range(self):
        self.client.get(reverse('control:state'), {'level': self.config.max_level_l})
        response = self.client.get(reverse('control:state'), {'level': self.config.max_level_l - 10})
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertFalse(response.data['drain_valve_open'])

    def test_manual_fill_increases_level_over_time(self):
        config = TankConfig.get_active()
        config.control_mode = 'MANUAL'
        config.manual_valve_open = True
        config.manual_drain_valve_open = False
        config.manual_heater_on = False
        config.save()

        initial_response = self.client.get(reverse('control:state'))
        self.assertEqual(status.HTTP_200_OK, initial_response.status_code)
        state = TankState.objects.order_by('-ts').first()
        previous_level = state.level_l
        state.ts = timezone.now() - timedelta(seconds=1)
        state.save(update_fields=['ts'])

        response = self.client.get(reverse('control:state'))
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertGreater(response.data['level_l'], previous_level)

        config.control_mode = 'AUTO'
        config.manual_valve_open = False
        config.manual_heater_150_on = False
        config.manual_heater_500_on = False
        config.save()

    def test_manual_drain_reduces_level_over_time(self):
        config = TankConfig.get_active()
        config.control_mode = 'MANUAL'
        config.manual_valve_open = False
        config.manual_drain_valve_open = True
        config.manual_heater_on = False
        config.save()

        initial_response = self.client.get(reverse('control:state'))
        self.assertEqual(status.HTTP_200_OK, initial_response.status_code)
        state = TankState.objects.order_by('-ts').first()
        previous_level = state.level_l
        state.ts = timezone.now() - timedelta(seconds=1)
        state.save(update_fields=['ts'])

        response = self.client.get(reverse('control:state'))
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertLess(response.data['level_l'], previous_level)

        config.control_mode = 'AUTO'
        config.manual_drain_valve_open = False
        config.manual_heater_150_on = False
        config.manual_heater_500_on = False
        config.save()

    def test_manual_aux_heaters_increase_heating(self):
        config = TankConfig.get_active()
        config.control_mode = 'MANUAL'
        config.manual_valve_open = False
        config.manual_drain_valve_open = False
        config.manual_heater_on = True
        config.manual_heater_150_on = False
        config.manual_heater_500_on = False
        config.save()

        initial_response = self.client.get(reverse('control:state'))
        self.assertEqual(status.HTTP_200_OK, initial_response.status_code)

        state = TankState.objects.order_by('-ts').first()
        state.temp_c = 32.0
        state.ts = timezone.now() - timedelta(seconds=2)
        state.save(update_fields=['temp_c', 'ts'])

        base_resp = self.client.get(reverse('control:state'))
        self.assertEqual(status.HTTP_200_OK, base_resp.status_code)
        base_temp = base_resp.data['temp_c']

        state = TankState.objects.order_by('-ts').first()
        state.temp_c = 32.0
        state.ts = timezone.now() - timedelta(seconds=2)
        state.save(update_fields=['temp_c', 'ts'])

        config.manual_heater_150_on = True
        config.save()

        aux_resp = self.client.get(reverse('control:state'))
        self.assertEqual(status.HTTP_200_OK, aux_resp.status_code)
        aux_temp = aux_resp.data['temp_c']

        self.assertGreater(aux_temp, base_temp)

        config.control_mode = 'AUTO'
        config.manual_heater_on = False
        config.manual_heater_150_on = False
        config.manual_heater_500_on = False
        config.save()

    def test_manual_mode_respects_manual_outputs(self):
        config = TankConfig.get_active()
        config.control_mode = 'MANUAL'
        config.manual_valve_open = False
        config.manual_drain_valve_open = True
        config.manual_heater_on = True
        config.save()

        response = self.client.get(reverse('control:state'), {
            'level': config.min_level_l + 10,
            'temp': config.temp_set_c - config.hysteresis_c - 5,
        })
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertFalse(response.data['valve_open'])
        self.assertTrue(response.data['drain_valve_open'])
        self.assertTrue(response.data['heater_on'])

    def test_manual_mode_still_protects_low_level_heater(self):
        config = TankConfig.get_active()
        config.control_mode = 'MANUAL'
        config.manual_valve_open = False
        config.manual_drain_valve_open = False
        config.manual_heater_on = True
        config.save()

        response = self.client.get(reverse('control:state'), {
            'level': config.min_level_l - 5,
            'temp': config.temp_set_c - config.hysteresis_c - 5,
        })
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertFalse(response.data['heater_on'])


class TankConfigSerializerTestCase(APITestCase):
    def test_rejects_setpoint_out_of_range(self):
        config = TankConfig.get_active()
        serializer = TankConfigSerializer(
            config,
            data={'temp_set_c': config.temp_max_c + 5},
            partial=True,
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('temp_set_c', serializer.errors)
