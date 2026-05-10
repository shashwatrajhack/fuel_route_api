from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .routing import get_route
from .optimizer import find_optimal_stops


class RoutePlannerView(APIView):
    """
    POST /api/route/
    Body: { "start": "New York, NY", "end": "Los Angeles, CA" }
    """

    def post(self, request):
        start = request.data.get("start", "").strip()
        end = request.data.get("end", "").strip()

        if not start or not end:
            return Response(
                {"error": "Both 'start' and 'end' fields are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            route_data = get_route(start, end)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": f"Routing service error: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        try:
            fuel_stops, total_fuel_cost = find_optimal_stops(
                route_data["route_points"],
                route_data["distance_miles"],
            )
        except Exception as e:
            return Response(
                {"error": f"Optimizer error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({
            "route": {
                "start": start,
                "end": end,
                "start_coords": route_data["start_coords"],
                "end_coords": route_data["end_coords"],
                "distance_miles": route_data["distance_miles"],
                "estimated_drive_hours": route_data["duration_hours"],
                "map_url": route_data["map_url"],
            },
            "fuel_summary": {
                "vehicle_range_miles": 500,
                "fuel_efficiency_mpg": 10,
                "total_gallons_needed": round(route_data["distance_miles"] / 10, 2),
                "total_fuel_cost_usd": total_fuel_cost,
                "number_of_stops": len(fuel_stops),
            },
            "fuel_stops": fuel_stops,
        })


class HealthView(APIView):
    def get(self, request):
        return Response({"status": "ok", "service": "Fuel Route Planner API"})
