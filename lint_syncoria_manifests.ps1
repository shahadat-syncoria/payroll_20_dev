$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

$env:PYTHONPATH = "."

$files = Get-ChildItem -Recurse -Filter __manifest__.py |
    Where-Object { $_.Directory.Name -like "syncoria*" } |
    Select-Object -ExpandProperty FullName

if (-not $files -or $files.Count -eq 0) {
    Write-Host "No syncoria* module manifests found." -ForegroundColor Yellow
    exit 0
}

Write-Host "Linting these manifest files:" -ForegroundColor Cyan
$files | ForEach-Object { Write-Host " - $_" }

python -m pylint --rcfile=.pylintrc --score=n $files
exit $LASTEXITCODE