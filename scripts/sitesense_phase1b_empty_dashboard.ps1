$ErrorActionPreference = "Stop"

$projectRoot = (Get-Location).Path
$frontend = Join-Path $projectRoot "_integration_staging\gargi_backend\SITESENSE---MULTIMODAL-OPERATIONS-INTELLIGENCE-PLATFORM_-Gargi_backend\frontend"
$target = Join-Path $frontend "src\App.tsx"

if (-not (Test-Path -LiteralPath $target)) { throw "App.tsx not found: $target" }

$content = (Get-Content -LiteralPath $target -Raw) -replace "`r`n", "`n"

# Fail safely if the expected source has already changed.
$required = @(
  "INSPECTIONS,",
  "useState<InspectionRecord[]>(INSPECTIONS)",
  "useState<InspectionFinding[]>(INSPECTION_FINDINGS)",
  "useState<InspectionEvidence[]>(INSPECTION_EVIDENCE)",
  "useState<CorrectiveAction[]>(CORRECTIVE_ACTIONS)",
  "if (!remoteItems || remoteItems.length === 0) return",
  "if (!remoteUsers || remoteUsers.length === 0) return"
)
foreach ($token in $required) {
  if (-not $content.Contains($token)) { throw "Expected source anchor not found: $token. No changes made." }
}

$backupDir = Join-Path $projectRoot ("_integration_backups\empty_frontend_phase1b_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
Copy-Item -LiteralPath $target -Destination (Join-Path $backupDir "App.tsx") -Force

try {
  # harsh changes starts
  $content = $content.Replace(@'
import {
  INSPECTIONS,
  INSPECTION_FINDINGS,
  INSPECTION_EVIDENCE,
  CORRECTIVE_ACTIONS,
} from './data/inspectionData'

'@, "// harsh changes starts`n// Removed demo inspection-data import.`n// harsh changes end`n")

  $content = $content.Replace(@'
  const [inspections, setInspections] =
    useState<InspectionRecord[]>(INSPECTIONS)

  const [findings, setFindings] =
    useState<InspectionFinding[]>(INSPECTION_FINDINGS)

  const [evidence, setEvidence] =
    useState<InspectionEvidence[]>(INSPECTION_EVIDENCE)

  const [correctiveActions, setCorrectiveActions] =
    useState<CorrectiveAction[]>(CORRECTIVE_ACTIONS)
'@, @'
  // harsh changes starts
  const [inspections, setInspections] = useState<InspectionRecord[]>([])
  const [findings, setFindings] = useState<InspectionFinding[]>([])
  const [evidence, setEvidence] = useState<InspectionEvidence[]>([])
  const [correctiveActions, setCorrectiveActions] = useState<CorrectiveAction[]>([])
  // harsh changes end
'@)

  $content = [regex]::Replace($content, '(?m)^\s*if \(!remoteItems \|\| remoteItems\.length === 0\) return\s*\n', '')
  $content = $content.Replace(@'
        setInspections(prev => {
          const remoteIds = new Set(mapped.map(m => m.id))
          return [...mapped, ...prev.filter(p => !remoteIds.has(p.id))]
        })
'@, @'
        // harsh changes starts
        setInspections(mapped)
        // harsh changes end
'@)

  $content = [regex]::Replace($content, '(?m)^\s*if \(!remoteUsers \|\| remoteUsers\.length === 0\) return\s*\n', '')
  $content = $content.Replace("          employeeId: `EMP-${ru.id.slice(0, 6).toUpperCase()}`,", "          employeeId: '',")
  $content = $content.Replace("          password: 'SiteSense@2026',", "          password: '',")
  $content = $content.Replace("          siteId: ru.site_ids?.[0] || 'SITE-001',", "          siteId: ru.site_ids?.[0] ?? null,")
  $content = $content.Replace(@'
        setUsers(prev => {
          const remoteEmails = new Set(mappedUsers.map(u => u.email.toLowerCase()))
          const filtered = prev.filter(p => !remoteEmails.has(p.email.toLowerCase()))
          return [...filtered, ...mappedUsers]
        })
'@, @'
        // harsh changes starts
        setUsers(mappedUsers)
        // harsh changes end
'@)
  # harsh changes end

  Set-Content -LiteralPath $target -Value $content -Encoding utf8

  $verify = Get-Content -LiteralPath $target -Raw
  $bad = @(
    "INSPECTIONS,",
    "INSPECTION_FINDINGS,",
    "INSPECTION_EVIDENCE,",
    "CORRECTIVE_ACTIONS,",
    "useState<InspectionRecord[]>(INSPECTIONS)",
    "if (!remoteItems || remoteItems.length === 0) return",
    "if (!remoteUsers || remoteUsers.length === 0) return",
    "'SITE-001'",
    "'SiteSense@2026'"
  )
  foreach ($token in $bad) {
    if ($verify.Contains($token)) { throw "Verification failed; unwanted token remains: $token" }
  }
  if (-not $verify.Contains("setInspections(mapped)")) { throw "Inspection replacement was not applied." }
  if (-not $verify.Contains("setUsers(mappedUsers)")) { throw "User replacement was not applied." }

  Write-Host "Phase 1B applied: dashboard collections start empty and successful API responses replace state."
  Write-Host "Backup: $backupDir"
}
catch {
  Copy-Item -LiteralPath (Join-Path $backupDir "App.tsx") -Destination $target -Force
  throw "Patch failed. Original App.tsx restored. Backup: $backupDir. Details: $($_.Exception.Message)"
}
