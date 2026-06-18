param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 5000,
    [string]$Confidence = "0.25",
    [string]$Device = "",
    [string]$WeightsPath = "",
    [string]$ModelRoot = "",
    [string]$ImageRoot = "C:\Git\py\KtemData",
    [switch]$Preload
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
$clientScript = Join-Path $projectRoot "labeling_tcp_client.py"

if ([string]::IsNullOrWhiteSpace($WeightsPath)) {
    $WeightsPath = Join-Path $projectRoot "best.pt"
}

if ([string]::IsNullOrWhiteSpace($ModelRoot)) {
    $ModelRoot = Join-Path $projectRoot "yolov5Master"
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

if (-not (Test-Path -LiteralPath $ModelRoot -PathType Container)) {
    throw "YOLO model root not found: $ModelRoot"
}

if (-not (Test-Path -LiteralPath $ImageRoot -PathType Container)) {
    Write-Warning "Image root not found: $ImageRoot. Absolute image paths in DetectImage requests will still work."
}

$arguments = @(
    $clientScript,
    "--host", $HostAddress,
    "--port", $Port,
    "--weights", $WeightsPath,
    "--model-root", $ModelRoot,
    "--image-root", $ImageRoot,
    "--conf", $Confidence,
    "--retry"
)

if (-not [string]::IsNullOrWhiteSpace($Device)) {
    $arguments += @("--device", $Device)
}

if ($Preload) {
    $arguments += "--preload"
}

& $pythonExe @arguments
