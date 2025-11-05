from __future__ import annotations

from typing import Optional

from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import EventLog
from .serializers import EventLogSerializer, TankConfigSerializer, TankStateSerializer
from .services import ControlService


class TankStateView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            level, temp = self._extract_measurements(request)
        except ValueError:
            return Response(
                {'detail': 'Los parámetros level y temp deben ser numéricos.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        service = ControlService()
        result = service.step(level_l=level, temp_c=temp)
        serializer = TankStateSerializer(result.state)
        return Response(serializer.data)

    def _extract_measurements(self, request) -> tuple[Optional[float], Optional[float]]:
        params = request.query_params
        level_param = params.get('level')
        temp_param = params.get('temp')
        level = temp = None
        if level_param is not None:
            level = float(level_param)
        if temp_param is not None:
            temp = float(temp_param)
        return level, temp


class TankConfigView(RetrieveUpdateAPIView):
    serializer_class = TankConfigSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        return ControlService().config


class EventLogView(ListAPIView):
    serializer_class = EventLogSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        limit_param = self.request.query_params.get('limit')
        queryset = EventLog.objects.all().order_by('-ts')
        if limit_param:
            try:
                limit = int(limit_param)
            except ValueError:
                limit = 50
            else:
                limit = max(1, min(limit, 500))
            queryset = queryset[:limit]
        else:
            queryset = queryset[:50]
        return queryset
