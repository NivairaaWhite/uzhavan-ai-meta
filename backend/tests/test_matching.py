from app.services.matching import cluster_listings, PoolCandidate


def _grid(lat0, lng0, n, step_km=0.5):
    """Small cluster of points ~step_km apart near (lat0, lng0)."""
    deg_step = step_km / 111.0  # rough km->degree conversion
    return [
        PoolCandidate(f"L{i}", lat0 + i * deg_step, lng0 + i * deg_step, quantity_kg=100)
        for i in range(n)
    ]


def test_dense_cluster_forms_one_pool():
    candidates = _grid(11.0, 77.0, n=5, step_km=0.3)
    pools = cluster_listings(candidates, radius_km=8.0, min_farmers=3)
    assert len(pools) == 1
    assert len(pools[0].member_listing_ids) == 5
    assert pools[0].total_quantity_kg == 500


def test_isolated_points_form_no_pool():
    candidates = [
        PoolCandidate("A", 11.0, 77.0, 100),
        PoolCandidate("B", 13.5, 80.2, 100),   # far away
        PoolCandidate("C", 9.9, 78.1, 100),    # far away
    ]
    pools = cluster_listings(candidates, radius_km=8.0, min_farmers=3)
    assert pools == []


def test_below_minimum_count_returns_no_pools():
    candidates = _grid(11.0, 77.0, n=2, step_km=0.2)
    pools = cluster_listings(candidates, radius_km=8.0, min_farmers=3)
    assert pools == []


def test_two_separate_dense_clusters_form_two_pools():
    cluster_a = _grid(11.0, 77.0, n=3, step_km=0.2)
    cluster_b = _grid(20.0, 85.0, n=3, step_km=0.2)  # far from cluster_a
    pools = cluster_listings(cluster_a + cluster_b, radius_km=8.0, min_farmers=3)
    assert len(pools) == 2
