$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
$ApiBaseUrl = "http://127.0.0.1:8001"


function Write-Section {
    param([string]$Title)

    Write-Host ""
    Write-Host "===== $Title ====="
}

function Assert-Equal {
    param(
        $Actual,
        $Expected,
        [string]$Message
    )

    if ($Actual -ne $Expected) {
        throw "$Message. Expected '$Expected', got '$Actual'."
    }

    Write-Host "PASS: $Message"
}

function Invoke-PsqlScalar {
    param([string]$Query)

    $result = docker exec -i `
        supabase_db_supportpilot-ai `
        psql `
        -U postgres `
        -d postgres `
        -tAc $Query

    if ($LASTEXITCODE -ne 0) {
        throw "PostgreSQL command failed."
    }

    return ($result | Out-String).Trim()
}


Write-Host "SupportPilot AI - Milestone 1 Foundation Smoke Test"
Write-Host "Run timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss K')"


# ============================================================
# API LIVENESS
# ============================================================

Write-Section "API Liveness"

$live = Invoke-RestMethod `
    -Uri "$ApiBaseUrl/health/live" `
    -Method Get

Assert-Equal `
    $live.status `
    "ok" `
    "API process is alive"

Assert-Equal `
    $live.service `
    "supportpilot-api" `
    "Correct API service responded"


# ============================================================
# API READINESS
# ============================================================

Write-Section "Dependency Readiness"

$ready = Invoke-RestMethod `
    -Uri "$ApiBaseUrl/health/ready" `
    -Method Get

Assert-Equal `
    $ready.status `
    "ready" `
    "API reports ready"

Assert-Equal `
    $ready.dependencies.database `
    $true `
    "PostgreSQL reachable from API"

Assert-Equal `
    $ready.dependencies.pgvector `
    $true `
    "pgvector available from API"


# ============================================================
# PGVECTOR
# ============================================================

Write-Section "pgvector"

$vectorCount = Invoke-PsqlScalar @"
select count(*)
from pg_extension
where extname = 'vector';
"@

Assert-Equal `
    $vectorCount `
    "1" `
    "vector extension installed"


# ============================================================
# CORE SCHEMA
# ============================================================

Write-Section "Core Database Schema"

$coreTableCount = Invoke-PsqlScalar @"
select count(*)
from pg_tables
where schemaname = 'public'
and tablename in (
    'users',
    'customers',
    'tickets',
    'messages',
    'orders_cache',
    'knowledge_sources',
    'knowledge_chunks',
    'ai_runs',
    'retrieval_evidence',
    'tool_calls',
    'agent_actions',
    'audit_events'
);
"@

Assert-Equal `
    $coreTableCount `
    "12" `
    "All 12 core SupportPilot tables exist"


# ============================================================
# ROW LEVEL SECURITY
# ============================================================

Write-Section "Row Level Security"

$rlsTableCount = Invoke-PsqlScalar @"
select count(*)
from pg_tables
where schemaname = 'public'
and rowsecurity = true
and tablename in (
    'users',
    'customers',
    'tickets',
    'messages',
    'orders_cache',
    'knowledge_sources',
    'knowledge_chunks',
    'ai_runs',
    'retrieval_evidence',
    'tool_calls',
    'agent_actions',
    'audit_events'
);
"@

Assert-Equal `
    $rlsTableCount `
    "12" `
    "RLS enabled on all core tables"


# ============================================================
# SYNTHETIC DATABASE DATA
# ============================================================

Write-Section "Synthetic Northstar Data"

$customerCount = Invoke-PsqlScalar `
    "select count(*) from public.customers;"

$orderCount = Invoke-PsqlScalar `
    "select count(*) from public.orders_cache;"

$knowledgeSourceCount = Invoke-PsqlScalar `
    "select count(*) from public.knowledge_sources;"

$knowledgeChunkCount = Invoke-PsqlScalar `
    "select count(*) from public.knowledge_chunks;"

Assert-Equal `
    $customerCount `
    "4" `
    "4 synthetic customers loaded"

Assert-Equal `
    $orderCount `
    "4" `
    "4 synthetic orders loaded"

Assert-Equal `
    $knowledgeSourceCount `
    "6" `
    "6 published knowledge sources loaded"

Assert-Equal `
    $knowledgeChunkCount `
    "9" `
    "9 knowledge chunks loaded"


# ============================================================
# COMMERCE FIXTURES
# ============================================================

Write-Section "Commerce Fixtures"

$products = Get-Content `
    "services\commerce-mock\fixtures\products.json" `
    -Raw |
    ConvertFrom-Json

$customers = Get-Content `
    "services\commerce-mock\fixtures\customers.json" `
    -Raw |
    ConvertFrom-Json

$orders = Get-Content `
    "services\commerce-mock\fixtures\orders.json" `
    -Raw |
    ConvertFrom-Json

$scenarios = Get-Content `
    "tests\fixtures\support_scenarios.json" `
    -Raw |
    ConvertFrom-Json

Assert-Equal `
    @($products).Count `
    4 `
    "4 product fixtures available"

Assert-Equal `
    @($customers).Count `
    4 `
    "4 customer fixtures available"

Assert-Equal `
    @($orders).Count `
    4 `
    "4 order fixtures available"

Assert-Equal `
    @($scenarios).Count `
    8 `
    "8 baseline support scenarios available"


# ============================================================
# DATABASE SECURITY TESTS
# ============================================================

Write-Section "Database Security Tests"

$dbTestOutput = & cmd.exe /d /c "npx supabase test db 2>&1"
$dbTestExitCode = $LASTEXITCODE

$dbTestOutput | ForEach-Object {
    Write-Host $_
}

if ($dbTestExitCode -ne 0) {
    throw "Supabase database tests failed."
}

Write-Host "PASS: Supabase database/RLS tests"

# ============================================================
# API TESTS
# ============================================================

Write-Section "API Tests"

docker compose exec -T api `
    python -m pytest `
    -q `
    -p no:cacheprovider

if ($LASTEXITCODE -ne 0) {
    throw "FastAPI tests failed."
}

Write-Host "PASS: FastAPI automated tests"


# ============================================================
# FINAL RESULT
# ============================================================

Write-Section "Milestone Result"

Write-Host "STATUS: PASSED"
Write-Host "Milestone 1 foundation acceptance checks completed successfully."
