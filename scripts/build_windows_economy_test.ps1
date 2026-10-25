param([string]$Python = '.\.venv\Scripts\python.exe')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$distDir = Join-Path $projectRoot 'dist\economy-rebalance-test'
$workDir = Join-Path $projectRoot 'build\economy-rebalance-test'
if (Test-Path -LiteralPath $distDir) { throw 'Economy test output already exists; preserve it.' }
$cacheDir = [System.IO.Path]::GetFullPath((Join-Path $workDir 'cache'))
if (-not $cacheDir.StartsWith($projectRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) { throw 'Build cache escaped the workspace.' }
$env:PYINSTALLER_CONFIG_DIR = $cacheDir
$env:PYTHONDONTWRITEBYTECODE = '1'
& $Python -B -m PyInstaller --noconfirm --clean --distpath $distDir --workpath $workDir 'Industriova_Economy_Rebalance_Test.spec'
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed ($LASTEXITCODE)." }
$exe = Join-Path $distDir 'Industriova_0.3_Economy_Rebalance_Test\Industriova_0.3_Economy_Rebalance_Test.exe'
if (-not (Test-Path -LiteralPath $exe)) { throw 'Expected test executable missing.' }
Write-Host "Build: $exe"
