# =============================================================================
# MONITOR - Real-time trading system monitoring (PowerShell)
# =============================================================================

# Configuración
$ErrorActionPreference = "SilentlyContinue"

# Colores
function Write-ColorOutput($ForegroundColor, $Text) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    Write-Output $Text
    $host.UI.RawUI.ForegroundColor = $fc
}

while ($true) {
    Clear-Host

    Write-ColorOutput Blue "=========================================================================="
    Write-ColorOutput Blue "  INSTITUTIONAL TRADING SYSTEM - LIVE MONITOR"
    Write-ColorOutput Blue "=========================================================================="
    Write-Output ""

    # Show latest log entries
    Write-ColorOutput Yellow "📊 LATEST ACTIVITY:"

    $dateStr = Get-Date -Format "yyyyMMdd"
    $logFile = "logs\trading_$dateStr.log"

    if (Test-Path $logFile) {
        Get-Content $logFile -Tail 20 | Select-String -Pattern "(SIGNAL|TRADE|ERROR|WARNING)" | ForEach-Object {
            Write-Output $_.Line
        }
    } else {
        Write-Output "No recent activity (log file not found)"
    }

    Write-Output ""
    Write-ColorOutput Yellow "💰 SYSTEM STATUS:"

    # Check if engine is running
    $engineProcess = Get-Process -Name python -ErrorAction SilentlyContinue |
                     Where-Object {$_.CommandLine -like "*live_trading_engine*"}

    if ($engineProcess) {
        Write-ColorOutput Green "✅ Trading engine: RUNNING (PID: $($engineProcess.Id))"
    } else {
        Write-ColorOutput Red "❌ Trading engine: STOPPED"
    }

    # Check database (PostgreSQL)
    $pgService = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($pgService -and $pgService.Status -eq "Running") {
        Write-ColorOutput Green "✅ Database: ONLINE"
    } else {
        Write-ColorOutput Red "❌ Database: OFFLINE"
    }

    # Memory usage
    $os = Get-WmiObject Win32_OperatingSystem
    $totalMemMB = [math]::Round($os.TotalVisibleMemorySize / 1KB)
    $freeMemMB = [math]::Round($os.FreePhysicalMemory / 1KB)
    $usedMemMB = $totalMemMB - $freeMemMB
    $memPercent = [math]::Round(($usedMemMB / $totalMemMB) * 100)

    Write-ColorOutput Blue "💾 Memory usage: $memPercent% ($usedMemMB MB / $totalMemMB MB)"

    # Disk space
    $disk = Get-WmiObject Win32_LogicalDisk -Filter "DeviceID='C:'" | Select-Object Size,FreeSpace
    $diskUsedGB = [math]::Round(($disk.Size - $disk.FreeSpace) / 1GB, 2)
    $diskTotalGB = [math]::Round($disk.Size / 1GB, 2)
    $diskPercent = [math]::Round((($disk.Size - $disk.FreeSpace) / $disk.Size) * 100)

    Write-ColorOutput Blue "💿 Disk usage: $diskPercent% ($diskUsedGB GB / $diskTotalGB GB)"

    Write-Output ""
    Write-ColorOutput Yellow "Press Ctrl+C to exit"
    Write-Output ""

    Start-Sleep -Seconds 5
}
