# Architecture

## System overview

```
                 ┌─────────────────────────┐
                 │   Flutter Mobile App     │
                 │  (farmer / student agent)│
                 └───────────┬──────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │ offline             │ REST (sync)          │ WebSocket
         ▼                     ▼                      ▼
 ┌──────────────┐      ┌───────────────┐       ┌──────────────┐
 │ On-device     │      │  FastAPI      │       │  Bhashini     │
 │ TFLite model  │      │  backend      │◄─────►│  (voice ASR/  │
 │ (YOLOv8 INT8) │      │               │       │  TTS/NMT)     │
 └──────────────┘      └───────┬───────┘       └──────────────┘
                                │
        ┌───────────────┬──────┴───────┬────────────────┐
        ▼               ▼              ▼                ▼
 ┌─────────────┐ ┌─────────────┐ ┌───────────┐  ┌────────────────┐
 │ Postgres     │ │ Redis +     │ │ Razorpay  │  │ DigiLocker      │
 │ (+ PostGIS   │ │ Celery      │ │ (escrow,  │  │ (e-KYC, no raw  │
 │  optional)   │ │ (scraping,  │ │  payouts) │  │  ID storage)    │
 │              │ │  pooling)   │ │           │  │                 │
 └─────────────┘ └─────────────┘ └───────────┘  └────────────────┘
```

## Design decisions that deviate from the original blueprint, and why

### 1. Geography: plain lat/lng floats, PostGIS as an optional upgrade

The blueprint mandated PostGIS for all spatial work. This repo stores
`latitude`/`longitude` as plain `Float` columns and does clustering in
the application layer (`services/matching.py`, scikit-learn `DBSCAN`
with the haversine metric) instead.

Why: it makes the entire backend runnable and testable on plain SQLite
with zero extra infrastructure (see `backend/tests/`), while still being
the textbook-correct way to density-cluster geographic points at
realistic MVP-to-mid scale (tens of thousands of concurrent listings).
PostGIS's `ST_ClusterDBSCAN` is the right move once you're past that —
here's the migration path when you need it:

```sql
ALTER TABLE crop_listings ADD COLUMN geog geography(Point, 4326)
  GENERATED ALWAYS AS (ST_MakePoint(longitude, latitude)::geography) STORED;
CREATE INDEX idx_crop_listings_geog ON crop_listings USING GIST (geog);

SELECT id, ST_ClusterDBSCAN(geog::geometry, eps := 8000, minpoints := 3)
         OVER () AS cluster_id
FROM crop_listings WHERE status = 'available';
```

Swap `services/matching.py`'s implementation for a raw query using the
above once listing volume actually demands it — the `PoolCandidate`/
`PoolResult` interface it exposes to `tasks.py` doesn't need to change.

### 2. Fair Price Algorithm is an explicit design, not a blueprint transcription

The source document referenced a "Price Algorithm" but the actual
formula didn't come through (likely an image that wasn't extracted as
text). `services/pricing.py` implements and documents a specific,
tunable formula:

```
fair_price = (wholesale + farmer_share × (retail − wholesale)) × (1 − platform_fee_pct)
```

with a safe fallback (small guaranteed premium over wholesale) when
there's no trustworthy retail signal. Every weight is a `Settings`
field — re-tune per crop/region without touching code. If you have the
actual intended formula from the original spec, swap the body of
`compute_fair_price()`; every caller goes through that one function.

### 3. Retail price scraping is stubbed, not faked

Quick-commerce apps (BigBasket, Zepto, Blinkit) don't publish public
price APIs, and scraping their consumer-facing apps directly generally
violates their Terms of Service. `tasks.scrape_retail_prices` is wired
into the Celery beat schedule with the correct shape but currently
no-ops with a clear log message. Real options, in order of
preference: (a) an official partner/affiliate data feed if one of these
platforms offers one in your region, (b) a manual daily-entry admin
endpoint (cheap to add: a POST to `/market/prices` restricted to
`UserRole.ADMIN`), (c) a compliant scrape only after confirming it
doesn't violate the target site's ToS.

### 4. Post-harvest advisor is a transparent heuristic, not a black-box model

`services/post_harvest_advisor.py` answers "what should I do with this crop
today?" by greedily allocating a lot across four channels — sell now
(capped at a demand estimate), cold-store, send to processing, or flag as
at-risk — in that priority order, using whatever spoilage/price/capacity
data the platform actually has. Every threshold (demand lookback window,
facility search radius, the no-history sell fraction, the illustrative
distress-sale discount used only for the comparison baseline) is a
`Settings` field (`POST_HARVEST_*`), and every response includes the
`reasoning` that produced it.

This is intentionally not a constrained optimizer yet. A proper version
would jointly maximize net value subject to capacity constraints (e.g.
PuLP/OR-Tools) instead of allocating channel-by-channel in a fixed order —
worth doing once there's enough real order/facility history for that to
actually outperform the greedy pass. The `recommend_allocation()` function
signature is the seam: swap its body, not its callers.

Known limitations, on purpose rather than by oversight:
- **Demand is a proxy, not a fact.** `_estimate_daily_demand_kg` uses the
  platform's own recent `Order` volume for the crop — real but partial,
  since it can't see a farmer's mandi/door-to-door sales outside the app.
- **Facility capacity doesn't decrement on recommendation.** A
  recommendation is advice, not a booking — `available_capacity_kg` /
  `remaining_intake_today_kg` only change via admin updates or the daily
  Celery reset (`tasks.reset_daily_processing_intake`). Add a real booking
  endpoint before relying on this at a scale where double-recommending the
  same capacity to two farmers becomes likely.
- **No live facility feed.** `StorageFacility`/`ProcessingUnit` rows are
  onboarded manually via admin-only endpoints — same honesty as §3 above
  on retail-price scraping: there's no public API for this either.

### 5. Agmarknet scraping prefers the OGD India JSON API over HTML parsing

`tasks._fetch_agmarknet_for_crop` tries `data.gov.in`'s structured
resource first (stable schema) and only falls back to parsing
Agmarknet's HTML report if no `OGD_INDIA_API_KEY` is configured. HTML
scraping is inherently fragile — the selectors in that fallback path
are the first thing to check if `scrape_agmarknet_prices` starts
returning zero rows.

## Data flow: a scan, end to end

1. Farmer opens the app (works with zero signal), points camera at
   produce.
2. `TfliteService` runs the on-device YOLOv8 INT8 model — grading never
   leaves the phone.
3. `LocalDbService` writes the result to Hive **immediately** — this is
   the row of truth until sync succeeds.
4. When connectivity returns, `SyncScreen` (manual, so 2G data isn't
   silently consumed) calls `POST /crop-listings/sync`, which the
   backend dedupes on `offline_scan_uuid`.
5. `recompute_fair_prices` (hourly, Celery beat) attaches a fair price
   from the latest `MarketPrice` row for that crop/district.
6. `run_logistics_pooling` (hourly) clusters same-crop nearby listings
   into a `LogisticsPool` once enough farmers have unsold stock.
7. A buyer places an `Order`; Razorpay holds payment in escrow;
   `confirm_payment` verifies the signature; delivery confirmation
   later triggers `create_route_transfer` to release funds to the
   farmer's linked account.

## What's intentionally NOT built here

- Admin dashboard UI (backend has everything a dashboard would call —
  building the dashboard itself is a separate frontend project).
- Push notifications (the `notifications`-shaped hook exists in
  `tasks.py`'s docstring intent but isn't implemented — pick FCM for
  Android and wire a `send_notification` task once you have a use case).
- Multi-language UI strings beyond the Tamil/English asset stub in
  `mobile/assets/lang/` — full i18n coverage is a content task, not an
  architecture one.
- A booking/confirmation flow for post-harvest storage and processing
  slots (see §4 above) — today's advisor recommends and logs, it doesn't
  reserve capacity or notify the facility.
