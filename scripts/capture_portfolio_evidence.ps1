param(
    [string]$RepoRoot = (Get-Location).Path
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path $RepoRoot).Path
$EvidenceRoot = Join-Path $RepoRoot "docs\evidence\portfolio"
$ScreenshotRoot = Join-Path $EvidenceRoot "screenshots"

New-Item -ItemType Directory -Path $EvidenceRoot -Force | Out-Null
New-Item -ItemType Directory -Path $ScreenshotRoot -Force | Out-Null

function Write-Section {
    param([string]$Text)
    Write-Host ""
    Write-Host ("=" * 72)
    Write-Host $Text
    Write-Host ("=" * 72)
}

function Invoke-CapturedNative {
    param(
        [string]$Label,
        [string]$OutputPath,
        [scriptblock]$Command
    )

    Write-Section $Label

    $previousErrorActionPreference =
        $ErrorActionPreference

    try {
        $ErrorActionPreference =
            "Continue"

        & $Command 2>&1 |
            Tee-Object -FilePath $OutputPath

        $exitCode =
            $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference =
            $previousErrorActionPreference
    }

    if ($null -eq $exitCode) {
        $exitCode = 0
    }

    if ($exitCode -ne 0) {
        throw (
            "$Label failed with exit code " +
            "$exitCode. See $OutputPath"
        )
    }
}

Push-Location $RepoRoot

try {
    Write-Section "SupportPilot M6C portfolio evidence capture"

    $generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    $head = (git rev-parse HEAD).Trim()
    $branch = (git branch --show-current).Trim()

    @(
        "generated_at_utc=$generatedAt"
        "git_branch=$branch"
        "git_commit=$head"
    ) | Set-Content `
        (Join-Path $EvidenceRoot "build-context.txt") `
        -Encoding utf8

    Invoke-CapturedNative `
        -Label "Docker Compose service state" `
        -OutputPath (Join-Path $EvidenceRoot "runtime-services.txt") `
        -Command {
            docker compose ps
        }

    Write-Section "API health evidence"

    $live = Invoke-RestMethod `
        -Uri "http://127.0.0.1:8001/health/live" `
        -Method Get

    $live |
        ConvertTo-Json -Depth 10 |
        Set-Content `
            (Join-Path $EvidenceRoot "health-live.json") `
            -Encoding utf8

    $ready = Invoke-RestMethod `
        -Uri "http://127.0.0.1:8001/health/ready" `
        -Method Get

    $ready |
        ConvertTo-Json -Depth 10 |
        Set-Content `
            (Join-Path $EvidenceRoot "health-ready.json") `
            -Encoding utf8

    Write-Host "Liveness:  $($live.status)"
    Write-Host "Readiness: $($ready.status)"

    Invoke-CapturedNative `
        -Label "Final API regression" `
        -OutputPath (Join-Path $EvidenceRoot "final-regression-api.txt") `
        -Command {
            docker compose exec -T api `
                python -m pytest -q -p no:cacheprovider
        }

    Invoke-CapturedNative `
        -Label "Final Supabase pgTAP regression" `
        -OutputPath (Join-Path $EvidenceRoot "final-regression-pgtap.txt") `
        -Command {
            npx supabase test db
        }

    Push-Location (Join-Path $RepoRoot "apps\web")

    try {
        Invoke-CapturedNative `
            -Label "Final frontend lint" `
            -OutputPath (Join-Path $EvidenceRoot "final-web-lint.txt") `
            -Command {
                npm run lint
            }

        Invoke-CapturedNative `
            -Label "Final frontend build" `
            -OutputPath (Join-Path $EvidenceRoot "final-web-build.txt") `
            -Command {
                npm run build
            }
    }
    finally {
        Pop-Location
    }

    Write-Section "Milestone evidence inventory"

    $expectedEvidence = @(
        "milestone-3-rag-evaluation.json",
        "milestone-3-rag-evaluation.txt",
        "milestone-4-commerce-safety-evaluation.json",
        "milestone-4-commerce-safety-evaluation.txt",
        "milestone-6a-adversarial-safety-evaluation.json",
        "milestone-6a-adversarial-safety-evaluation.txt",
        "milestone-6b-reliability-performance.json",
        "milestone-6b-reliability-performance.txt"
    )

    $inventory = @()

    foreach ($name in $expectedEvidence) {
        $path = Join-Path (Join-Path $RepoRoot "docs\evidence") $name

        if (Test-Path $path) {
            $hash = Get-FileHash -Algorithm SHA256 -LiteralPath $path

            $inventory += [pscustomobject]@{
                file = "evidence/$name"
                exists = $true
                sha256 = $hash.Hash.ToLowerInvariant()
            }

            Write-Host "FOUND  $name"
        }
        else {
            $inventory += [pscustomobject]@{
                file = "evidence/$name"
                exists = $false
                sha256 = $null
            }

            Write-Warning "Missing expected evidence file: $name"
        }
    }

    $inventory |
        ConvertTo-Json -Depth 10 |
        Set-Content `
            (Join-Path $EvidenceRoot "milestone-evidence-inventory.json") `
            -Encoding utf8

    $missing = @(
        $inventory |
            Where-Object { -not $_.exists }
    )

    $manifest = @"
# SupportPilot AI â€” Portfolio Evidence Manifest

Generated: $generatedAt
Git branch: $branch
Git commit: $head

## Automated runtime proof

- ``runtime-services.txt`` â€” Docker Compose service state.
- ``health-live.json`` â€” API process liveness.
- ``health-ready.json`` â€” database/pgvector readiness contract.
- ``final-regression-api.txt`` â€” complete API pytest regression.
- ``final-regression-pgtap.txt`` â€” database/RLS pgTAP regression.
- ``final-web-lint.txt`` â€” frontend lint gate.
- ``final-web-build.txt`` â€” production Next.js build gate.
- ``milestone-evidence-inventory.json`` â€” SHA-256 inventory of milestone evaluation evidence.

## Existing measured milestone evidence

- ``../milestone-3-rag-evaluation.json`` / ``.txt``
- ``../milestone-4-commerce-safety-evaluation.json`` / ``.txt``
- ``../milestone-6a-adversarial-safety-evaluation.json`` / ``.txt``
- ``../milestone-6b-reliability-performance.json`` / ``.txt``

## Screenshot set

Place curated public screenshots in ``screenshots/`` using these names:

1. ``01-agent-queue.png``
2. ``02-ticket-workspace.png``
3. ``03-ai-decision.png``
4. ``04-retrieval-evidence.png``
5. ``05-verified-order-context.png``
6. ``06-restricted-review.png``
7. ``07-operations-dashboard.png``
8. ``08-gmail-delivery-redacted.png``

See ``docs/portfolio-evidence-guide.md`` for capture guidance.

## Public-evidence rules

- Do not expose API keys, secrets, bearer tokens, cookies, local ``.env`` values, or service-role keys.
- Redact personal email addresses in the Gmail screenshot before committing it publicly.
- Prefer synthetic Northstar customer data in product screenshots.
- Do not modify historical milestone result files merely to make the final presentation cleaner.
"@

    $manifest |
        Set-Content `
            (Join-Path $EvidenceRoot "README.md") `
            -Encoding utf8

    Write-Section "Git state"

    git status --short |
        Tee-Object `
            -FilePath (Join-Path $EvidenceRoot "git-status-after-capture.txt")

    if ($missing.Count -gt 0) {
        Write-Warning (
            "Capture completed, but $($missing.Count) expected milestone " +
            "evidence file(s) were not found. Inspect milestone-evidence-inventory.json."
        )
    }

    Write-Host ""
    Write-Host "M6C automated evidence capture completed."
    Write-Host "Output: $EvidenceRoot"
}
finally {
    Pop-Location
}

