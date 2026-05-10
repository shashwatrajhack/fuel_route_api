"""
Fast fuel stop optimizer.
Key optimizations:
- Only sample every Nth route point (not all hundreds)
- Use bounding box pre-filter before Haversine (eliminates 95% of stations instantly)
- lru_cache so station list loads once ever
"""

import math
import csv
import os
import functools
from typing import List, Tuple, Dict, Optional

MAX_RANGE_MILES = 500
MPG = 10
TANK_GALLONS = MAX_RANGE_MILES / MPG  # 50 gallons
CSV_PATH = os.path.join(os.path.dirname(__file__), 'fuel_prices.csv')

STATE_CENTROIDS = {
    'AL': (32.806671, -86.791130), 'AK': (61.370716, -152.404419),
    'AZ': (33.729759, -111.431221), 'AR': (34.969704, -92.373123),
    'CA': (36.116203, -119.681564), 'CO': (39.059811, -105.311104),
    'CT': (41.597782, -72.755371), 'DE': (39.318523, -75.507141),
    'FL': (27.766279, -81.686783), 'GA': (33.040619, -83.643074),
    'HI': (21.094318, -157.498337), 'ID': (44.240459, -114.478828),
    'IL': (40.349457, -88.986137), 'IN': (39.849426, -86.258278),
    'IA': (42.011539, -93.210526), 'KS': (38.526600, -96.726486),
    'KY': (37.668140, -84.670067), 'LA': (31.169960, -91.867805),
    'ME': (44.693947, -69.381927), 'MD': (39.063946, -76.802101),
    'MA': (42.230171, -71.530106), 'MI': (43.326618, -84.536095),
    'MN': (45.694454, -93.900192), 'MS': (32.741646, -89.678696),
    'MO': (38.456085, -92.288368), 'MT': (46.921925, -110.454353),
    'NE': (41.125370, -98.268082), 'NV': (38.313515, -117.055374),
    'NH': (43.452492, -71.563896), 'NJ': (40.298904, -74.521011),
    'NM': (34.840515, -106.248482), 'NY': (42.165726, -74.948051),
    'NC': (35.630066, -79.806419), 'ND': (47.528912, -99.784012),
    'OH': (40.388783, -82.764915), 'OK': (35.565342, -96.928917),
    'OR': (44.572021, -122.070938), 'PA': (40.590752, -77.209755),
    'RI': (41.680893, -71.511780), 'SC': (33.856892, -80.945007),
    'SD': (44.299782, -99.438828), 'TN': (35.747845, -86.692345),
    'TX': (31.054487, -97.563461), 'UT': (40.150032, -111.862434),
    'VT': (44.045876, -72.710686), 'VA': (37.769337, -78.169968),
    'WA': (47.400902, -121.490494), 'WV': (38.491226, -80.954453),
    'WI': (44.268543, -89.616508), 'WY': (42.755966, -107.302490),
    'DC': (38.897438, -77.026817),
}

def haversine(lat1, lon1, lat2, lon2):
    R = 3958.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return 2 * R * math.asin(math.sqrt(a))

@functools.lru_cache(maxsize=1)
def load_stations():
    stations = []
    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            state = row['State'].strip().upper()
            if state not in STATE_CENTROIDS:
                continue
            try:
                price = float(row['Retail Price'])
            except (ValueError, KeyError):
                continue
            clat, clon = STATE_CENTROIDS[state]
            stations.append({
                'name': row.get('Truckstop Name', '').strip(),
                'address': row.get('Address', '').strip(),
                'city': row.get('City', '').strip(),
                'state': state,
                'price': price,
                'lat': clat,
                'lon': clon,
            })
    return stations

def find_optimal_stops(route_points, total_distance_miles):
    stations = load_stations()

  
    step = max(1, len(route_points) // 100)
    sampled = route_points[::step]
    if route_points[-1] not in sampled:
        sampled.append(route_points[-1])

    lats = [p[0] for p in sampled]
    lons = [p[1] for p in sampled]
    min_lat, max_lat = min(lats) - 1.0, max(lats) + 1.0
    min_lon, max_lon = min(lons) - 1.0, max(lons) + 1.0

    # ── OPTIMIZATION 3: pre-filter stations to bounding box (cheap compare) ───
    nearby = [s for s in stations
              if min_lat <= s['lat'] <= max_lat and min_lon <= s['lon'] <= max_lon]

    cum = [0.0]
    for i in range(1, len(sampled)):
        d = haversine(sampled[i-1][0], sampled[i-1][1], sampled[i][0], sampled[i][1])
        cum.append(cum[-1] + d)
    total_sampled = cum[-1] if cum[-1] > 0 else total_distance_miles

    # Scale factor to map sampled distances → actual route distances
    scale = total_distance_miles / total_sampled if total_sampled > 0 else 1.0

   
    MAX_DETOUR = 50.0  # miles — wider since we're using state centroids
    route_stations = []
    for st in nearby:
        best_mile = None
        best_d = float('inf')
        for i, (rlat, rlon) in enumerate(sampled):
            # Quick bounding box skip before expensive haversine
            if abs(st['lat'] - rlat) > 1.5 or abs(st['lon'] - rlon) > 1.5:
                continue
            d = haversine(st['lat'], st['lon'], rlat, rlon)
            if d < best_d:
                best_d = d
                best_mile = cum[i] * scale
        if best_d <= MAX_DETOUR and best_mile is not None:
            if 0 < best_mile < total_distance_miles:
                route_stations.append((best_mile, st))

    route_stations.sort(key=lambda x: x[0])

    if not route_stations:
        prices = [s['price'] for s in stations]
        avg = sum(prices) / len(prices) if prices else 3.5
        return [], round((total_distance_miles / MPG) * avg, 2)

    
    stops = []
    current_mile = 0.0
    fuel_in_tank = TANK_GALLONS
    total_cost = 0.0

    while current_mile < total_distance_miles:
        if (total_distance_miles - current_mile) <= fuel_in_tank * MPG:
            break  # Can reach destination

        reachable_limit = current_mile + fuel_in_tank * MPG
        candidates = [(m, s) for m, s in route_stations if current_mile < m <= reachable_limit]

        if not candidates:
            future = [(m, s) for m, s in route_stations if m > current_mile]
            if not future:
                break
            candidates = [future[0]]

        best_mile, best_st = min(candidates, key=lambda x: x[1]['price'])

        miles_driven = best_mile - current_mile
        fuel_in_tank -= miles_driven / MPG
        gallons_to_fill = TANK_GALLONS - fuel_in_tank
        stop_cost = gallons_to_fill * best_st['price']
        total_cost += stop_cost
        fuel_in_tank = TANK_GALLONS

        stops.append({
            'name': best_st['name'],
            'city': best_st['city'],
            'state': best_st['state'],
            'address': best_st['address'],
            'price_per_gallon': round(best_st['price'], 3),
            'lat': best_st['lat'],
            'lon': best_st['lon'],
            'mile_marker': round(best_mile, 1),
            'gallons_purchased': round(gallons_to_fill, 2),
            'stop_cost': round(stop_cost, 2),
        })
        current_mile = best_mile


    final_gallons = (total_distance_miles - current_mile) / MPG
    avg_p = sum(s['price'] for _, s in route_stations) / len(route_stations)
    total_cost += final_gallons * avg_p

    return stops, round(total_cost, 2)