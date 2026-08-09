begin;

create extension if not exists pgtap with schema extensions;

select plan(9);


-- ============================================================
-- TEST IDENTITIES
-- ============================================================

insert into auth.users (id, email)
values
(
    '11111111-1111-4111-8111-111111111111',
    'agent@supportpilot.test'
),
(
    '22222222-2222-4222-8222-222222222222',
    'manager@supportpilot.test'
),
(
    '33333333-3333-4333-8333-333333333333',
    'admin@supportpilot.test'
),
(
    '44444444-4444-4444-8444-444444444444',
    'disabled@supportpilot.test'
),
(
    '55555555-5555-4555-8555-555555555555',
    'outsider@supportpilot.test'
);


insert into public.users (
    id,
    role,
    name,
    email,
    status
)
values
(
    '11111111-1111-4111-8111-111111111111',
    'SUPPORT_AGENT',
    'Test Agent',
    'agent@supportpilot.test',
    'ACTIVE'
),
(
    '22222222-2222-4222-8222-222222222222',
    'SUPPORT_MANAGER',
    'Test Manager',
    'manager@supportpilot.test',
    'ACTIVE'
),
(
    '33333333-3333-4333-8333-333333333333',
    'SYSTEM_ADMIN',
    'Test Admin',
    'admin@supportpilot.test',
    'ACTIVE'
),
(
    '44444444-4444-4444-8444-444444444444',
    'SUPPORT_AGENT',
    'Disabled Agent',
    'disabled@supportpilot.test',
    'DISABLED'
);


-- ============================================================
-- TEST-SCOPED BUSINESS DATA
--
-- These IDs are intentionally isolated from normal seed data.
-- Tests below only count these rows so adding portfolio fixtures
-- cannot change security-test expectations.
-- ============================================================

insert into public.customers (
    id,
    external_id,
    email,
    name
)
values (
    'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
    'customer-rls-test-001',
    'customer-rls@example.test',
    'RLS Test Customer'
);


insert into public.tickets (
    id,
    channel,
    customer_ref
)
values (
    'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
    'chat',
    'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
);


insert into public.orders_cache (
    external_order_id,
    customer_ref,
    status
)
values (
    'ORDER-RLS-TEST-001',
    'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
    'IN_TRANSIT'
);


insert into public.knowledge_sources (
    id,
    title,
    type,
    version,
    status,
    checksum
)
values
(
    'cccccccc-cccc-4ccc-8ccc-cccccccccccc',
    'RLS Published Shipping Policy',
    'POLICY',
    'rls-test-1.0',
    'PUBLISHED',
    'rls-test-published-checksum'
),
(
    'dddddddd-dddd-4ddd-8ddd-dddddddddddd',
    'RLS Draft Return Policy',
    'POLICY',
    'rls-test-2.0-draft',
    'DRAFT',
    'rls-test-draft-checksum'
);


-- ============================================================
-- SUPPORT AGENT
-- ============================================================

set local role authenticated;

set local request.jwt.claim.sub =
    '11111111-1111-4111-8111-111111111111';


select results_eq(
    $$
        select count(*)
        from public.tickets
        where id = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'
    $$,
    array[1::bigint],
    'active support agent can read support tickets'
);


select results_eq(
    $$
        select count(*)
        from public.customers
        where id = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
    $$,
    array[1::bigint],
    'active support agent can read customer context'
);


select results_eq(
    $$
        select count(*)
        from public.orders_cache
        where external_order_id = 'ORDER-RLS-TEST-001'
    $$,
    array[1::bigint],
    'active support agent can read order context'
);


select results_eq(
    $$
        select count(*)
        from public.knowledge_sources
        where id in (
            'cccccccc-cccc-4ccc-8ccc-cccccccccccc',
            'dddddddd-dddd-4ddd-8ddd-dddddddddddd'
        )
    $$,
    array[1::bigint],
    'support agent can only read published knowledge'
);


select results_eq(
    $$
        select count(*)
        from public.users
        where id in (
            '11111111-1111-4111-8111-111111111111',
            '22222222-2222-4222-8222-222222222222',
            '33333333-3333-4333-8333-333333333333',
            '44444444-4444-4444-8444-444444444444'
        )
    $$,
    array[3::bigint],
    'support agent only sees active internal staff'
);


select throws_ok(
    $$
        update public.tickets
        set priority = 'P1'
        where id = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'
    $$,
    '42501',
    'permission denied for table tickets',
    'browser-authenticated agent cannot directly mutate ticket state'
);


-- ============================================================
-- SUPPORT MANAGER
-- ============================================================

set local request.jwt.claim.sub =
    '22222222-2222-4222-8222-222222222222';


select results_eq(
    $$
        select count(*)
        from public.knowledge_sources
        where id in (
            'cccccccc-cccc-4ccc-8ccc-cccccccccccc',
            'dddddddd-dddd-4ddd-8ddd-dddddddddddd'
        )
    $$,
    array[2::bigint],
    'support manager can inspect draft and published knowledge'
);


select results_eq(
    $$
        select count(*)
        from public.users
        where id in (
            '11111111-1111-4111-8111-111111111111',
            '22222222-2222-4222-8222-222222222222',
            '33333333-3333-4333-8333-333333333333',
            '44444444-4444-4444-8444-444444444444'
        )
    $$,
    array[4::bigint],
    'support manager can inspect disabled staff profiles'
);


-- ============================================================
-- AUTHENTICATED USER WITHOUT SUPPORTPILOT PROFILE
-- ============================================================

set local request.jwt.claim.sub =
    '55555555-5555-4555-8555-555555555555';


select results_eq(
    $$
        select count(*)
        from public.tickets
        where id = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'
    $$,
    array[0::bigint],
    'authenticated user without active SupportPilot role has no ticket access'
);


select * from finish();

rollback;