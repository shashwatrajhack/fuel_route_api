import requests
import concurrent.futures
from typing import Tuple, Dict, Any

OSRM_BASE = "https://router.project-osrm.org/route/v1/driving"
PHOTON_BASE = "https://photon.komoot.io/api/"
HEADERS = {"User-Agent": "FuelRouteAPI/1.0"}

_geocode_cache = {}

def geocode_location(location: str) -> Tuple[float, float]:
    if location in _geocode_cache:
        return _geocode_cache[location]
    
    params = {"q": location, "limit": 1}
    resp = requests.get(PHOTON_BASE, params=params, headers=HEADERS, timeout=8)
    resp.raise_for_status()
    features = resp.json().get("features", [])
    
    if not features:
        raise ValueError(f"Could not find location: '{location}'. Try format: 'Chicago, IL'")
    
    coords = features[0]["geometry"]["coordinates"]  # [lon, lat]
    result = (coords[1], coords[0])
    _geocode_cache[location] = result
    return result


def get_route(start_location: str, end_location: str) -> Dict[str, Any]:
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f_start = executor.submit(geocode_location, start_location)
        f_end = executor.submit(geocode_location, end_location)
        start_lat, start_lon = f_start.result()
        end_lat, end_lon = f_end.result()

    url = f"{OSRM_BASE}/{start_lon},{start_lat};{end_lon},{end_lat}"
    resp = requests.get(url, params={
        "overview": "full",
        "geometries": "geojson",
        "steps": "false",
    }, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if data.get("code") != "Ok":
        raise ValueError(f"Routing failed: {data.get('message', 'unknown')}")

    route = data["routes"][0]
    coords = route["geometry"]["coordinates"]
    route_points = [(c[1], c[0]) for c in coords]
    distance_miles = route["distance"] * 0.000621371
    duration_hours = route["duration"] / 3600

    map_url = (
        f"https://www.google.com/maps/dir/?api=1"
        f"&origin={start_lat},{start_lon}"
        f"&destination={end_lat},{end_lon}"
        f"&travelmode=driving"
    )

    return {
        "start_coords": {"lat": start_lat, "lon": start_lon},
        "end_coords": {"lat": end_lat, "lon": end_lon},
        "distance_miles": round(distance_miles, 1),
        "duration_hours": round(duration_hours, 2),
        "route_points": route_points,
        "map_url": map_url,
    }