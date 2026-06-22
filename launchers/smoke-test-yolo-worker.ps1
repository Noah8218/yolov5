param(
    [string]$ImagePath = "",
    [string]$ImageRoot = "",
    [string]$WeightsPath = "",
    [string]$Device = "",
    [string]$Confidence = "0.25",
    [switch]$InstallRequirements,
    [switch]$NoInstallPrompt,
    [switch]$SkipEnvironmentCheck
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
$clientScript = Join-Path $projectRoot "labeling_tcp_client.py"
$modelRoot = Join-Path $projectRoot "yolov5Master"
$ensureEnvironmentScript = Join-Path $PSScriptRoot "ensure-yolo-environment.ps1"

function Find-FirstImage {
    param([string]$RootPath)

    if ([string]::IsNullOrWhiteSpace($RootPath) -or -not (Test-Path -LiteralPath $RootPath -PathType Container)) {
        return ""
    }

    $image = Get-ChildItem -LiteralPath $RootPath -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Extension -match '^\.(bmp|jpg|jpeg|png)$' } |
        Sort-Object Name |
        Select-Object -First 1

    if ($null -eq $image) {
        return ""
    }

    return $image.FullName
}

function Resolve-SmokeTestImage {
    if (-not [string]::IsNullOrWhiteSpace($ImagePath)) {
        return $ImagePath
    }

    $candidateRoots = @()
    if (-not [string]::IsNullOrWhiteSpace($ImageRoot)) {
        $candidateRoots += $ImageRoot
    }

    $candidateRoots += @(
        (Join-Path $projectRoot "data\train\images"),
        (Join-Path $projectRoot "data\valid\images"),
        (Join-Path $projectRoot "data\images"),
        "C:\Git\py\data\train\images",
        "C:\Git\py\KtemData"
    )

    foreach ($candidateRoot in $candidateRoots) {
        $candidateImage = Find-FirstImage $candidateRoot
        if (-not [string]::IsNullOrWhiteSpace($candidateImage)) {
            return $candidateImage
        }
    }

    return ""
}

if ([string]::IsNullOrWhiteSpace($WeightsPath)) {
    $WeightsPath = Join-Path $projectRoot "best.pt"
}

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

$ImagePath = Resolve-SmokeTestImage

if (-not (Test-Path -LiteralPath $ImagePath -PathType Leaf)) {
    throw "Image file not found. Pass -ImagePath or place images under C:\Git\py\data\train\images."
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
