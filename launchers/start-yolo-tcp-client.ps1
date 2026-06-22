param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 5000,
    [string]$Confidence = "0.25",
    [string]$Device = "",
    [string]$WeightsPath = "",
    [string]$ModelRoot = "",
    [string]$ImageRoot = "",
    [int]$ImageSize = 320,
    [switch]$Preload,
    [switch]$InstallRequirements,
    [switch]$NoInstallPrompt,
    [switch]$SkipEnvironmentCheck
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
$clientScript = Join-Path $projectRoot "labeling_tcp_client.py"
$ensureEnvironmentScript = Join-Path $PSScriptRoot "ensure-yolo-environment.ps1"

function Resolve-ImageRoot {
    param([string]$ConfiguredImageRoot)

    if (-not [string]::IsNullOrWhiteSpace($ConfiguredImageRoot)) {
        return $ConfiguredImageRoot
    }

    foreach ($candidate in @(
        (Join-Path $projectRoot "data\train\images"),
        (Join-Path $projectRoot "data\valid\images"),
        (Join-Path $projectRoot "data\images"),
        "C:\Git\py\data\train\images",
        "C:\Git\py\KtemData"
    )) {
        if (Test-Path -LiteralPath $candidate -PathType Container) {
            return $candidate
        }
    }

    return "C:\Git\py\KtemData"
}

if ([string]::IsNullOrWhiteSpace($WeightsPath)) {
    $WeightsPath = Join-Path $projectRoot "best.pt"
}

if ([string]::IsNullOrWhiteSpace($ModelRoot)) {
    $ModelRoot = Join-Path $projectRoot "yolov5Master"
}

$ImageRoot = Resolve-ImageRoot $ImageRoot

if (-not $SkipEnvironmentCheck) {
    if (-not (Test-Path -LiteralPath $ensureEnvironmentScript -PathType Leaf)) {
        throw "Environment setup script not found: $ensureEnvironmentScript"
    }

    $ensureArguments = @{
        ProjectRoot = $projectRoot
    }
    if ($InstallRequirements) {
        $ensureArguments.InstallIfMissing = $true
    }
    elseif (-not $NoInstallPrompt) {
        $ensureArguments.PromptInstall = $true
    }

    & $ensureEnvironmentScript @ensureArguments
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
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
    "--img-size", $ImageSize,
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
