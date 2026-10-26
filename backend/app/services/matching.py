"""
Logistics pooling ("Uber-pool for crops"): group nearby, same-crop listings
into truck-fillable clusters.

Uses scikit-learn DBSCAN with the haversine metric — this is the standard,
correct way to density-cluster lat/lng points (it respects the earth's
curvature, unlike naive Euclidean clustering on raw degrees) and needs no
database extension, so it runs identically in dev and prod.

At very large scale (multi-million concurrent listings) this step is
better pushed into the database as `ST_ClusterDBSCAN` over a PostGIS
geography column — see docs/ARCHITECTURE.md for that migration. Below
that scale (which covers a state-wide rollout), doing it in the app layer
is simpler to test, deploy, and debug.
"""
from dataclasses import dataclass, field
from typing import List, Sequence

import numpy as np
from sklearn.cluster import DBSCAN

from app.config import get_settings

settings = get_settings()

EARTH_RADIUS_KM = 6371.0088


@dataclass
class PoolCandidate:
    listing_id: str
    latitude: float
    longitude: float
    quantity_kg: float


@dataclass
class PoolResult:
    member_listing_ids: List[str]
    centroid_lat: float
    centroid_lng: float
    total_quantity_kg: float = 0.0


def cluster_listings(
    candidates: Sequence[PoolCandidate],
    radius_km: float = None,
    min_farmers: int = None,
) -> List[PoolResult]:
    """Groups same-crop-type candidates into pools within `radius_km` of
    each other, discarding clusters smaller than `min_farmers` (too small
    to justify dispatching a truck)."""
    radius_km = settings.POOLING_RADIUS_KM if radius_km is None else radius_km
    min_farmers = settings.POOLING_MIN_FARMERS if min_farmers is None else min_farmers

    if len(candidates) < min_farmers:
        return []

    coords_rad = np.radians([[c.latitude, c.longitude] for c in candidates])
    eps = radius_km / EARTH_RADIUS_KM  # DBSCAN eps in radians for haversine metric

    db = DBSCAN(eps=eps, min_samples=min_farmers, metric="haversine")
    labels = db.fit_predict(coords_rad)

    pools: List[PoolResult] = []
    for label in sorted(set(labels)):
        if label == -1:
            continue  # noise: farmers too isolated to pool profitably
        members = [c for c, lbl in zip(candidates, labels) if lbl == label]
        centroid_lat = float(np.mean([m.latitude for m in members]))
        centroid_lng = float(np.mean([m.longitude for m in members]))
        total_qty = float(sum(m.quantity_kg for m in members))
        pools.append(
            PoolResult(
                member_listing_ids=[m.listing_id for m in members],
                centroid_lat=centroid_lat,
                centroid_lng=centroid_lng,
                total_quantity_kg=total_qty,
            )
        )
    return pools
