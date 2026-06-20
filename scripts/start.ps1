<#
  Sobe os servicos de desenvolvimento do White Tree Nexus, cada um em sua propria janela:
    - Backend  (FastAPI/uvicorn)  -> http://localhost:8000   (Swagger em /docs)
    - Frontend (Angular/ng serve) -> http://localhost:4200

  Uso (a partir da raiz do projeto):
    powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1
#>
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent

if (-not (Test-Path (Join-Path $root '.env'))) {
  Write-Warning ".env nao encontrado em $root - o backend cai no SQLite em memoria (sem persistencia)."
}
if (-not (Test-Path (Join-Path $root '.venv\Scripts\python.exe'))) {
  throw "venv nao encontrado em $root\.venv. Crie o ambiente e instale as dependencias antes."
}

# O `$env e escapado de proposito: deve ser avaliado na NOVA janela, nao nesta.
$backend  = "Set-Location '$root'; `$env:PYTHONIOENCODING='utf-8'; & '.\.venv\Scripts\python.exe' -m uvicorn wtnapp.main:app --reload --port 8000"
$frontend = "Set-Location '$root\wtnadmin'; npm start"

Start-Process powershell -ArgumentList '-NoExit', '-Command', $backend
Start-Process powershell -ArgumentList '-NoExit', '-Command', $frontend

Write-Host ''
Write-Host 'Servicos iniciados em janelas separadas:' -ForegroundColor Green
Write-Host '  Backend  -> http://localhost:8000  (Swagger: http://localhost:8000/docs)'
Write-Host '  Frontend -> http://localhost:4200'
Write-Host ''
Write-Host 'Primeiro uso - crie o Super Admin:' -ForegroundColor Yellow
Write-Host '  .\.venv\Scripts\python.exe scripts\seed_super_admin.py'
