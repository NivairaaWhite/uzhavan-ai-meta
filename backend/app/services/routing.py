"""OSRM routing client for logistics-pool truck routes. OSRM's public demo
server is fine for dev; production should self-host an OSRM instance
(Docker image osrm/osrm-backend) over an India OSM extract, or swap this
for Google Maps Distance Matrix by setting GOOGLE_MAPS_API_KEY and using
the alternate function below — both return the same normalized dict so
callers don't care which one is active."""
from typing import List, Tuple

import httpx

from app.config import get_settings

settings = get_settings()


async def get_route_osrm(waypoints: List[Tuple[float, float]]) -> dict:
    """waypoints: list of (lat, lng). Returns {distance_km, duration_min, polyline}."""
    if len(waypoints) < 2:
        raise ValueError("Need at least 2 waypoints for a route")
    coords = ";".join(f"{lng},{lat}" for lat, lng in waypoints)  # OSRM wants lng,lat
    url = f"{settings.OSRM_BASE_URL}/route/v1/driving/{coords}"
    params = {"overview": "full", "geometries": "polyline"}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        route = data["routes"][0]
        return {
            "distance_km": round(route["distance"] / 1000, 2),
            "duration_min": round(route["duration"] / 60, 1),
            "polyline": route["geometry"],
        }


async def get_route_google(waypoints: List[Tuple[float, float]]) -> dict:
    if not settings.GOOGLE_MAPS_API_KEY:
        raise RuntimeError("GOOGLE_MAPS_API_KEY not set")
    origin = waypoints[0]
    destination = waypoints[-1]
    waypoints_param = "|".join(f"{lat},{lng}" for lat, lng in waypoints[1:-1])
    params = {
        "origin": f"{origin[0]},{origin[1]}",
        "destination": f"{destination[0]},{destination[1]}",
        "waypoints": waypoints_param,
        "key": settings.GOOGLE_MAPS_API_KEY,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get("https://maps.googleapis.com/maps/api/directions/json", params=params)
        resp.raise_for_status()
        data = resp.json()
        leg_distances = sum(leg["distance"]["value"] for leg in data["routes"][0]["legs"])
        leg_durations = sum(leg["duration"]["value"] for leg in data["routes"][0]["legs"])
        return {
            "distance_km": round(leg_distances / 1000, 2),
            "duration_min": round(leg_durations / 60, 1),
            "polyline": data["routes"][0]["overview_polyline"]["points"],
        }
