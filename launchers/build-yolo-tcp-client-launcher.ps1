$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$launcherProject = Join-Path $projectRoot "tools\YoloTcpClientLauncher\YoloTcpClientLauncher.csproj"
$publishRoot = Join-Path $projectRoot "dist\YoloTcpClientLauncher"

if (-not (Test-Path -LiteralPath $launcherProject -PathType Leaf)) {
    throw "Launcher project not found: $launcherProject"
}

dotnet publish $launcherProject `
    -c Release `
    -r win-x64 `
    --self-contained false `
    -p:PublishSingleFile=true `
    -p:DebugType=None `
    -p:DebugSymbols=false `
    -o $publishRoot

Write-Host "Launcher published:"
Write-Host (Join-Path $publishRoot "YoloTcpClientLauncher.exe")
