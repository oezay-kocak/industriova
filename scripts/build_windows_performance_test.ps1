param([string]$Python = '.\.venv\Scripts\python.exe')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$distDir = Join-Path $projectRoot 'dist\performance-test-20261025'
$workDir = Join-Path $projectRoot 'build\performance-test-20261025'
if (Test-Path -LiteralPath $distDir) { throw 'Performance test output already exists; preserve it.' }
$cacheDir = [System.IO.Path]::GetFullPath((Join-Path $workDir 'cache'))
if (-not $cacheDir.StartsWith($projectRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) { throw 'Build cache escaped the workspace.' }
$env:PYINSTALLER_CONFIG_DIR = $cacheDir
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:INDUSTRIOVA_PERFORMANCE_BUILD_METADATA = Join-Path $workDir 'metadata\performance_build.json'
& $Python -B scripts/performance_build_metadata.py $env:INDUSTRIOVA_PERFORMANCE_BUILD_METADATA
if ($LASTEXITCODE -ne 0) { throw 'Build metadata failed.' }
& $Python -B -m PyInstaller --noconfirm --clean --distpath $distDir --workpath $workDir 'Industriova_Performance_Test.spec'
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed ($LASTEXITCODE)." }
$exe = Join-Path $distDir 'Industriova_Performance_Test\Industriova_Performance_Test.exe'
if (-not (Test-Path -LiteralPath $exe)) { throw 'Expected test executable missing.' }
Write-Host "Build: $exe"
