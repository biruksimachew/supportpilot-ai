-- ============================================================
-- SupportPilot AI
-- Northstar Commerce Co. synthetic portfolio seed data
--
-- ALL DATA IN THIS FILE IS FICTIONAL.
-- No real customer, order or payment information is included.
-- ============================================================


-- ============================================================
-- CUSTOMERS
-- ============================================================

insert into public.customers (
    id,
    external_id,
    email,
    name,
    verification_metadata
)
values
(
    '10000000-0000-4000-8000-000000000001',
    'CUST-1001',
    'amina.demo@example.com',
    'Amina Tesfaye',
    '{"postcode_hint": "10001", "demo": true}'::jsonb
),
(
    '10000000-0000-4000-8000-000000000002',
    'CUST-1002',
    'daniel.demo@example.com',
    'Daniel Reed',
    '{"postcode_hint": "10002", "demo": true}'::jsonb
),
(
    '10000000-0000-4000-8000-000000000003',
    'CUST-1003',
    'maya.demo@example.com',
    'Maya Chen',
    '{"postcode_hint": "10003", "demo": true}'::jsonb
),
(
    '10000000-0000-4000-8000-000000000004',
    'CUST-1004',
    'noah.demo@example.com',
    'Noah Williams',
    '{"postcode_hint": "10004", "demo": true}'::jsonb
)
on conflict (id) do nothing;


-- ============================================================
-- READ-ONLY COMMERCE CACHE
-- ============================================================

insert into public.orders_cache (
    external_order_id,
    customer_ref,
    status,
    fulfillment_summary,
    total_summary,
    retrieved_at
)
values
(
    '#NS10041',
    '10000000-0000-4000-8000-000000000001',
    'IN_TRANSIT',
    '{
        "items": [
            {
                "sku": "NST-TRVL-001",
                "name": "TrailPack 28L",
                "quantity": 1
            }
        ],
        "tracking_number": "TRK-DEMO-10041",
        "carrier": "Northstar Demo Carrier",
        "fulfillment_status": "IN_TRANSIT"
    }'::jsonb,
    '{
        "currency": "USD",
        "total": "89.00"
    }'::jsonb,
    timezone('utc', now())
),
(
    '#NS10042',
    '10000000-0000-4000-8000-000000000002',
    'DELIVERED',
    '{
        "items": [
            {
                "sku": "NST-BTL-014",
                "name": "Summit Flask 750ml",
                "quantity": 1
            }
        ],
        "delivered_at": "2026-08-06",
        "fulfillment_status": "DELIVERED"
    }'::jsonb,
    '{
        "currency": "USD",
        "total": "34.00"
    }'::jsonb,
    timezone('utc', now())
),
(
    '#NS10043',
    '10000000-0000-4000-8000-000000000003',
    'PARTIALLY_FULFILLED',
    '{
        "items": [
            {
                "sku": "NST-LGT-220",
                "name": "CampGlow Lantern",
                "quantity": 1,
                "status": "SHIPPED"
            },
            {
                "sku": "NST-ORG-031",
                "name": "Packing Cube Set",
                "quantity": 1,
                "status": "PENDING"
            }
        ],
        "fulfillment_status": "PARTIALLY_FULFILLED"
    }'::jsonb,
    '{
        "currency": "USD",
        "total": "101.00"
    }'::jsonb,
    timezone('utc', now())
),
(
    '#NS10044',
    '10000000-0000-4000-8000-000000000004',
    'PROCESSING',
    '{
        "items": [
            {
                "sku": "NST-ORG-031",
                "name": "Packing Cube Set",
                "quantity": 2
            }
        ],
        "tracking_number": null,
        "fulfillment_status": "PROCESSING"
    }'::jsonb,
    '{
        "currency": "USD",
        "total": "84.00"
    }'::jsonb,
    timezone('utc', now())
)
on conflict (external_order_id) do update
set
    customer_ref = excluded.customer_ref,
    status = excluded.status,
    fulfillment_summary = excluded.fulfillment_summary,
    total_summary = excluded.total_summary,
    retrieved_at = excluded.retrieved_at;


-- ============================================================
-- KNOWLEDGE SOURCES
-- ============================================================

insert into public.knowledge_sources (
    id,
    title,
    type,
    version,
    status,
    effective_at,
    checksum,
    metadata
)
values
(
    '20000000-0000-4000-8000-000000000001',
    'Returns Policy',
    'POLICY',
    '1.0',
    'PUBLISHED',
    '2026-08-01T00:00:00Z',
    'demo-returns-policy-v1',
    '{"category": "returns", "demo": true}'::jsonb
),
(
    '20000000-0000-4000-8000-000000000002',
    'Exchange Policy',
    'POLICY',
    '1.0',
    'PUBLISHED',
    '2026-08-01T00:00:00Z',
    'demo-exchange-policy-v1',
    '{"category": "exchanges", "demo": true}'::jsonb
),
(
    '20000000-0000-4000-8000-000000000003',
    'Damaged Items Policy',
    'POLICY',
    '1.0',
    'PUBLISHED',
    '2026-08-01T00:00:00Z',
    'demo-damaged-items-v1',
    '{"category": "damaged_items", "demo": true}'::jsonb
),
(
    '20000000-0000-4000-8000-000000000004',
    'Standard Shipping Policy',
    'POLICY',
    '1.0',
    'PUBLISHED',
    '2026-08-01T00:00:00Z',
    'demo-shipping-policy-v1',
    '{"category": "shipping", "demo": true}'::jsonb
),
(
    '20000000-0000-4000-8000-000000000005',
    'Product Warranty Policy',
    'POLICY',
    '1.0',
    'PUBLISHED',
    '2026-08-01T00:00:00Z',
    'demo-warranty-policy-v1',
    '{"category": "warranty", "demo": true}'::jsonb
),
(
    '20000000-0000-4000-8000-000000000006',
    'Northstar Product Support Facts',
    'PRODUCT',
    '1.0',
    'PUBLISHED',
    '2026-08-01T00:00:00Z',
    'demo-products-v1',
    '{"category": "products", "demo": true}'::jsonb
)
on conflict (id) do nothing;


-- ============================================================
-- KNOWLEDGE CHUNKS
--
-- Embeddings intentionally remain NULL during M1.
-- M3 will generate/index embeddings through the ingestion
-- pipeline instead of embedding seed vectors by hand.
-- ============================================================

insert into public.knowledge_chunks (
    id,
    source_id,
    section,
    content,
    metadata
)
values
(
    '30000000-0000-4000-8000-000000000001',
    '20000000-0000-4000-8000-000000000001',
    'Eligibility',
    'Unused items may be returned within 30 days of delivery. Exceptions require agent approval.',
    '{"policy_category": "returns"}'::jsonb
),
(
    '30000000-0000-4000-8000-000000000002',
    '20000000-0000-4000-8000-000000000002',
    'Eligibility',
    'Eligible unused items may be exchanged within 30 days. Stock availability must be confirmed by an agent or approved process.',
    '{"policy_category": "exchanges"}'::jsonb
),
(
    '30000000-0000-4000-8000-000000000003',
    '20000000-0000-4000-8000-000000000003',
    'Damaged Item Handling',
    'For damaged items, collect the order number and a description or photo of the damage. Replacement or refund decisions require human review.',
    '{"policy_category": "damaged_items"}'::jsonb
),
(
    '30000000-0000-4000-8000-000000000004',
    '20000000-0000-4000-8000-000000000004',
    'Delivery Timing',
    'Standard shipping typically targets delivery within 3 to 7 business days after fulfillment. A guaranteed delivery date must not be claimed unless commerce data explicitly provides one.',
    '{"policy_category": "shipping"}'::jsonb
),
(
    '30000000-0000-4000-8000-000000000005',
    '20000000-0000-4000-8000-000000000005',
    'Manufacturing Warranty',
    'Manufacturing defects are covered for 2 years on designated products. Claims involving misuse or normal wear require human review.',
    '{"policy_category": "warranty"}'::jsonb
),
(
    '30000000-0000-4000-8000-000000000006',
    '20000000-0000-4000-8000-000000000006',
    'TrailPack 28L',
    'TrailPack 28L is water-resistant, not waterproof. It has a 2-year manufacturing warranty.',
    '{"sku": "NST-TRVL-001"}'::jsonb
),
(
    '30000000-0000-4000-8000-000000000007',
    '20000000-0000-4000-8000-000000000006',
    'Summit Flask 750ml',
    'The Summit Flask 750ml lid is dishwasher-safe. Hand washing is recommended for the flask body.',
    '{"sku": "NST-BTL-014"}'::jsonb
),
(
    '30000000-0000-4000-8000-000000000008',
    '20000000-0000-4000-8000-000000000006',
    'CampGlow Lantern',
    'The CampGlow Lantern is rechargeable and includes a charging cable. Its battery is not user-replaceable.',
    '{"sku": "NST-LGT-220"}'::jsonb
),
(
    '30000000-0000-4000-8000-000000000009',
    '20000000-0000-4000-8000-000000000006',
    'Packing Cube Set',
    'The Packing Cube Set contains four cubes. Machine wash cold and air dry.',
    '{"sku": "NST-ORG-031"}'::jsonb
)
on conflict (id) do nothing;