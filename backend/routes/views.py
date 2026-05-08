"""DRF views for the fuel-route API."""
from __future__ import annotations

from rest_framework.decorators import api_view
from rest_framework.response import Response

from .data_loader import get_stations
from .services import plan_trip


@api_view(["GET"])
def health(request):
    stations = get_stations()
    return Response({
        "status": "ok",
        "stations_loaded": len(stations),
        "service": "fuel-route-api",
    })


@api_view(["GET"])
def stations_summary(request):
    stations = get_stations()
    if not stations:
        return Response({"count": 0, "min_price": None, "max_price": None})
    prices = [s["price"] for s in stations]
    return Response({
        "count": len(stations),
        "min_price": round(min(prices), 4),
        "max_price": round(max(prices), 4),
        "states": sorted({s["state"] for s in stations}),
    })


@api_view(["POST", "GET"])
def plan_route(request):
    if request.method == "POST":
        start = (request.data.get("start") or "").strip()
        finish = (request.data.get("finish") or "").strip()
    else:
        start = (request.query_params.get("start") or "").strip()
        finish = (request.query_params.get("finish") or "").strip()
    if not start or not finish:
        return Response(
            {"error": "Both 'start' and 'finish' are required."},
            status=400,
        )
    result = plan_trip(start, finish)
    if "error" in result:
        return Response(result, status=400)
    return Response(result)
