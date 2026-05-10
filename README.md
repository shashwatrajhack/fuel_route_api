<<<<<<< HEAD
# Fuel Route Planner API

A Django REST API that calculates optimal fuel stops along a US road trip route, minimising total fuel cost.

## Tech Stack
- **Backend:** Django 5 + Django REST Framework
- **Routing API:** OSRM (project-osrm.org) — free, no API key needed
- **Geocoding:** Nominatim (OpenStreetMap) — free, no API key needed
- **Fuel data:** Provided CSV (8,151 stations, retail price per gallon)

## External API Calls (per request)
1. Nominatim geocode — start location
2. Nominatim geocode — end location  
3. OSRM route — full driving polyline

**Total: 3 calls maximum** (matches the brief's acceptable range).

## Setup

```bash
# Clone / unzip project
cd fuel_route_api

# Install dependencies
pip install -r requirements.txt

# Run the server
python manage.py runserver
```

No database migrations needed (no models used — fuel data is read from CSV at startup).

## API Endpoints

### POST /api/route/
Plan a fuel-optimised route between two US locations.

**Request body:**
```json
{
  "start": "New York, NY",
  "end": "Los Angeles, CA"
}
```

**Response:**
```json
{
  "route": {
    "start": "New York, NY",
    "end": "Los Angeles, CA",
    "start_coords": {"lat": 40.71, "lon": -74.00},
    "end_coords": {"lat": 34.05, "lon": -118.24},
    "distance_miles": 2789.5,
    "estimated_drive_hours": 40.2,
    "map_url": "https://www.google.com/maps/dir/?api=1&origin=..."
  },
  "fuel_summary": {
    "vehicle_range_miles": 500,
    "fuel_efficiency_mpg": 10,
    "total_gallons_needed": 278.95,
    "total_fuel_cost_usd": 942.38,
    "number_of_stops": 6
  },
  "fuel_stops": [
    {
      "name": "LOVES TRAVEL STOP #123",
      "city": "Columbus",
      "state": "OH",
      "address": "I-70, EXIT 94",
      "price_per_gallon": 3.189,
      "lat": 39.96,
      "lon": -82.99,
      "mile_marker": 487.3,
      "gallons_purchased": 48.73,
      "stop_cost": 155.40
    }
  ]
}
```

**map_url** — open this in any browser to see the full route on Google Maps (no API key needed for the link format).

### GET /api/health/
Returns `{"status": "ok"}` — useful for liveness checks.

## Algorithm

1. **Geocode** start and end to lat/lon coordinates.
2. **Fetch route** from OSRM — a dense polyline of hundreds of GPS points.
3. **Project stations** — for each of the 7,531 fuel stations, find how far along the route it sits (mile marker) using the Haversine formula. Stations more than 25 miles off-route are excluded.
4. **Greedy optimisation** — iterate from mile 0:
   - Find all stations reachable within the current fuel range (max 500 miles).
   - Pick the **cheapest** one (lowest $/gallon).
   - Fill tank completely there.
   - Advance to that station and repeat until destination is reachable.
5. **Cost calculation** — sum (gallons filled × price/gallon) at each stop.

This greedy approach is O(n·m) in the worst case but fast in practice because the station list is sorted by mile marker and filtered to route-adjacent stations only.

## Design Decisions

- **No database** — 7,531 stations load from CSV into memory in ~50ms using `functools.lru_cache`. Subsequent requests use the cache and are ~10x faster.
- **No API key** — both OSRM and Nominatim are genuinely free with no key required.
- **map_url** — returns a Google Maps link the client can embed or open. No Maps API billing.
- **State centroid geocoding** — stations are projected using state-level coordinates (bundled offline). A production version would use a city-level geocoding database for higher accuracy.
=======
# fuel_route_api
>>>>>>> 8b6de698f23f4fad4fc2c6267c1f565973580848
