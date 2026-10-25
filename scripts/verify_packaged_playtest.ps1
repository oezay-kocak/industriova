param([string]$AppDirectory = 'dist\playtest\dev3\Industriova')
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$app = (Resolve-Path -LiteralPath (Join-Path $root $AppDirectory)).Path
$exe = Join-Path $app 'Industriova.exe'
$destination = Join-Path $root ('artifacts\industriova-stabilization\packaged-smoke-' + (Get-Date -Format 'yyyyMMddTHHmmss'))
New-Item -ItemType Directory -Path $destination | Out-Null
$previousAppData = $env:LOCALAPPDATA
$previousQt = $env:QT_QPA_PLATFORM
$env:LOCALAPPDATA = $destination
$env:QT_QPA_PLATFORM = 'windows'
# A normal native window receives WM_CLOSE; never terminate the application
# to manufacture a successful orderly-close result.
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class PlaytestWindowClose {
    public delegate bool EnumProc(IntPtr hwnd, IntPtr parameter);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc callback, IntPtr parameter);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hwnd, out uint process);
    [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr hwnd, uint message, IntPtr wParam, IntPtr lParam);
    [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hwnd, System.Text.StringBuilder text, int count);
    public static int Close(int pid) {
        int count = 0;
        EnumWindows((hwnd, p) => {
            uint owner;
            GetWindowThreadProcessId(hwnd, out owner);
            var title = new System.Text.StringBuilder(256);
            GetWindowText(hwnd, title, 256);
            if (owner == pid && title.ToString() == "Industriova") {
                if (PostMessage(hwnd, 0x0010, IntPtr.Zero, IntPtr.Zero)) count++;
            }
            return true;
        }, IntPtr.Zero);
        return count;
    }
}
'@
$runs = @()
try {
    foreach ($number in 1..3) {
        $process = Start-Process -FilePath $exe -WorkingDirectory $app -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $destination "stdout-$number.txt") -RedirectStandardError (Join-Path $destination "stderr-$number.txt")
        # Retain the native handle before exit (Windows PowerShell 5.1 can
        # otherwise lose ExitCode when Start-Process children exit quickly).
        $null = $process.Handle
        $sent = 0
        $deadline = [DateTime]::UtcNow.AddSeconds(30)
        while (-not $process.HasExited -and [DateTime]::UtcNow -lt $deadline) {
            Start-Sleep -Milliseconds 250
            $process.Refresh()
            if ($process.MainWindowHandle -ne [IntPtr]::Zero) {
                # Let first layout, load and the normal event loop settle.
                Start-Sleep -Seconds 2
                $sent = [PlaytestWindowClose]::Close($process.Id)
                if ($sent -gt 0) { break }
            }
        }
        if ($sent -eq 0 -and -not $process.HasExited) { $sent = [PlaytestWindowClose]::Close($process.Id) }
        $closed = $process.WaitForExit(30000)
        if (-not $closed) { throw "Packaged application did not close normally: PID $($process.Id)." }
        $exitCode = $process.ExitCode
        $snapshotJson = & (Join-Path $root '.venv\Scripts\python.exe') (Join-Path $PSScriptRoot 'inspect_playtest_save.py') (Join-Path $destination 'Industriova\saves\company.sqlite')
        if ($LASTEXITCODE -ne 0) { throw 'Packaged save inspection failed.' }
        $snapshot = $snapshotJson | ConvertFrom-Json
        $entry = [ordered]@{ launch=$number; process_id=$process.Id; close_messages=$sent; exit_code=$exitCode; orderly_close=($sent -gt 0 -and $exitCode -eq 0); save=$snapshot }
        $runs += $entry
        $runs | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $destination 'progress.json') -Encoding utf8
        if (-not $entry.orderly_close) { throw "Packaged application startup/close failed on launch $number." }
        if ($number -gt 1 -and $snapshot.tick -le $runs[$number - 2].save.tick) { throw 'Packaged application did not resume saved simulation progress.' }
    }
    [ordered]@{ exe=$exe; isolated_appdata=$destination; launches=$runs; mode='Native Windows Qt application; WM_CLOSE; automated startup and save/reload, no manual gameplay acceptance' } | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $destination 'results.json') -Encoding utf8
    Write-Output (Join-Path $destination 'results.json')
}
finally {
    $env:LOCALAPPDATA = $previousAppData
    $env:QT_QPA_PLATFORM = $previousQt
}
