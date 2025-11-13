# SCRIPT DE CONFIGURACIÓN AUTOMÁTICA PARA VPS
# Ejecutar DENTRO del VPS después de conectar con Remote Desktop

Write-Host "`nCONFIGURACIÓN AUTOMÁTICA DEL VPS CONTABO" -ForegroundColor Cyan
Write-Host "=========================================`n" -ForegroundColor Cyan

# Deshabilitar IE Enhanced Security
Write-Host "[1/7] Configurando sistema..." -ForegroundColor Yellow
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Active Setup\Installed Components\{A509B1A7-37EF-4b3f-8CFC-4F3A74704073}" -Name "IsInstalled" -Value 0
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Active Setup\Installed Components\{A509B1A8-37EF-4b3f-8CFC-4F3A74704073}" -Name "IsInstalled" -Value 0

# Instalar Chocolatey
Write-Host "[2/7] Instalando gestor de paquetes..." -ForegroundColor Yellow
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

refreshenv

# Instalar software necesario
Write-Host "[3/7] Instalando Python 3.13..." -ForegroundColor Yellow
choco install python --version=3.13.0 -y

Write-Host "[4/7] Instalando PostgreSQL 17..." -ForegroundColor Yellow
choco install postgresql17 --params '/Password:abc /Port:5432' -y

Write-Host "[5/7] Instalando 7-Zip..." -ForegroundColor Yellow
choco install 7zip -y

Write-Host "[6/7] Instalando Chrome..." -ForegroundColor Yellow
choco install googlechrome -y

refreshenv

Write-Host "[7/7] Instalando dependencias de Python..." -ForegroundColor Yellow
pip install MetaTrader5 --break-system-packages
pip install psycopg2-binary --break-system-packages
pip install pandas --break-system-packages
pip install numpy --break-system-packages

Write-Host "`n✓ VPS CONFIGURADO CORRECTAMENTE" -ForegroundColor Green
Write-Host "`nAhora necesita:" -ForegroundColor Cyan
Write-Host "1. Descargar MetaTrader 5 desde: https://www.metatrader5.com/en/download" -ForegroundColor White
Write-Host "2. Transferir el sistema desde su PC local" -ForegroundColor White

Write-Host "`nPresione Enter para continuar..." -ForegroundColor Yellow
Read-Host
