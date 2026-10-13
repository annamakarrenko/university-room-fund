param(
    [Parameter(Mandatory = $true)]
    [string]$BackupFile,

    [string]$Database = "university_fund_migration_test",
    [string]$User = "postgres",
    [string]$HostName = "localhost"
)

$pgRestore = "C:\Program Files\PostgreSQL\17\bin\pg_restore.exe"

if (-not (Test-Path $BackupFile)) {
    throw "Backup file not found: $BackupFile"
}

& $pgRestore `
    -U $User `
    -h $HostName `
    -d $Database `
    --clean `
    --if-exists `
    $BackupFile

if ($LASTEXITCODE -ne 0) {
    throw "Restore failed"
}

Write-Host "Restore completed."