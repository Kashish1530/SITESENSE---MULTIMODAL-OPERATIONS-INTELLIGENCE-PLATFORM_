$ErrorActionPreference = "Stop"

$projectRoot = (Get-Location).Path
$frontend = Join-Path $projectRoot "_integration_staging\gargi_backend\SITESENSE---MULTIMODAL-OPERATIONS-INTELLIGENCE-PLATFORM_-Gargi_backend\frontend"
$target = Join-Path $frontend "src\App.tsx"

if (-not (Test-Path -LiteralPath $target)) { throw "App.tsx not found: $target" }
$content = (Get-Content -LiteralPath $target -Raw) -replace "`r`n", "`n"

$pattern = '(?s)\nfunction createEvidenceId\(\): string \{\n.*?\n\}\n(?=\nfunction AppContent\(\))'
if ([regex]::Matches($content, $pattern).Count -ne 1) {
  throw "Expected exactly one unused createEvidenceId helper before AppContent. No changes made."
}

$backupDir = Join-Path $projectRoot ("_integration_backups\remove_unused_evidence_id_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
Copy-Item -LiteralPath $target -Destination (Join-Path $backupDir "App.tsx") -Force

try {
  # harsh changes starts
  $content = [regex]::Replace(
    $content,
    $pattern,
    "`n// harsh changes starts`n// Removed obsolete local evidence-ID generator; evidence IDs must come from persisted backend media records.`n// harsh changes end`n",
    1
  )
  # harsh changes end

  if ($content -match 'function createEvidenceId') { throw "Verification failed: helper still exists." }
  Set-Content -LiteralPath $target -Value $content -Encoding utf8
  Write-Host "Cleanup applied: unused createEvidenceId helper removed."
  Write-Host "Backup: $backupDir"
}
catch {
  Copy-Item -LiteralPath (Join-Path $backupDir "App.tsx") -Destination $target -Force
  throw "Patch failed. Original App.tsx restored. Backup: $backupDir. Details: $($_.Exception.Message)"
}
