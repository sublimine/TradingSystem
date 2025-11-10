#!/usr/bin/env python
"""
Claude Code Agent - Ejecución Local Profesional
Conecta Claude Sonnet 4.5 directamente a tu VPS para ejecución automática.

Uso:
    Modo interactivo:  python claude_agent.py
    Modo batch:        python claude_agent.py --batch tasks.txt

    Formato tasks.txt (separa tareas con "---"):

    Tarea 1: Validar gestión de riesgo
    Ejecuta validaciones completas...
    [prompt extenso aquí]

    ---

    Tarea 2: Ejecutar backtest
    Realiza backtest de 30 días...
    [otro prompt extenso]

    ---

Configuración:
    Requiere ANTHROPIC_API_KEY en variable de entorno o .env
"""

import os
import sys
import subprocess
import platform
from pathlib import Path
from anthropic import Anthropic
import json
from datetime import datetime
import argparse

# Configuración
BASE_DIR = Path(__file__).parent.resolve()
SYSTEM_TYPE = platform.system()  # Windows, Linux, Darwin
SHELL = "powershell.exe" if SYSTEM_TYPE == "Windows" else "/bin/bash"

# Colores para terminal
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    """Imprime header estilizado"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}\n")

def print_success(text):
    """Imprime mensaje de éxito"""
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")

def print_error(text):
    """Imprime mensaje de error"""
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")

def print_info(text):
    """Imprime mensaje informativo"""
    print(f"{Colors.OKCYAN}ℹ️  {text}{Colors.ENDC}")

def print_warning(text):
    """Imprime advertencia"""
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")

def execute_command(command: str, cwd: str = None) -> dict:
    """
    Ejecuta comando en shell local y retorna resultado.

    Args:
        command: Comando a ejecutar
        cwd: Directorio de trabajo (default: BASE_DIR)

    Returns:
        dict con stdout, stderr, returncode
    """
    if cwd is None:
        cwd = str(BASE_DIR)

    try:
        if SYSTEM_TYPE == "Windows":
            # En Windows, usar PowerShell
            result = subprocess.run(
                ["powershell.exe", "-Command", command],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 min timeout
                encoding='utf-8',
                errors='replace'
            )
        else:
            # En Linux/Mac, usar bash
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300,
                encoding='utf-8',
                errors='replace'
            )

        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "success": result.returncode == 0
        }

    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": "ERROR: Comando excedió timeout de 5 minutos",
            "returncode": -1,
            "success": False
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": f"ERROR ejecutando comando: {str(e)}",
            "returncode": -1,
            "success": False
        }

def get_system_info() -> str:
    """Retorna información del sistema"""
    info = f"""
Sistema Operativo: {platform.system()} {platform.release()}
Arquitectura: {platform.machine()}
Python: {sys.version.split()[0]}
Directorio actual: {BASE_DIR}
Shell: {SHELL}
Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    return info.strip()

def chat_with_claude(client: Anthropic, user_message: str, conversation_history: list) -> str:
    """
    Envía mensaje a Claude y recibe respuesta.

    Args:
        client: Cliente de Anthropic
        user_message: Mensaje del usuario
        conversation_history: Historial de conversación

    Returns:
        Respuesta de Claude
    """
    # Agregar mensaje del usuario al historial
    conversation_history.append({
        "role": "user",
        "content": user_message
    })

    # Sistema prompt
    system_prompt = f"""Eres Claude Code ejecutándose localmente en el VPS del usuario.

INFORMACIÓN DEL SISTEMA:
{get_system_info()}

CAPACIDADES:
- Puedes ejecutar comandos directamente usando el formato: [EXECUTE: comando]
- Puedes leer archivos del proyecto
- Puedes modificar código
- Puedes ejecutar tests, validaciones, scripts
- Iteras automáticamente hasta resolver errores

IMPORTANTE:
- Cuando necesites ejecutar un comando, usa EXACTAMENTE este formato:
  [EXECUTE: comando_aqui]

- Ejemplo: [EXECUTE: python scripts/live_trading_engine.py --dry-run]
- Ejemplo: [EXECUTE: Get-ChildItem src]
- Ejemplo: [EXECUTE: git status]

- NO uses markdown code blocks para comandos que quieras ejecutar
- USA [EXECUTE: ...] para CUALQUIER comando que deba ejecutarse

El sistema ejecutará automáticamente tus [EXECUTE: ...] y te mostrará los resultados.

Tu objetivo: Completar las tareas del usuario de forma autónoma, iterando hasta resolver todos los errores.
"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",  # Claude Sonnet 4.5
            max_tokens=4096,
            system=system_prompt,
            messages=conversation_history
        )

        assistant_message = response.content[0].text

        # Agregar respuesta al historial
        conversation_history.append({
            "role": "assistant",
            "content": assistant_message
        })

        return assistant_message

    except Exception as e:
        return f"ERROR comunicándose con Claude API: {str(e)}"

def parse_and_execute_commands(response: str, conversation_history: list, client: Anthropic) -> str:
    """
    Parsea la respuesta de Claude, ejecuta comandos y retorna actualización.

    Args:
        response: Respuesta de Claude
        conversation_history: Historial de conversación
        client: Cliente de Anthropic

    Returns:
        Respuesta actualizada después de ejecuciones
    """
    import re

    # Buscar comandos en formato [EXECUTE: comando]
    commands = re.findall(r'\[EXECUTE:\s*(.+?)\]', response)

    if not commands:
        return response

    print_info(f"Encontrados {len(commands)} comando(s) para ejecutar")

    execution_results = []

    for idx, command in enumerate(commands, 1):
        print(f"\n{Colors.OKCYAN}{'─' * 80}{Colors.ENDC}")
        print_info(f"Ejecutando comando {idx}/{len(commands)}:")
        print(f"{Colors.BOLD}{command}{Colors.ENDC}")

        result = execute_command(command)

        if result["success"]:
            print_success(f"Comando completado exitosamente (exit code: {result['returncode']})")
        else:
            print_error(f"Comando falló (exit code: {result['returncode']})")

        # Mostrar output
        if result["stdout"]:
            print(f"\n{Colors.OKBLUE}STDOUT:{Colors.ENDC}")
            print(result["stdout"][:2000])  # Limitar a 2000 chars
            if len(result["stdout"]) > 2000:
                print(f"{Colors.WARNING}... (output truncado){Colors.ENDC}")

        if result["stderr"]:
            print(f"\n{Colors.FAIL}STDERR:{Colors.ENDC}")
            print(result["stderr"][:2000])
            if len(result["stderr"]) > 2000:
                print(f"{Colors.WARNING}... (output truncado){Colors.ENDC}")

        execution_results.append({
            "command": command,
            "stdout": result["stdout"][:4000],  # Limitar para API
            "stderr": result["stderr"][:4000],
            "returncode": result["returncode"],
            "success": result["success"]
        })

    # Enviar resultados de vuelta a Claude
    results_message = "RESULTADOS DE EJECUCIÓN:\n\n"
    for idx, result in enumerate(execution_results, 1):
        results_message += f"Comando {idx}: {result['command']}\n"
        results_message += f"Exit Code: {result['returncode']}\n"
        if result['stdout']:
            results_message += f"STDOUT:\n{result['stdout']}\n"
        if result['stderr']:
            results_message += f"STDERR:\n{result['stderr']}\n"
        results_message += "\n" + "─" * 40 + "\n\n"

    results_message += "\n¿Qué necesitas hacer ahora basado en estos resultados?"

    print_info("Enviando resultados a Claude para análisis...")

    # Claude analiza los resultados y decide qué hacer
    next_response = chat_with_claude(client, results_message, conversation_history)

    # Recursivo: si Claude genera más comandos, ejecutarlos también
    return parse_and_execute_commands(next_response, conversation_history, client)

def load_tasks_from_file(file_path: str) -> list:
    """
    Carga tareas desde archivo, separadas por '---'

    Args:
        file_path: Ruta al archivo de tareas

    Returns:
        Lista de strings, cada uno es una tarea/prompt
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Separar por ---
        tasks = [task.strip() for task in content.split('---') if task.strip()]

        return tasks

    except FileNotFoundError:
        print_error(f"Archivo no encontrado: {file_path}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Error leyendo archivo: {str(e)}")
        sys.exit(1)

def run_batch_mode(tasks_file: str, api_key: str):
    """
    Ejecuta modo batch: procesa todas las tareas del archivo secuencialmente

    Args:
        tasks_file: Ruta al archivo de tareas
        api_key: API key de Anthropic
    """
    print_header("MODO BATCH - Ejecución Automática de Múltiples Tareas")

    # Cargar tareas
    tasks = load_tasks_from_file(tasks_file)
    total_tasks = len(tasks)

    print_success(f"{total_tasks} tarea(s) cargadas desde {tasks_file}")
    print_info(f"Directorio de trabajo: {BASE_DIR}")
    print_info(f"Sistema: {SYSTEM_TYPE}\n")

    # Crear log file
    log_file = BASE_DIR / f"agent_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    def log(message: str):
        """Escribe en log file y pantalla"""
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"{message}\n")
        print(message)

    log(f"{'=' * 80}")
    log(f"SESIÓN BATCH INICIADA: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"Total de tareas: {total_tasks}")
    log(f"Log file: {log_file}")
    log(f"{'=' * 80}\n")

    # Inicializar cliente
    client = Anthropic(api_key=api_key)

    # Estadísticas
    completed = 0
    failed = 0
    results_summary = []

    # Procesar cada tarea
    for idx, task in enumerate(tasks, 1):
        conversation_history = []  # Nueva conversación por tarea

        print_header(f"TAREA {idx}/{total_tasks}")
        log(f"\n{'=' * 80}")
        log(f"TAREA {idx}/{total_tasks}")
        log(f"{'=' * 80}")

        # Mostrar preview del prompt (primeras 200 chars)
        preview = task[:200] + "..." if len(task) > 200 else task
        log(f"\n{preview}\n")
        log(f"{'─' * 80}\n")

        try:
            # Enviar tarea a Claude
            print_info(f"Enviando tarea {idx} a Claude...")
            log(f"[{datetime.now().strftime('%H:%M:%S')}] Enviando a Claude...")

            response = chat_with_claude(client, task, conversation_history)

            log(f"\n[CLAUDE RESPONDE]:\n{response}\n")

            # Ejecutar comandos
            print_info("Ejecutando comandos automáticamente...")
            final_response = parse_and_execute_commands(response, conversation_history, client)

            if final_response != response:
                log(f"\n[CLAUDE ACTUALIZA]:\n{final_response}\n")

            print_success(f"Tarea {idx}/{total_tasks} completada")
            log(f"\n✅ TAREA {idx} COMPLETADA\n")

            completed += 1
            results_summary.append({
                "task_num": idx,
                "status": "SUCCESS",
                "preview": preview
            })

        except Exception as e:
            print_error(f"Error en tarea {idx}: {str(e)}")
            log(f"\n❌ ERROR EN TAREA {idx}: {str(e)}\n")

            failed += 1
            results_summary.append({
                "task_num": idx,
                "status": "FAILED",
                "preview": preview,
                "error": str(e)
            })

        log(f"{'=' * 80}\n")

    # Resumen final
    print_header("RESUMEN FINAL")
    log(f"\n{'=' * 80}")
    log(f"RESUMEN FINAL")
    log(f"{'=' * 80}\n")

    log(f"Total tareas:      {total_tasks}")
    log(f"✅ Completadas:    {completed}")
    log(f"❌ Fallidas:       {failed}")
    log(f"\nDetalle:\n")

    for result in results_summary:
        status_icon = "✅" if result["status"] == "SUCCESS" else "❌"
        log(f"{status_icon} Tarea {result['task_num']}: {result['status']}")
        log(f"   {result['preview'][:100]}")
        if result["status"] == "FAILED":
            log(f"   Error: {result.get('error', 'Unknown')}")
        log("")

    log(f"\n{'=' * 80}")
    log(f"SESIÓN FINALIZADA: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"Log completo guardado en: {log_file}")
    log(f"{'=' * 80}\n")

    print_success(f"\nLog completo guardado en: {log_file}")

    if failed > 0:
        print_warning(f"\n⚠️  {failed} tarea(s) fallaron. Revisa el log para detalles.")
    else:
        print_success("\n🎉 TODAS LAS TAREAS COMPLETADAS EXITOSAMENTE")

def main():
    """Función principal del agente"""

    # Parsear argumentos
    parser = argparse.ArgumentParser(
        description="Claude Code Agent - Ejecución local con Claude Sonnet 4.5",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Modo interactivo
  python claude_agent.py

  # Modo batch
  python claude_agent.py --batch tasks.txt
        """
    )
    parser.add_argument('--batch', metavar='FILE', help='Ejecutar en modo batch desde archivo de tareas')

    args = parser.parse_args()

    # Verificar API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")

    if not api_key:
        print_header("CLAUDE CODE AGENT - Ejecución Local Profesional")
        print_error("No se encontró ANTHROPIC_API_KEY en variables de entorno")
        print_info("Configúrala con:")
        if SYSTEM_TYPE == "Windows":
            print("  $env:ANTHROPIC_API_KEY = 'tu-api-key-aqui'")
        else:
            print("  export ANTHROPIC_API_KEY='tu-api-key-aqui'")
        sys.exit(1)

    # Modo batch o interactivo
    if args.batch:
        run_batch_mode(args.batch, api_key)
        return

    # Modo interactivo
    print_header("CLAUDE CODE AGENT - Ejecución Local Profesional")
    print_success("API Key encontrada")
    print_info(f"Directorio de trabajo: {BASE_DIR}")
    print_info(f"Sistema: {SYSTEM_TYPE}")

    # Inicializar cliente
    client = Anthropic(api_key=api_key)
    conversation_history = []

    print_header("Sesión Iniciada - Escribe tus instrucciones")
    print_info("Escribe 'salir' para terminar la sesión")
    print_info("Escribe 'limpiar' para resetear la conversación\n")

    while True:
        try:
            # Obtener input del usuario
            user_input = input(f"{Colors.BOLD}{Colors.OKGREEN}TÚ >{Colors.ENDC} ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['salir', 'exit', 'quit']:
                print_success("Cerrando sesión. ¡Hasta luego!")
                break

            if user_input.lower() in ['limpiar', 'clear', 'reset']:
                conversation_history = []
                print_success("Conversación reseteada")
                continue

            # Enviar a Claude
            print(f"\n{Colors.OKCYAN}CLAUDE >{Colors.ENDC} ", end="", flush=True)
            response = chat_with_claude(client, user_input, conversation_history)
            print(response)

            # Ejecutar comandos si los hay
            parse_and_execute_commands(response, conversation_history, client)

            print()  # Línea en blanco

        except KeyboardInterrupt:
            print(f"\n{Colors.WARNING}Interrupción detectada{Colors.ENDC}")
            confirm = input("¿Salir? (s/n): ").strip().lower()
            if confirm == 's':
                break
        except Exception as e:
            print_error(f"Error inesperado: {str(e)}")

if __name__ == "__main__":
    main()
