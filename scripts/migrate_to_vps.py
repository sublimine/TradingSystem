import paramiko
import os
import sys
from pathlib import Path
import time

VPS_IP = '81.17.100.15'
VPS_USER = 'root'
VPS_PASSWORD = '93ekgc*gUfz7VA7p'

print('=' * 80)
print('MIGRACIÓN AUTOMATIZADA AL VPS CONTABO')
print('=' * 80)

from scp import SCPClient

# PASO 1: Conectar al VPS
print('\n[1/8] Conectando al VPS 81.17.100.15...')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(VPS_IP, username=VPS_USER, password=VPS_PASSWORD, timeout=30, port=22)
    print('✓ Conexión SSH establecida')
except Exception as e:
    print(f'✗ ERROR: {e}')
    print('\nEl VPS Contabo usa Linux, no Windows.')
    print('Verificando sistema operativo...')
    sys.exit(1)

# Verificar si es Linux o Windows
print('\n[2/8] Detectando sistema operativo...')
stdin, stdout, stderr = ssh.exec_command('uname -a')
os_info = stdout.read().decode('utf-8', errors='ignore')

if 'Linux' in os_info:
    print(f'✓ Sistema detectado: Linux')
    print(f'  Detalles: {os_info.strip()[:80]}')
    
    print('\n⚠️  IMPORTANTE: Su VPS tiene LINUX, no Windows')
    print('\nOpciones:')
    print('1. Reinstalar el VPS con Windows Server (desde panel Contabo)')
    print('2. Adaptar el sistema para Linux (requiere Docker)')
    
    ssh.close()
    sys.exit(0)
else:
    print('Sistema detectado: Windows')
    print('Continuando con migración...')

ssh.close()

print('\n' + '=' * 80)
print('SIGUIENTE ACCIÓN REQUERIDA')
print('=' * 80)
print('\nSu VPS tiene Linux. Para ejecutar el sistema de trading necesita:')
print('\nOpción A (Recomendada): Reinstalar VPS con Windows')
print('  1. Vaya al panel de Contabo')
print('  2. Reinstale el VPS seleccionando Windows Server 2022')
print('  3. Ejecute este script nuevamente')
print('\nOpción B: Adaptar el sistema para Linux')
print('  Requiere configuración adicional con Docker')
print('  ¿Desea que prepare los scripts para Linux?')
print('=' * 80)
