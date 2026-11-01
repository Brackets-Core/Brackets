#!/usr/bin/env python3
"""CLI action dispatch helpers extracted from main entrypoint."""

import os
import re
from typing import Optional

from brackets.utils.content_parser import debug_content_parsing
from brackets.utils.file_finder import debug_files_in_directory
from brackets.utils.legacy_utils import test_emoji_pattern
from brackets.utils.file_finder import FileFinder
from brackets.utils.legacy_utils import safe_file_read, safe_file_write


def has_action_flags(args) -> bool:
    """Return True when any direct action flag is present in CLI args."""
    return any(
        [
            args.weekly,
            args.monthly,
            bool(args.add_task),
            args.timer,
            getattr(args, "timer_gui", False),
            getattr(args, "web", False),
            args.consolidate,
            args.consolidate_year,
            args.list,
            args.debug,
            args.test_emoji,
            args.analyze,
        ]
    )


def dispatch_cli_action(args, manager, vault_directory: str) -> Optional[int]:
    """Execute direct CLI actions and return an exit code, or None for interactive mode."""
    event_log = manager.event_log

    if getattr(args, "web", False):
        from brackets.web import run_web_server

        port = getattr(args, "port", 8080)
        open_browser = not getattr(args, "no_browser", False)
        run_web_server(port=port, workspace_root=vault_directory, open_browser=open_browser)
        return 0

    if args.add_task:
        target = args.task_target or "weekly"
        success = add_task_to_latest_file(vault_directory, args.add_task, target)
        if success:
            event_log.append("task_added", task_text=args.add_task, target=target, source="cli")
        return 0 if success else 1

    if args.weekly:
        if not manager.bitacoras_enabled:
            print("❌ Bitácoras desactivadas por configuración (feature_flags.bitacoras_enabled=false)")
            return 1
        print("📅️ Creando bitácora semanal...")
        success = manager.weekly_gen.create_next_or_manual_weekly_bitacora()
        if success:
            event_log.append("bitacora_generated", type="weekly", source="cli")
        return 0 if success else 1

    if args.monthly:
        if not manager.bitacoras_enabled:
            print("❌ Bitácoras desactivadas por configuración (feature_flags.bitacoras_enabled=false)")
            return 1
        print("📋 Creando archivo mensual...")
        success = manager.monthly_gen.create_next_monthly_topics()
        if success:
            event_log.append("bitacora_generated", type="monthly", source="cli")
        return 0 if success else 1

    if getattr(args, "timer_gui", False):
        try:
            from brackets.modules.pomodoro_retro_ui import launch_retro_pomodoro
            launch_retro_pomodoro(vault_directory)
            return 0
        except Exception as ex:
            print(f"⚠️ Error al abrir app retro ({ex}), abriendo consola...")

    if args.timer:
        from brackets.modules.pomodoro_timer import run_pomodoro_standalone

        run_pomodoro_standalone(vault_directory, event_log=event_log)
        return 0

    if args.consolidate:
        if not manager.bitacoras_enabled:
            print("❌ Bitácoras desactivadas por configuración (feature_flags.bitacoras_enabled=false)")
            return 1
        print(f"📦 Consolidando mes {args.consolidate}...")
        match = re.match(r"(\d{4})-(\d{2})", args.consolidate)
        if not match:
            print("❌ Formato inválido. Use YYYY-MM (ejemplo: 2025-07)")
            return 1
        year = int(match.group(1))
        month = int(match.group(2))
        success = manager.month_consolidator.consolidate_month(year, month)
        return 0 if success else 1

    if args.consolidate_year:
        if not manager.bitacoras_enabled:
            print("❌ Bitácoras desactivadas por configuración (feature_flags.bitacoras_enabled=false)")
            return 1
        print(f"📅 Consolidando año {args.consolidate_year}...")
        try:
            year = int(args.consolidate_year)
            success = manager.year_consolidator.consolidate_year(year)
            return 0 if success else 1
        except ValueError:
            print("❌ Formato inválido. Use YYYY (ejemplo: 2025)")
            return 1

    if args.list:
        print("📊 Archivos recientes:")
        print("\n📝 Bitácoras semanales:")
        manager.weekly_gen.list_recent_weeks(10)
        print("\n📋 Archivos mensuales:")
        manager.monthly_gen.list_recent_months(5)
        return 0

    if args.debug:
        debug_files_in_directory(vault_directory)
        return 0

    if args.test_emoji:
        test_emoji_pattern()
        return 0

    if args.analyze:
        filepath = args.analyze
        if not os.path.exists(filepath):
            filepath = os.path.join(vault_directory, args.analyze)

        if os.path.exists(filepath):
            debug_content_parsing(filepath)
            return 0

        print(f"❌ Archivo no encontrado: {args.analyze}")
        return 1

    return None


def add_task_to_latest_file(vault_directory: str, task_text: str, target: str = "weekly", silent: bool = False) -> bool:
    """Append a pending task into specific section of the latest weekly/monthly file."""
    task = (task_text or "").strip()
    if not task:
        if not silent:
            print("❌ El texto de la tarea no puede estar vacío")
        return False

    finder = FileFinder(vault_directory)
    is_today = target == "today"
    
    if target == "monthly":
        filepath = finder.get_most_recent_monthly()
        label = "mensual"
        section_type = "topics"
    else:
        filepath = finder.get_most_recent_weekly()
        label = "hoy (semanal)" if is_today else "semanal"
        section_type = "day" if is_today else "topics"

    if not filepath:
        if not silent:
            print(f"❌ No se encontró archivo {label} para añadir la tarea")
        return False

    content = safe_file_read(filepath)
    if not content:
        return False

    if section_type == "day":
        from datetime import datetime
        day_to_find = datetime.now().day
        updated = _insert_task_into_day_section(content, task, day_to_find)
        if updated == content:
            if not silent:
                print(f"⚠️ No se encontró la sección para el día {day_to_find} en {os.path.basename(filepath)}")
                print("💡 Añadiendo a la sección Topics como fallback...")
            updated = _insert_task_into_topics(content, task)
    else:
        updated = _insert_task_into_topics(content, task)

    if updated == content:
        if not silent:
            print("⚠️ No se realizaron cambios en el archivo")
        return False

    if not safe_file_write(filepath, updated):
        return False

    if not silent:
        print(f"✅ Tarea añadida en {os.path.basename(filepath)}")
    return True


def _insert_task_into_day_section(content: str, task: str, day: int) -> str:
    """Insert task line in a specific day section (## ICONday)."""
    task_line = f"  - [ ] {task}"
    # Header format: ## ICONday (Note) or ## ICONday
    # Matches: ## 🏠27, ## 🚗27 (Oficina), etc.
    day_header_re = re.compile(rf"^##\s+.*{day}(?:\s|\(|$)", re.MULTILINE)
    match = day_header_re.search(content)

    if not match:
        return content

    # Find next heading to determine end of section
    next_heading_re = re.compile(r"^##\s+", re.MULTILINE)
    insert_pos = len(content)
    for next_match in next_heading_re.finditer(content, match.end()):
        insert_pos = next_match.start()
        break

    before = content[:insert_pos]
    after = content[insert_pos:]

    # Ensure clean insertion
    if before and not before.endswith("\n"):
        before += "\n"
    
    # Optional: Insert before separator --- if present in the section
    section_part = before[match.end():]
    if "---" in section_part:
        sep_pos = match.end() + section_part.rfind("---")
        before = content[:sep_pos]
        after = content[sep_pos:]
        if not before.endswith("\n"):
            before += "\n"

    return before + f"{task_line}\n" + after


def _insert_task_into_topics(content: str, task: str) -> str:
    """Insert task line in Topics section, creating the section if needed."""
    task_line = f"  - [ ] {task}"
    heading_re = re.compile(r"^##\s+(?:✅\s*)?Topics\s*$", re.MULTILINE)
    heading = heading_re.search(content)

    if not heading:
        suffix = "" if content.endswith("\n") else "\n"
        return f"{content}{suffix}\n## ✅Topics\n{task_line}\n"

    insert_pos = len(content)
    next_heading_re = re.compile(r"^##\s+", re.MULTILINE)
    for match in next_heading_re.finditer(content, heading.end()):
        insert_pos = match.start()
        break

    before = content[:insert_pos]
    after = content[insert_pos:]

    if before and not before.endswith("\n"):
        before += "\n"
    before += f"{task_line}\n"

    return before + after
