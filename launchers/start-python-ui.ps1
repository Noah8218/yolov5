$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
$program = Join-Path $projectRoot "Program.py"

if (-not (Test-Path -LiteralPath $pythonExe -PathType Leaf)) {
    throw "Python executable not found: $pythonExe"
}

if (-not (Test-Path -LiteralPath $program -PathType Leaf)) {
    throw "Python UI program not found: $program"
}

Push-Location $projectRoot
try {
    & $pythonExe $program
}
finally {
    Pop-Location
}
