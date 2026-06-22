param(
    [string]$ProjectRoot = "",
    [string]$PythonExe = "",
    [switch]$InstallIfMissing,
    [switch]$PromptInstall,
    [switch]$SkipPackageCheck,
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = Split-Path -Parent $PSScriptRoot
}

$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$venvRoot = Join-Path $ProjectRoot ".venv"
$venvPython = Join-Path $venvRoot "Scripts\python.exe"
$requirementsPath = Join-Path $ProjectRoot "requirements.txt"

function Write-Step([string]$Message) {
    if (-not $Quiet) {
        Write-Host "[yolo-env] $Message"
    }
}

function Exit-WithError([int]$Code, [string]$Message) {
    Write-Error $Message
    exit $Code
}

function Normalize-PackageName([string]$Name) {
    if ([string]::IsNullOrWhiteSpace($Name)) {
        return ""
    }

    return $Name.Trim().Replace("_", "-").ToLowerInvariant()
}

function Get-PythonCommand {
    if (-not [string]::IsNullOrWhiteSpace($PythonExe)) {
        if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
            Exit-WithError 10 "Configured Python executable was not found: $PythonExe"
        }

        return @($PythonExe)
    }

    $pyLauncher = Join-Path $env:WINDIR "py.exe"
    if (Test-Path -LiteralPath $pyLauncher -PathType Leaf) {
        return @($pyLauncher, "-3")
    }

    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($null -ne $pythonCommand) {
        return @($pythonCommand.Source)
    }

    return @()
}

function Invoke-PythonCommand([string[]]$Command, [string[]]$Arguments) {
    if ($Command.Count -eq 0) {
        Exit-WithError 10 "Python was not found. Install Python 3.10+ or pass -PythonExe."
    }

    $exe = $Command[0]
    $prefix = @()
    if ($Command.Count -gt 1) {
        $prefix = $Command[1..($Command.Count - 1)]
    }

    $allArguments = @($prefix) + @($Arguments)
    & $exe @allArguments
    return $LASTEXITCODE
}

function Confirm-Install([string]$Reason) {
    if ($InstallIfMissing) {
        return $true
    }

    if (-not $PromptInstall) {
        return $false
    }

    Write-Warning $Reason
    $answer = Read-Host "Install now? [Y/N]"
    return $answer -match "^(y|yes)$"
}

function Get-RequirementPackageNames([string]$Path, [System.Collections.Generic.HashSet[string]]$Visited) {
    $packages = New-Object System.Collections.Generic.List[string]
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        Exit-WithError 11 "requirements.txt was not found: $Path"
    }

    $fullPath = (Resolve-Path -LiteralPath $Path).Path
    if (-not $Visited.Add($fullPath)) {
        return $packages
    }

    $baseDirectory = Split-Path -Parent $fullPath
    foreach ($rawLine in Get-Content -LiteralPath $fullPath) {
        $line = ($rawLine -replace "\s+#.*$", "").Trim()
        if ([string]::IsNullOrWhiteSpace($line) -or $line.StartsWith("#")) {
            continue
        }

        if ($line -match "^(-r|--requirement)\s+(.+)$") {
            $includePath = $Matches[2].Trim(" `t`"")
            if (-not [System.IO.Path]::IsPathRooted($includePath)) {
                $includePath = Join-Path $baseDirectory $includePath
            }

            foreach ($nestedPackage in Get-RequirementPackageNames $includePath $Visited) {
                $packages.Add($nestedPackage)
            }

            continue
        }

        if ($line.StartsWith("-")) {
            continue
        }

        if ($line -match "[#&]egg=([A-Za-z0-9_.-]+)") {
            $packages.Add($Matches[1])
            continue
        }

        $line = $line.Split(";")[0].Trim()
        if ($line -match "^([A-Za-z0-9_.-]+)(?:\[[^\]]+\])?") {
            $packages.Add($Matches[1])
        }
    }

    return $packages
}

function Get-MissingPackages([string]$PythonPath) {
    $requiredPackages = New-Object System.Collections.Generic.HashSet[string]([System.StringComparer]::OrdinalIgnoreCase)
    $visited = New-Object System.Collections.Generic.HashSet[string]([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($packageName in Get-RequirementPackageNames $requirementsPath $visited) {
        $normalizedName = Normalize-PackageName $packageName
        if (-not [string]::IsNullOrWhiteSpace($normalizedName)) {
            [void]$requiredPackages.Add($normalizedName)
        }
    }

    if ($requiredPackages.Count -eq 0) {
        Exit-WithError 11 "No package names were found in requirements.txt: $requirementsPath"
    }

    $pipJson = & $PythonPath -m pip list --format=json
    if ($LASTEXITCODE -ne 0) {
        Exit-WithError 16 "Could not inspect installed Python packages with pip list."
    }

    $installedPackages = New-Object System.Collections.Generic.HashSet[string]([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($packageInfo in ($pipJson | ConvertFrom-Json)) {
        $normalizedName = Normalize-PackageName $packageInfo.name
        if (-not [string]::IsNullOrWhiteSpace($normalizedName)) {
            [void]$installedPackages.Add($normalizedName)
        }
    }

    $missingPackages = New-Object System.Collections.Generic.List[string]
    foreach ($packageName in $requiredPackages) {
        if (-not $installedPackages.Contains($packageName)) {
            $missingPackages.Add($packageName)
        }
    }

    return $missingPackages | Sort-Object
}

function Install-Requirements([string]$PythonPath) {
    Write-Step "Installing requirements from $requirementsPath"
    & $PythonPath -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) {
        Exit-WithError 15 "pip upgrade failed."
    }

    & $PythonPath -m pip install -r $requirementsPath
    if ($LASTEXITCODE -ne 0) {
        Exit-WithError 15 "requirements installation failed."
    }
}

if (-not (Test-Path -LiteralPath $requirementsPath -PathType Leaf)) {
    Exit-WithError 11 "requirements.txt was not found: $requirementsPath"
}

if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
    $reason = "Python virtual environment was not found: $venvPython"
    if (-not (Confirm-Install $reason)) {
        Write-Warning $reason
        Write-Host "Run this command to create it:"
        Write-Host "powershell -NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" -InstallIfMissing"
        exit 12
    }

    $pythonCommand = @(Get-PythonCommand)
    Write-Step "Creating virtual environment at $venvRoot"
    $exitCode = Invoke-PythonCommand -Command $pythonCommand -Arguments @("-m", "venv", $venvRoot)
    if ($exitCode -ne 0) {
        Exit-WithError 13 "Virtual environment creation failed."
    }
}

if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
    Exit-WithError 13 "Virtual environment Python executable was not created: $venvPython"
}

if (-not $SkipPackageCheck) {
    $missingPackages = @(Get-MissingPackages $venvPython)
    if ($missingPackages.Count -gt 0) {
        $preview = ($missingPackages | Select-Object -First 12) -join ", "
        if ($missingPackages.Count -gt 12) {
            $preview = "$preview, ..."
        }

        $reason = "Missing Python packages: $preview"
        if (-not (Confirm-Install $reason)) {
            Write-Warning $reason
            Write-Host "Run this command to install them:"
            Write-Host "powershell -NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" -InstallIfMissing"
            exit 14
        }

        Install-Requirements $venvPython
    }
}

& $venvPython -m pip check
if ($LASTEXITCODE -ne 0) {
    Write-Warning "pip check reported dependency conflicts. The worker may still start, but inference can fail."
}

Write-Step "Python environment is ready: $venvPython"
exit 0
