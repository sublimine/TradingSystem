<#
.SYNOPSIS
    Sistema de Correcci?n Institucional de Imports - Trading System
.DESCRIPTION
    Sistema robusto de correcci?n con validaci?n exhaustiva, backups verificados,
    an?lisis sint?ctico Python AST, y reportes cuantitativos completos.
.PARAMETER DryRun
    Ejecuta en modo simulaci?n sin aplicar cambios permanentes
.PARAMETER SkipBackup
    Omite la creaci?n de backups (no recomendado en producci?n)
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [switch]$DryRun,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipBackup
)

$ErrorActionPreference = "Stop"
$PROJECT_ROOT = "C:\TradingSystem"
$STRATEGIES_DIR = Join-Path $PROJECT_ROOT "src\strategies"
$BACKUP_DIR = Join-Path $PROJECT_ROOT "backups\import_correction"
$LOG_DIR = Join-Path $PROJECT_ROOT "logs"
$REPORT_DIR = Join-Path $PROJECT_ROOT "reports"
$TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"
$LOG_FILE = Join-Path $LOG_DIR "import_correction_$TIMESTAMP.log"
$MANIFEST_FILE = Join-Path $BACKUP_DIR "correction_manifest_$TIMESTAMP.json"

$CORRECT_IMPORT = "from src.strategies.strategy_base import StrategyBase, Signal"

$PATTERNS = @{
    standalone_signal = '^\s*import\s+Signal\s*$'
    from_signal = 'from\s+Signal\s+import'
    models_signal = 'from\s+src\.models\s+import\s+Signal'
    incomplete_base = 'from\s+src\.strategies\.strategy_base\s+import\s+StrategyBase\s*$(?!.*Signal)'
}

class Logger {
    [string]$LogFile
    [string]$SessionId
    [System.Collections.ArrayList]$Entries
    
    Logger([string]$path) {
        $this.LogFile = $path
        $this.SessionId = [guid]::NewGuid().ToString().Substring(0,8)
        $this.Entries = [System.Collections.ArrayList]@()
        
        $dir = Split-Path $path -Parent
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
        
        $this.Log("INFO", "Session initialized: $($this.SessionId)")
    }
    
    [void]Log([string]$level, [string]$message) {
        $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff"
        $entry = @{
            Timestamp = $ts
            Level = $level
            Message = $message
        }
        [void]$this.Entries.Add($entry)
        
        $color = switch ($level) {
            "ERROR" { "Red" }
            "WARN" { "Yellow" }
            "SUCCESS" { "Green" }
            "INFO" { "Cyan" }
            default { "White" }
        }
        
        Write-Host "[$ts][$level] $message" -ForegroundColor $color
        Add-Content -Path $this.LogFile -Value "[$ts][$level] $message" -Encoding UTF8
    }
    
    [hashtable]Stats() {
        return @{
            Total = $this.Entries.Count
            Errors = @($this.Entries | Where-Object {$_.Level -eq "ERROR"}).Count
            Warnings = @($this.Entries | Where-Object {$_.Level -eq "WARN"}).Count
            Success = @($this.Entries | Where-Object {$_.Level -eq "SUCCESS"}).Count
        }
    }
}

function Test-Prerequisites {
    param([Logger]$log)
    
    $log.Log("INFO", "=== PHASE 1: VALIDATING PREREQUISITES ===")
    
    if (-not (Test-Path $PROJECT_ROOT)) {
        $log.Log("ERROR", "Project root not found: $PROJECT_ROOT")
        throw "Critical error: Project directory does not exist"
    }
    
    if (-not (Test-Path $STRATEGIES_DIR)) {
        $log.Log("ERROR", "Strategies directory not found: $STRATEGIES_DIR")
        throw "Critical error: Strategies directory does not exist"
    }
    
    $basePath = Join-Path $STRATEGIES_DIR "strategy_base.py"
    if (-not (Test-Path $basePath)) {
        $log.Log("ERROR", "strategy_base.py not found")
        throw "Critical error: Base strategy file missing"
    }
    
    try {
        $pyVer = & python --version 2>&1
        $log.Log("INFO", "Python detected: $pyVer")
    } catch {
        $log.Log("ERROR", "Python not available in PATH")
        throw "Critical error: Python executable not found"
    }
    
    $files = Get-ChildItem -Path $STRATEGIES_DIR -Filter "*.py" | Where-Object {
        $_.Name -ne "__init__.py" -and $_.Name -ne "strategy_base.py"
    }
    
    if ($files.Count -eq 0) {
        $log.Log("ERROR", "No strategy files found for processing")
        throw "Critical error: No strategy files available"
    }
    
    $log.Log("INFO", "Found $($files.Count) strategy files to process")
    foreach ($f in $files) {
        $log.Log("INFO", "  - $($f.Name) ($($f.Length) bytes)")
    }
    
    return $files
}

function New-Backup {
    param([array]$files, [Logger]$log)
    
    $log.Log("INFO", "=== PHASE 2: CREATING BACKUP ===")
    
    $backupPath = Join-Path $BACKUP_DIR $TIMESTAMP
    if (-not (Test-Path $backupPath)) {
        New-Item -ItemType Directory -Path $backupPath -Force | Out-Null
    }
    
    $manifest = @{
        Timestamp = $TIMESTAMP
        Path = $backupPath
        Files = @()
        Hashes = @{}
    }
    
    foreach ($file in $files) {
        $rel = $file.FullName.Replace("$PROJECT_ROOT\", "")
        $dest = Join-Path $backupPath $rel
        $destDir = Split-Path $dest -Parent
        
        if (-not (Test-Path $destDir)) {
            New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        }
        
        Copy-Item -Path $file.FullName -Destination $dest -Force
        $hash = (Get-FileHash -Path $file.FullName -Algorithm SHA256).Hash
        
        $manifest.Files += $rel
        $manifest.Hashes[$rel] = $hash
        
        $log.Log("INFO", "  Backed up: $($file.Name) [SHA256: $($hash.Substring(0,12))...]")
    }
    
    $manifest | ConvertTo-Json -Depth 10 | Out-File -FilePath $MANIFEST_FILE -Encoding UTF8
    
    $log.Log("SUCCESS", "Backup complete: $($manifest.Files.Count) files saved")
    $log.Log("INFO", "Manifest: $MANIFEST_FILE")
    
    return $manifest
}

function Test-PythonSyntax {
    param([string]$path)
    
    $pyCheck = @"
import sys, ast
try:
    with open(r'$path', 'r', encoding='utf-8') as f:
        ast.parse(f.read())
    print('VALID')
except SyntaxError as e:
    print(f'SYNTAX_ERROR:Line {e.lineno}:{e.msg}')
except Exception as e:
    print(f'ERROR:{e}')
"@
    
    $temp = [System.IO.Path]::GetTempFileName() + ".py"
    $pyCheck | Out-File -FilePath $temp -Encoding UTF8
    
    try {
        $result = & python $temp 2>&1 | Out-String
        Remove-Item $temp -Force
        return $result.Trim()
    } catch {
        Remove-Item $temp -Force -ErrorAction SilentlyContinue
        return "ERROR:Execution failed"
    }
}

function Repair-Import {
    param([System.IO.FileInfo]$file, [Logger]$log, [bool]$dry)
    
    $log.Log("INFO", "Processing: $($file.Name)")
    
    $content = Get-Content -Path $file.FullName -Raw -Encoding UTF8
    $original = $content
    $changes = @()
    
    $syntaxPre = Test-PythonSyntax -path $file.FullName
    if ($syntaxPre -notmatch "^VALID") {
        $log.Log("WARN", "  Pre-correction syntax issue: $syntaxPre")
    }
    
    foreach ($name in $PATTERNS.Keys) {
        $pattern = $PATTERNS[$name]
        if ($content -match $pattern) {
            $content = switch ($name) {
                "standalone_signal" { $content -replace $pattern, $CORRECT_IMPORT }
                "from_signal" { $content -replace 'from\s+Signal\s+import[^\n]*', $CORRECT_IMPORT }
                "models_signal" { $content -replace $pattern, $CORRECT_IMPORT }
                "incomplete_base" { 
                    if ($content -notmatch 'Signal') {
                        $content -replace $pattern, $CORRECT_IMPORT
                    } else {
                        $content
                    }
                }
            }
            $changes += $name
            $log.Log("INFO", "  Applied correction: $name")
        }
    }
    
    if ($content -eq $original) {
        if ($content -match [regex]::Escape($CORRECT_IMPORT)) {
            $log.Log("SUCCESS", "  Status: Already correct")
            return @{Status="AlreadyCorrect"; File=$file.Name; Changes=@()}
        } else {
            $log.Log("WARN", "  Status: Manual review required")
            return @{Status="ManualReview"; File=$file.Name; Changes=@()}
        }
    }
    
    if (-not $dry) {
        $content | Out-File -FilePath $file.FullName -Encoding UTF8 -NoNewline
        
        $syntaxPost = Test-PythonSyntax -path $file.FullName
        if ($syntaxPost -notmatch "^VALID") {
            $log.Log("ERROR", "  Post-correction syntax failed: $syntaxPost")
            $original | Out-File -FilePath $file.FullName -Encoding UTF8 -NoNewline
            return @{Status="SyntaxFailed"; File=$file.Name; Changes=$changes; Error=$syntaxPost}
        }
        
        $log.Log("SUCCESS", "  Status: Corrected and validated")
    } else {
        $log.Log("INFO", "  [DRY-RUN] Would apply $($changes.Count) corrections")
    }
    
    return @{Status="Corrected"; File=$file.Name; Changes=$changes}
}

function Test-Imports {
    param([array]$files, [Logger]$log)
    
    $log.Log("INFO", "=== PHASE 4: VALIDATING IMPORTS ===")
    
    $results = @{}
    
    foreach ($file in $files) {
        $name = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
        
        $pyTest = @"
import sys
sys.path.insert(0, r'$PROJECT_ROOT')
try:
    exec('from src.strategies.$name import *')
    print('SUCCESS')
except Exception as e:
    print(f'FAIL:{e}')
"@
        
        $temp = [System.IO.Path]::GetTempFileName() + ".py"
        $pyTest | Out-File -FilePath $temp -Encoding UTF8
        
        try {
            $result = & python $temp 2>&1 | Out-String
            Remove-Item $temp -Force
            
            if ($result -match "SUCCESS") {
                $log.Log("SUCCESS", "  Import OK: $name")
                $results[$name] = "SUCCESS"
            } else {
                $log.Log("ERROR", "  Import FAILED: $name")
                $log.Log("ERROR", "    $($result.Trim())")
                $results[$name] = $result.Trim()
            }
        } catch {
            Remove-Item $temp -Force -ErrorAction SilentlyContinue
            $log.Log("ERROR", "  Execution error: $name")
            $results[$name] = "EXECUTION_ERROR"
        }
    }
    
    return $results
}

function New-Report {
    param([array]$repairs, [hashtable]$validations, [hashtable]$backup, [Logger]$log)
    
    $log.Log("INFO", "=== PHASE 5: GENERATING REPORT ===")
    
    $corrected = @($repairs | Where-Object {$_.Status -eq "Corrected"}).Count
    $alreadyOk = @($repairs | Where-Object {$_.Status -eq "AlreadyCorrect"}).Count
    $needReview = @($repairs | Where-Object {$_.Status -eq "ManualReview"}).Count
    $syntaxFail = @($repairs | Where-Object {$_.Status -eq "SyntaxFailed"}).Count
    
    $importOk = @($validations.Values | Where-Object {$_ -eq "SUCCESS"}).Count
    $importFail = @($validations.Values | Where-Object {$_ -ne "SUCCESS"}).Count
    
    $stats = $log.Stats()
    
    $report = @"
================================================================================
INSTITUTIONAL IMPORT CORRECTION REPORT
================================================================================
Execution: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Session: $($log.SessionId)
Project: $PROJECT_ROOT
================================================================================

SUMMARY
--------------------------------------------------------------------------------
Total Strategies Processed: $($repairs.Count)
Successfully Corrected: $corrected
Already Correct: $alreadyOk
Require Manual Review: $needReview
Syntax Validation Failed: $syntaxFail

IMPORT VALIDATION
--------------------------------------------------------------------------------
Successful Imports: $importOk
Failed Imports: $importFail

BACKUP
--------------------------------------------------------------------------------
Location: $($backup.Path)
Files Backed Up: $($backup.Files.Count)
Manifest: $MANIFEST_FILE

DETAILED RESULTS
--------------------------------------------------------------------------------
"@

    foreach ($r in $repairs) {
        $report += "`n$($r.File):"
        $report += "`n  Status: $($r.Status)"
        if ($r.Changes.Count -gt 0) {
            $report += "`n  Corrections: $($r.Changes -join ', ')"
        }
        $stratName = [System.IO.Path]::GetFileNameWithoutExtension($r.File)
        if ($validations.ContainsKey($stratName)) {
            $report += "`n  Import: $($validations[$stratName])"
        }
    }
    
    $report += @"

`nLOGGING STATISTICS
--------------------------------------------------------------------------------
Total Entries: $($stats.Total)
Errors: $($stats.Errors)
Warnings: $($stats.Warnings)
Success: $($stats.Success)

Log File: $LOG_FILE
================================================================================
"@

    $reportPath = Join-Path $REPORT_DIR "import_correction_$TIMESTAMP.txt"
    if (-not (Test-Path $REPORT_DIR)) {
        New-Item -ItemType Directory -Path $REPORT_DIR -Force | Out-Null
    }
    
    $report | Out-File -FilePath $reportPath -Encoding UTF8
    Write-Host $report
    
    $log.Log("SUCCESS", "Report saved: $reportPath")
    
    return $reportPath
}

function Invoke-Correction {
    Write-Host "`n================================================================================" -ForegroundColor Cyan
    Write-Host "INSTITUTIONAL IMPORT CORRECTION SYSTEM v1.0" -ForegroundColor Cyan
    Write-Host "================================================================================" -ForegroundColor Cyan
    Write-Host ""
    
    $log = [Logger]::new($LOG_FILE)
    
    try {
        $files = Test-Prerequisites -log $log
        
        if (-not $SkipBackup) {
            $backup = New-Backup -files $files -log $log
        } else {
            $log.Log("WARN", "Backup skipped")
            $backup = @{Files=@(); Path="SKIPPED"}
        }
        
        $log.Log("INFO", "=== PHASE 3: ANALYZING AND CORRECTING ===")
        $repairs = @()
        foreach ($f in $files) {
            $repairs += Repair-Import -file $f -log $log -dry $DryRun
        }
        
        if (-not $DryRun) {
            $validations = Test-Imports -files $files -log $log
        } else {
            $log.Log("INFO", "Validation skipped (dry-run mode)")
            $validations = @{}
        }
        
        $reportPath = New-Report -repairs $repairs -validations $validations -backup $backup -log $log
        
        $log.Log("SUCCESS", "Correction system completed")
        
    } catch {
        $log.Log("ERROR", "Critical failure: $($_.Exception.Message)")
        throw
    }
}

Invoke-Correction
