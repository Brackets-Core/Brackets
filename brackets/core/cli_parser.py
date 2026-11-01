#!/usr/bin/env python3
"""Argument parser builder for Brackets CLI."""

import argparse


def build_cli_parser() -> argparse.ArgumentParser:
    """Build and return the Brackets CLI parser."""
    parser = argparse.ArgumentParser(
        description="Generador de bitácoras semanales y archivos mensuales",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python main.py                             # Modo interactivo (gestor de vaults)
  python main.py -d .                        # Modo interactivo (vault actual)
  python main.py --weekly                   # Crear bitácora semanal directamente
  python main.py --monthly                  # Crear archivo mensual directamente
    python main.py --add-task "Preparar release"          # Añadir tarea al último weekly
    python main.py --add-task "Cerrar retrospectiva" --task-target monthly
    python main.py --timer                    # Abrir Pomodoro Timer
  python main.py --consolidate 2025-07      # Consolidar mes específico
  python main.py --consolidate-year 2025    # Consolidar año completo
  python main.py --list                     # Listar archivos recientes
  python main.py --debug                    # Información de debug
  python main.py --web                      # Iniciar Brackets Web Hub (PWA + REST API)
        """,
    )

    parser.add_argument(
        "--directory",
        "-d",
        default=None,
        help="Directorio del vault (por defecto: selector de vaults)",
    )

    parser.add_argument(
        "--weekly",
        "-w",
        action="store_true",
        help="Crear bitácora semanal directamente",
    )

    parser.add_argument(
        "--monthly",
        "-m",
        action="store_true",
        help="Crear archivo mensual directamente",
    )

    parser.add_argument(
        "--add-task",
        metavar="TEXTO",
        help="Añadir una tarea al último archivo weekly/monthly",
    )

    parser.add_argument(
        "--task-target",
        choices=["weekly", "monthly"],
        default="weekly",
        help="Destino de --add-task (default: weekly)",
    )

    parser.add_argument(
        "--timer",
        action="store_true",
        help="Abrir Pomodoro Timer",
    )

    parser.add_argument(
        "--timer-gui",
        action="store_true",
        help="Abrir Pomodoro Timer en ventana retro con Tomatín",
    )

    parser.add_argument(
        "--consolidate",
        "-c",
        metavar="YYYY-MM",
        help="Consolidar todos los archivos de un mes específico (formato: YYYY-MM)",
    )

    parser.add_argument(
        "--consolidate-year",
        metavar="YYYY",
        help="Consolidar todos los meses de un año específico (formato: YYYY)",
    )

    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="Listar archivos recientes",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Mostrar información de debug",
    )

    parser.add_argument(
        "--web",
        action="store_true",
        help="Iniciar Brackets Web Hub (interfaz PWA y API REST)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Puerto para Brackets Web Hub (por defecto: 8080)",
    )

    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="No abrir automáticamente el navegador al iniciar --web",
    )

    parser.add_argument(
        "--test-emoji",
        action="store_true",
        help="Probar patrón de emojis de trabajo",
    )

    parser.add_argument(
        "--analyze",
        metavar="ARCHIVO",
        help="Analizar contenido de un archivo específico",
    )

    return parser
