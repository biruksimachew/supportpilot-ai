alter table public.tickets
    add column identity_verification_status text
        not null
        default 'UNVERIFIED',

    add column identity_verification_method text,

    add column identity_verified_at timestamptz,

    add column identity_verified_order_number text,

    add column identity_verification_attempts integer
        not null
        default 0;


alter table public.tickets
    add constraint tickets_identity_verification_status_check
    check (
        identity_verification_status
        in (
            'UNVERIFIED',
            'VERIFIED',
            'FAILED'
        )
    );


alter table public.tickets
    add constraint tickets_identity_verification_method_check
    check (
        identity_verification_method is null
        or identity_verification_method
            in (
                'EMAIL_POSTCODE_ORDER'
            )
    );


alter table public.tickets
    add constraint tickets_identity_verification_attempts_check
    check (
        identity_verification_attempts >= 0
    );


alter table public.tickets
    add constraint tickets_verified_identity_requires_context
    check (
        identity_verification_status <> 'VERIFIED'
        or (
            customer_ref is not null
            and identity_verification_method is not null
            and identity_verified_at is not null
            and identity_verified_order_number is not null
        )
    );


create index tickets_identity_verification_status_idx
    on public.tickets (
        identity_verification_status
    );