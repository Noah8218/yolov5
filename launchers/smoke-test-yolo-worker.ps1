param(
    [Parameter(Mandatory = $true)]
    [string]$ImagePath,
    [string]$WeightsPath = "",
    [string]$Device = "",
    [string]$Confidence = "0.25"
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
$clientScript = Join-Path $projectRoot "labeling_tcp_client.py"
$modelRoot = Join-Path $projectRoot "yolov5Master"

if ([string]::IsNullOrWhiteSpace($WeightsPath)) {
    $WeightsPath = Join-Path $projectRoot "best.pt"
}

if (-not (Test-Path -LiteralPath $pythonExe -PathType Leaf)) {
    throw "Python executable not found: $pythonExe"
}

if (-not (Test-Path -LiteralPath $clientScript -PathType Leaf)) {
    throw "TCP client script not found: $clientScript"
}

if (-not (Test-Path -LiteralPath $WeightsPath -PathType Leaf)) {
    throw "YOLO weights not found: $WeightsPath"
}

if (-not (Test-Path -LiteralPath $ImagePath -PathType Leaf)) {
    throw "Image file not found: $ImagePath"
}

$arguments = @(
    $clientScript,
    "--smoke-test",
    "--weights", $WeightsPath,
    "--model-root", $modelRoot,
    "--image", $ImagePath,
    "--conf", $Confidence
)

if (-not [string]::IsNullOrWhiteSpace($Device)) {
    $arguments += @("--device", $Device)
}

& $pythonExe @arguments
