"""Geofence proximity checks for a delivery fleet."""

import math

EARTH_RADIUS_M = 6371000.0


def haversine_meters(lat1_deg, lon1_deg, lat2_deg, lon2_deg):
    lat1 = math.radians(lat1_deg)
    lat2 = math.radians(lat2_deg)
    d_lat = math.radians(lat2_deg - lat1_deg)
    d_lon = math.radians(lon2_deg - lon1_deg)

    a = (math.sin(d_lat / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin(d_lon / 2) ** 2)
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def within_fence(vehicle, fence):
    distance_m = haversine_meters(
        vehicle["lat"], vehicle["lon"],
        fence["center_lat"], fence["center_lon"],
    )
    return distance_m <= fence["radius_m"]


def vehicles_in_fence(vehicles, fence):
    return [v for v in vehicles if within_fence(v, fence)]
