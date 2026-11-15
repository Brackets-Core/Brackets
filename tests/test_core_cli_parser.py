#!/usr/bin/env python3
"""Tests para constructor de parser CLI extraído de main.py."""

import os
import sys

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.cli_parser import build_cli_parser


class TestCoreCliParser:
    """Valida parser CLI base y aliases de opciones."""

    def __init__(self):
        self.passed = 0
        self.failed = 0

    def _assert(self, condition: bool, message: str):
        if not condition:
            raise AssertionError(message)

    def test_parser_accepts_aliases(self):
        try:
            parser = build_cli_parser()
            args = parser.parse_args(["-d", "my-vault", "-w", "-m", "-l"])

            self._assert(args.directory == "my-vault", "Debe parsear -d")
            self._assert(args.weekly is True, "Debe parsear -w")
            self._assert(args.monthly is True, "Debe parsear -m")
            self._assert(args.list is True, "Debe parsear -l")

            print("✅ Test: parser acepta aliases cortos")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test parser_accepts_aliases falló: {e}")
            self.failed += 1

    def test_parser_accepts_long_options(self):
        try:
            parser = build_cli_parser()
            args = parser.parse_args([
                "--directory",
                "vault",
                "--add-task",
                "Preparar release",
                "--task-target",
                "monthly",
                "--consolidate",
                "2026-05",
                "--consolidate-year",
                "2026",
                "--debug",
                "--test-emoji",
                "--analyze",
                "file.md",
            ])

            self._assert(args.directory == "vault", "Debe parsear --directory")
            self._assert(args.add_task == "Preparar release", "Debe parsear --add-task")
            self._assert(args.task_target == "monthly", "Debe parsear --task-target")
            self._assert(args.consolidate == "2026-05", "Debe parsear --consolidate")
            self._assert(args.consolidate_year == "2026", "Debe parsear --consolidate-year")
            self._assert(args.debug is True, "Debe parsear --debug")
            self._assert(args.test_emoji is True, "Debe parsear --test-emoji")
            self._assert(args.analyze == "file.md", "Debe parsear --analyze")

            print("✅ Test: parser acepta opciones largas")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test parser_accepts_long_options falló: {e}")
            self.failed += 1

    def test_parser_defaults(self):
        try:
            parser = build_cli_parser()
            args = parser.parse_args([])

            self._assert(args.directory is None, "directory por defecto debe ser None")
            self._assert(args.weekly is False, "weekly por defecto debe ser False")
            self._assert(args.monthly is False, "monthly por defecto debe ser False")
            self._assert(args.add_task is None, "add_task por defecto debe ser None")
            self._assert(args.task_target == "weekly", "task_target por defecto debe ser weekly")
            self._assert(args.timer is False, "timer por defecto debe ser False")
            self._assert(args.list is False, "list por defecto debe ser False")
            self._assert(args.debug is False, "debug por defecto debe ser False")
            self._assert(args.test_emoji is False, "test_emoji por defecto debe ser False")
            self._assert(args.analyze is None, "analyze por defecto debe ser None")

            print("✅ Test: parser mantiene defaults esperados")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test parser_defaults falló: {e}")
            self.failed += 1

    def run_all(self):
        print("\n🧪 TESTS: core/cli_parser.py")
        print("=" * 50)

        self.test_parser_accepts_aliases()
        self.test_parser_accepts_long_options()
        self.test_parser_defaults()

        print(f"\n📊 Resultado: ✅ {self.passed} | ❌ {self.failed}")
        return self.failed == 0


if __name__ == "__main__":
    tester = TestCoreCliParser()
    success = tester.run_all()
    sys.exit(0 if success else 1)
