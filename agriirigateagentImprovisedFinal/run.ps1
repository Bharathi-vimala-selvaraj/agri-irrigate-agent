$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Starting backend..." -ForegroundColor Cyan
Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000" -WorkingDirectory "$root/backend" -WindowStyle Normal

Write-Host "Starting frontend..." -ForegroundColor Cyan
Start-Process -FilePath "npm" -ArgumentList "run", "dev" -WorkingDirectory "$root/frontend" -WindowStyle Normal

Write-Host "Both services are starting. Open http://localhost:3000" -ForegroundColor Green
