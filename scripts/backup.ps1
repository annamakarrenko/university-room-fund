param(
    [string]$Database = "university_fund_migration_test",
    [string]$User = "postgres",
    [string]$HostName = "localhost"
)

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

$backupDir = Join-Path $PSScriptRoot "..\backups"

New-Item -ItemType Directory -Force $backupDir | Out-Null

$backupFile = Join-Path `
    $backupDir `
    "${Database}_${timestamp}.dump"

$pgDump = "C:\Program Files\PostgreSQL\17\bin\pg_dump.exe"

& $pgDump `
    -U $User `
    -h $HostName `
    -Fc `
    -f $backupFile `
    $Database

if ($LASTEXITCODE -ne 0) {
    throw "Backup failed"
}

Write-Host "Backup created:"
Write-Host $backupFile