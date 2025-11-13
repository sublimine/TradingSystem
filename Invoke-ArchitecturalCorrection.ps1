$ErrorActionPreference = "Stop"
$PROJECT_ROOT = "C:\TradingSystem"
$STRATEGIES_DIR = Join-Path $PROJECT_ROOT "src\strategies"
$TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"
$LOG_FILE = Join-Path $PROJECT_ROOT "logs\architectural_correction_$TIMESTAMP.log"
$BACKUP_DIR = Join-Path $PROJECT_ROOT "backups\architectural_correction_$TIMESTAMP"

$CORRECT_IMPORT = "from .strategy_base import StrategyBase, Signal"
$SIGNAL_IMPORT_PATTERNS = @(
    '^\s*import\s+Signal\s*$',
    '^\s*from\s+models\s+import\s+Signal\s*$',
    '^\s*from\s+src\.core\.models\s+import\s+Signal\s*$',
    '^\s*from\s+src\.models\s+import\s+Signal\s*$',
    '^\s*from\s+strategies\.base\s+import.*Signal.*$',
    '^\s*from\s+Signal\s+import.*$'
)

function Write-Log {
    param([string]$level, [string]$msg)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff"
    $color = switch ($level) {
        "ERROR" { "Red" }
        "WARN" { "Yellow" }
        "SUCCESS" { "Green" }
        "INFO" { "Cyan" }
        default { "White" }
    }
    $line = "[$ts][$level] $msg"
    Write-Host $line -ForegroundColor $color
    Add-Content -Path $LOG_FILE -Value $line -Encoding UTF8
}

function Remove-BOM {
    param([string]$path)
    
    $bytes = [System.IO.File]::ReadAllBytes($path)
    
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        Write-Log "INFO" "  Removing BOM from file"
        $content = [System.IO.File]::ReadAllText($path, [System.Text.UTF8Encoding]::new($false))
        [System.IO.File]::WriteAllText($path, $content, [System.Text.UTF8Encoding]::new($false))
        return $true
    }
    return $false
}

function Test-PythonSyntax {
    param([string]$path)
    
    $check = @"
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
    $check | Out-File -FilePath $temp -Encoding UTF8
    
    try {
        $result = & python $temp 2>&1 | Out-String
        Remove-Item $temp -Force
        return $result.Trim()
    } catch {
        Remove-Item $temp -Force -ErrorAction SilentlyContinue
        return "ERROR:Execution failed"
    }
}

function Repair-Imports {
    param([string]$path, [string]$filename)
    
    Write-Log "INFO" "Processing: $filename"
    
    $content = Get-Content -Path $path -Raw -Encoding UTF8
    $original = $content
    
    $bomRemoved = Remove-BOM -path $path
    if ($bomRemoved) {
        $content = Get-Content -Path $path -Raw -Encoding UTF8
    }
    
    $lines = $content -split "`r?`n"
    $newLines = [System.Collections.ArrayList]@()
    $removedCount = 0
    $hasCorrectImport = $false
    $lastImportIndex = -1
    
    for ($i = 0; $i -lt $lines.Count; $i++) {
        $line = $lines[$i]
        $shouldRemove = $false
        
        foreach ($pattern in $SIGNAL_IMPORT_PATTERNS) {
            if ($line -match $pattern) {
                Write-Log "INFO" "  Removing incorrect import: $($line.Trim())"
                $shouldRemove = $true
                $removedCount++
                break
            }
        }
        
        if (-not $shouldRemove) {
            [void]$newLines.Add($line)
            
            if ($line -match '^\s*from\s+\.strategy_base\s+import.*Signal') {
                $hasCorrectImport = $true
            }
            
            if ($line -match '^\s*(import|from)\s+' -and $line -notmatch 'strategy_base') {
                $lastImportIndex = $newLines.Count - 1
            }
        }
    }
    
    if (-not $hasCorrectImport) {
        if ($lastImportIndex -ge 0) {
            $newLines.Insert($lastImportIndex + 1, $CORRECT_IMPORT)
            Write-Log "INFO" "  Inserted correct import after line $($lastImportIndex + 1)"
        } else {
            $newLines.Insert(0, $CORRECT_IMPORT)
            Write-Log "INFO" "  Inserted correct import at beginning"
        }
    }
    
    $newContent = $newLines -join "`n"
    
    if ($newContent -ne $original -or $bomRemoved) {
        [System.IO.File]::WriteAllText($path, $newContent, [System.Text.UTF8Encoding]::new($false))
        
        $syntax = Test-PythonSyntax -path $path
        if ($syntax -notmatch "^VALID") {
            Write-Log "ERROR" "  Syntax validation failed: $syntax"
            [System.IO.File]::WriteAllText($path, $original, [System.Text.UTF8Encoding]::new($false))
            return @{Status="SyntaxFailed"; BOMRemoved=$bomRemoved; ImportsRemoved=$removedCount}
        }
        
        Write-Log "SUCCESS" "  File corrected (BOM removed: $bomRemoved, imports cleaned: $removedCount)"
        return @{Status="Corrected"; BOMRemoved=$bomRemoved; ImportsRemoved=$removedCount}
    }
    
    Write-Log "SUCCESS" "  Already correct"
    return @{Status="AlreadyCorrect"; BOMRemoved=$false; ImportsRemoved=0}
}

function Test-Import {
    param([string]$name)
    
    $test = @"
import sys
sys.path.insert(0, r'$PROJECT_ROOT')
try:
    from src.strategies.$name import *
    print('SUCCESS')
except Exception as e:
    print(f'FAIL:{e}')
"@
    
    $temp = [System.IO.Path]::GetTempFileName() + ".py"
    $test | Out-File -FilePath $temp -Encoding UTF8
    
    try {
        $result = & python $temp 2>&1 | Out-String
        Remove-Item $temp -Force
        return $result.Trim()
    } catch {
        Remove-Item $temp -Force -ErrorAction SilentlyContinue
        return "ERROR:Execution failed"
    }
}

Write-Host "`n================================================================================" -ForegroundColor Cyan
Write-Host "ARCHITECTURAL CORRECTION SYSTEM - DEFINITIVE SOLUTION" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

$logDir = Split-Path $LOG_FILE -Parent
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

Write-Log "INFO" "=== PHASE 1: BACKUP CREATION ==="

if (-not (Test-Path $BACKUP_DIR)) {
    New-Item -ItemType Directory -Path $BACKUP_DIR -Force | Out-Null
}

$files = Get-ChildItem -Path $STRATEGIES_DIR -Filter "*.py" | Where-Object {
    $_.Name -ne "__init__.py" -and $_.Name -ne "strategy_base.py"
}

foreach ($file in $files) {
    $dest = Join-Path $BACKUP_DIR $file.Name
    Copy-Item -Path $file.FullName -Destination $dest -Force
}

Write-Log "SUCCESS" "Backed up $($files.Count) files to $BACKUP_DIR"

Write-Log "INFO" "=== PHASE 2: BOM REMOVAL AND IMPORT CORRECTION ==="

$results = @()
foreach ($file in $files) {
    $result = Repair-Imports -path $file.FullName -filename $file.Name
    $result.File = $file.Name
    $results += $result
}

Write-Log "INFO" "=== PHASE 3: IMPORT VALIDATION ==="

$validations = @{}
foreach ($file in $files) {
    $name = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
    $validation = Test-Import -name $name
    
    if ($validation -match "SUCCESS") {
        Write-Log "SUCCESS" "  Import OK: $name"
        $validations[$name] = "SUCCESS"
    } else {
        Write-Log "ERROR" "  Import FAILED: $name - $validation"
        $validations[$name] = $validation
    }
}

Write-Log "INFO" "=== SUMMARY ==="

$corrected = @($results | Where-Object {$_.Status -eq "Corrected"}).Count
$alreadyOk = @($results | Where-Object {$_.Status -eq "AlreadyCorrect"}).Count
$failed = @($results | Where-Object {$_.Status -eq "SyntaxFailed"}).Count
$importSuccess = @($validations.Values | Where-Object {$_ -eq "SUCCESS"}).Count

Write-Log "INFO" "Files Corrected: $corrected"
Write-Log "INFO" "Already Correct: $alreadyOk"
Write-Log "INFO" "Syntax Failures: $failed"
Write-Log "INFO" "Successful Imports: $importSuccess / $($files.Count)"

if ($importSuccess -eq $files.Count) {
    Write-Log "SUCCESS" "ALL IMPORTS VALIDATED SUCCESSFULLY"
} else {
    Write-Log "ERROR" "Some imports still failing - manual review required"
}

Write-Host "`n================================================================================" -ForegroundColor Cyan
