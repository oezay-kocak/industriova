param(
    [string]$Python = ".\.venv\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$distDir = Join-Path $projectRoot "dist\playtest\dev6"
$buildDir = Join-Path $projectRoot "build\playtest-dev6"
$appDir = Join-Path $distDir "Industriova"
$zipPath = Join-Path $projectRoot "dist\playtest\Industriova-0.2.0-dev6-Windows-Playtest.zip"
$specPath = Join-Path $projectRoot "Industriova.spec"

Set-Location $projectRoot
if ((Test-Path -LiteralPath $zipPath) -or (Test-Path -LiteralPath $appDir)) {
    throw "Dev6 output already exists. Preserve the existing build before rebuilding."
}

& $Python -m PyInstaller --noconfirm --clean --distpath $distDir --workpath $buildDir $specPath
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed ($LASTEXITCODE)."
}

if (-not (Test-Path (Join-Path $appDir "Industriova.exe"))) {
    throw "Industriova.exe was not created."
}

Copy-Item -LiteralPath (Join-Path $PSScriptRoot "playtest_LIESMICH.txt") -Destination (Join-Path $appDir "LIESMICH.txt")
Compress-Archive -Path $appDir -DestinationPath $zipPath -CompressionLevel Optimal

Write-Host "Build: $appDir"
Write-Host "ZIP:   $zipPath"
