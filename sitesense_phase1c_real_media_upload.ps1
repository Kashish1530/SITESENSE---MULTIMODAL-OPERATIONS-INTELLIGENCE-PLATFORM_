$ErrorActionPreference = "Stop"

$projectRoot = (Get-Location).Path
$frontend = Join-Path $projectRoot "_integration_staging\gargi_backend\SITESENSE---MULTIMODAL-OPERATIONS-INTELLIGENCE-PLATFORM_-Gargi_backend\frontend"
$target = Join-Path $frontend "src\App.tsx"

if (-not (Test-Path -LiteralPath $target)) { throw "App.tsx not found: $target" }
$content = (Get-Content -LiteralPath $target -Raw) -replace "`r`n", "`n"

$adapterImport = @'
import {
  createTaskPhotoFormData,
  mockTaskPhotoUpload,
  formatFileSize,
} from './inspections/taskPhotoAdapter'
'@
if (-not $content.Contains($adapterImport)) { throw "Expected taskPhotoAdapter import not found. No changes made." }
if (-not $content.Contains("let uploadSuccessful = false")) { throw "Expected upload fallback block not found. No changes made." }
if (-not $content.Contains("const uploadedAt = new Date().toISOString()")) { throw "Expected local task-completion block not found. No changes made." }

$backupDir = Join-Path $projectRoot ("_integration_backups\real_media_upload_phase1c_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
Copy-Item -LiteralPath $target -Destination (Join-Path $backupDir "App.tsx") -Force

try {
  # harsh changes starts
  $content = $content.Replace($adapterImport, "// harsh changes starts`n// Removed local mock media-upload adapter; inspection media must be persisted by the backend.`n// harsh changes end")

  $uploadReplacement = @'
      // harsh changes starts
      const isUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(task.id)
      if (!isUuid || !getStoredAccessToken()) {
        console.warn('A persisted inspection and authenticated session are required for media upload.')
        return false
      }

      const uploadResult = await batchUploadMediaApi(task.id, files, onProgress)
      if (
        uploadResult?.total_uploaded !== files.length ||
        (Array.isArray(uploadResult?.errors) && uploadResult.errors.length > 0)
      ) {
        console.warn('Backend did not confirm that every selected media file was uploaded.', uploadResult)
        return false
      }
      // harsh changes end
'@
  $pattern = '(?s)      let uploadSuccessful = false.*?      const latestTask = inspectionsRef\.current\.find\('
  $replacement = $uploadReplacement + "`n      const latestTask = inspectionsRef.current.find("
  $content = [regex]::Replace($content, $pattern, $replacement, 1)
  if ($content -match 'mockTaskPhotoUpload|createTaskPhotoFormData') { throw "Mock upload references remain after replacement." }
  $content = [regex]::Replace($content, '(?s)\nfunction createEvidenceId\(\) \{.*?\n\}\n', "`n", 1)

  $completionReplacement = @'
      // harsh changes starts
      // Media upload is not an inspection completion or review decision.
      // Keep inspection status unchanged until a dedicated backend submission workflow exists.
      return true
      // harsh changes end
'@
  $content = [regex]::Replace(
    $content,
    '(?s)      const uploadedAt = new Date\(\)\.toISOString\(\).*?      return true(?=\s*\r?\n    \} catch)',
    $completionReplacement,
    1
  )
  # harsh changes end

  if ($content -match 'const uploadedAt = new Date\(\)\.toISOString\(\)|mockTaskPhotoUpload|createTaskPhotoFormData') {
    throw "Verification failed: mock evidence or local completion logic remains in App.tsx."
  }
  if ($content -notmatch 'uploadResult\?\.total_uploaded !== files\.length') {
    throw "Verification failed: backend upload response validation was not inserted."
  }
  Set-Content -LiteralPath $target -Value $content -Encoding utf8
  Write-Host "Phase 1C applied: task photo upload now requires backend confirmation; no mock fallback or local completion."
  Write-Host "Backup: $backupDir"
}
catch {
  Copy-Item -LiteralPath (Join-Path $backupDir "App.tsx") -Destination $target -Force
  throw "Patch failed. Original App.tsx restored. Backup: $backupDir. Details: $($_.Exception.Message)"
}
