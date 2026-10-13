if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

if (Test-Path "requirements-dev.txt") {
    .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
}

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host ".env created. Configure DATABASE_URL and SESSION_SECRET."
}

Write-Host "Project setup completed."