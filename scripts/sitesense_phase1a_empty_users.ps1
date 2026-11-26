$ErrorActionPreference = "Stop"

$projectRoot = (Get-Location).Path
$frontend = Join-Path $projectRoot "_integration_staging\gargi_backend\SITESENSE---MULTIMODAL-OPERATIONS-INTELLIGENCE-PLATFORM_-Gargi_backend\frontend"
$target = Join-Path $frontend "src\hooks\useOrganizationUsers.ts"

if (-not (Test-Path $target)) {
    throw "Target file not found: $target"
}

$content = Get-Content -LiteralPath $target -Raw
if ($content -notmatch "DEMO_USERS") {
    Write-Host "No DEMO_USERS reference found. No changes made."
    exit 0
}

$backupDir = Join-Path $projectRoot ("_integration_backups\empty_frontend_phase1_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
Copy-Item -LiteralPath $target -Destination (Join-Path $backupDir "useOrganizationUsers.ts") -Force

$newContent = @'
// harsh changes starts
import { useState } from 'react'
import type { DemoUser } from '../data/users'

export function useOrganizationUsers() {
  const [users, setUsers] = useState<DemoUser[]>([])
  return { users, setUsers }
}
// harsh changes end
'@

Set-Content -LiteralPath $target -Value $newContent -Encoding utf8

$verify = Get-Content -LiteralPath $target -Raw
if ($verify -match "DEMO_USERS|sitesense_demo_organization|sessionStorage") {
    Copy-Item -LiteralPath (Join-Path $backupDir "useOrganizationUsers.ts") -Destination $target -Force
    throw "Verification failed. Original file restored from backup: $backupDir"
}

Write-Host "Phase 1A applied: organization users now start empty."
Write-Host "Backup: $backupDir"
Write-Host "Next: verify the file, then we will patch the remaining mock-backed dashboard state."
