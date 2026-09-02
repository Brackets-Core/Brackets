#!/usr/bin/env python3
"""Pomodoro timer para Brackets (v1).

Incluye:
- Motor de estado testeable (sin I/O directo).
- UI de consola con barra de progreso y personaje parpadeante.
- Configuración YAML para foco/descanso/jornada.
- Hook de integración para registrar sesiones finalizadas.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
import os
import time
from typing import Callable, Dict, Optional

import yaml


DEFAULT_CONFIG_FILENAME = "pomodoro_timer.yaml"


@dataclass
class TimerConfig:
    """Configuración del timer en minutos/segundos de refresco."""

    focus_minutes: int = 25
    break_minutes: int = 5
    workday_minutes: int = 420
    progress_bar_width: int = 24
    tick_seconds: int = 1
    avatar_open: str = "(^_^)"
    avatar_closed: str = "(-_-)"

    @property
    def focus_seconds(self) -> int:
        return max(1, int(self.focus_minutes) * 60)

    @property
    def break_seconds(self) -> int:
        return max(1, int(self.break_minutes) * 60)

    @property
    def workday_seconds(self) -> int:
        return max(1, int(self.workday_minutes) * 60)

    def to_dict(self) -> Dict[str, int]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Dict) -> "TimerConfig":
        if not isinstance(payload, dict):
            return cls()

        default = cls()
        return cls(
            focus_minutes=int(payload.get("focus_minutes", default.focus_minutes)),
            break_minutes=int(payload.get("break_minutes", default.break_minutes)),
            workday_minutes=int(payload.get("workday_minutes", default.workday_minutes)),
            progress_bar_width=int(payload.get("progress_bar_width", default.progress_bar_width)),
            tick_seconds=int(payload.get("tick_seconds", default.tick_seconds)),
            avatar_open=str(payload.get("avatar_open", default.avatar_open)),
            avatar_closed=str(payload.get("avatar_closed", default.avatar_closed)),
        )


def _default_data_dir(base_dir: str) -> str:
    candidate = os.path.join(os.path.abspath(base_dir), "data")
    if os.path.isdir(candidate):
        return candidate
    return os.path.abspath(base_dir)


def load_timer_config(base_dir: str = ".") -> tuple[TimerConfig, str]:
    """Carga configuración de timer desde YAML. Si no existe, usa defaults."""

    data_dir = _default_data_dir(base_dir)
    config_path = os.path.join(data_dir, DEFAULT_CONFIG_FILENAME)

    if not os.path.exists(config_path):
        return TimerConfig(), config_path

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            payload = yaml.safe_load(f) or {}
        return TimerConfig.from_dict(payload), config_path
    except Exception:
        return TimerConfig(), config_path


def save_timer_config(config: TimerConfig, config_path: str) -> None:
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config.to_dict(), f, sort_keys=False, allow_unicode=True)


class PomodoroTimerEngine:
    """Motor del timer (sin dependencia de consola)."""

    def __init__(self, config: TimerConfig):
        self.config = config
        self.phase: str = "idle"
        self.is_running: bool = False
        self.is_paused: bool = False
        self.remaining_seconds: int = 0
        self.phase_total_seconds: int = 0
        self.completed_focus_sessions: int = 0
        self.worked_seconds_today: int = 0
        self.blink_open: bool = True
        self.last_event: Optional[str] = None
        self.last_session_record: Optional[Dict] = None
        self.active_task_id: Optional[str] = None
        self.active_project_id: Optional[str] = None
        self.active_task_title: Optional[str] = None
        self._on_session_completed: Optional[Callable[[Dict], None]] = None

    def set_active_task(
        self,
        task_id: Optional[str],
        project_id: Optional[str] = None,
        title: Optional[str] = None
    ) -> None:
        """Asocia una tarea al temporizador de foco actual."""
        self.active_task_id = task_id
        self.active_project_id = project_id
        self.active_task_title = title

    def set_session_completed_hook(self, callback: Optional[Callable[[Dict], None]]) -> None:
        """Hook de extensión para integración futura con notas/tareas."""
        self._on_session_completed = callback

    def start_focus(self) -> None:
        self.phase = "focus"
        self.phase_total_seconds = self.config.focus_seconds
        self.remaining_seconds = self.phase_total_seconds
        self.is_running = True
        self.is_paused = False
        self.last_event = "focus_started"
        self._session_start_ts = datetime.utcnow().isoformat() + "Z"

    def start_break(self) -> None:
        self.phase = "break"
        self.phase_total_seconds = self.config.break_seconds
        self.remaining_seconds = self.phase_total_seconds
        self.is_running = True
        self.is_paused = False
        self.last_event = "break_started"
        self._session_start_ts = datetime.utcnow().isoformat() + "Z"

    def pause(self) -> None:
        if self.is_running and not self.is_paused:
            self.is_paused = True
            self.last_event = "paused"

    def resume(self) -> None:
        if self.is_running and self.is_paused:
            self.is_paused = False
            self.last_event = "resumed"

    def reset(self) -> None:
        self.phase = "idle"
        self.is_running = False
        self.is_paused = False
        self.remaining_seconds = 0
        self.phase_total_seconds = 0
        self.last_event = "reset"
        self._session_start_ts = None

    def tick(self, seconds: int = 1) -> Optional[str]:
        """Avanza el temporizador. Devuelve evento si terminó fase."""
        if not self.is_running or self.is_paused:
            return None

        step = max(1, int(seconds))
        self.remaining_seconds = max(0, self.remaining_seconds - step)
        self.blink_open = not self.blink_open

        if self.remaining_seconds > 0:
            return None

        # Fin de fase
        self.is_running = False
        self.is_paused = False
        event = f"{self.phase}_finished"
        self.last_event = event

        if self.phase == "focus":
            self.completed_focus_sessions += 1
            self.worked_seconds_today += self.config.focus_seconds
            try:
                from brackets.worklog.log4brackets import log4brackets
                log4brackets.log_pomodoro(
                    task_id=self.active_task_id,
                    project_id=self.active_project_id,
                    duration_min=int(self.config.focus_seconds // 60)
                )
            except Exception:
                pass

        self.last_session_record = {
            "phase": self.phase,
            "started_at": self._session_start_ts,
            "ended_at": datetime.utcnow().isoformat() + "Z",
            "planned_seconds": self.phase_total_seconds,
            "workday_progress": round(self.workday_progress(), 4),
            "task_id": self.active_task_id,
            "project_id": self.active_project_id,
            "task_title": self.active_task_title,
        }

        if self.phase == "focus" and self._on_session_completed:
            self._on_session_completed(self.last_session_record)

        return event

    def progress(self) -> float:
        if self.phase_total_seconds <= 0:
            return 0.0
        completed = self.phase_total_seconds - self.remaining_seconds
        return max(0.0, min(1.0, completed / self.phase_total_seconds))

    def workday_progress(self) -> float:
        return max(0.0, min(1.0, self.worked_seconds_today / self.config.workday_seconds))

    def phase_label(self) -> str:
        if self.phase == "focus":
            return "FOCUS"
        if self.phase == "break":
            return "BREAK"
        return "IDLE"

    def avatar(self) -> str:
        return self.config.avatar_open if self.blink_open else self.config.avatar_closed

    def remaining_hhmmss(self) -> str:
        minutes, seconds = divmod(self.remaining_seconds, 60)
        return f"{minutes:02d}:{seconds:02d}"


class PomodoroConsoleApp:
    """Interfaz de consola para usar el timer con selección de tareas."""

    def __init__(
        self,
        base_dir: str = ".",
        event_log=None,
        entity_manager=None,
        current_week=None,
        current_day=None,
        input_fn=input,
        print_fn=print,
    ):
        self.base_dir = os.path.abspath(base_dir)
        self.config, self.config_path = load_timer_config(base_dir)
        self.engine = PomodoroTimerEngine(self.config)
        self.engine.set_session_completed_hook(self._register_session)
        self.session_log = []
        self._event_log = event_log
        self.input_fn = input_fn
        self.print_fn = print_fn

        self.manager = entity_manager
        if self.manager is None:
            data_dir = os.path.join(self.base_dir, "data")
            if os.path.isdir(data_dir):
                try:
                    from brackets.managers.entity_manager import EntityManager
                    self.manager = EntityManager(data_dir)
                except Exception:
                    self.manager = None

        self.current_week = current_week
        self.current_day = current_day
        if self.manager and (self.current_week is None or self.current_day is None):
            self._resolve_week_and_day()

    def _resolve_week_and_day(self) -> None:
        if not self.manager:
            return
        now = datetime.now()
        iso_year, iso_week, _ = now.isocalendar()
        today_day = now.day

        if not self.current_week:
            week = self.manager.load_week(iso_year, iso_week)
            if not week and hasattr(self.manager, "weeks_dir") and os.path.exists(self.manager.weeks_dir):
                import re
                week_files = sorted([f for f in os.listdir(self.manager.weeks_dir) if re.match(r'^\d{4}-W\d{2}\.yaml$', f)])
                if week_files:
                    last_fn = week_files[-1]
                    m = re.match(r'^(\d{4})-W(\d{2})\.yaml$', last_fn)
                    if m:
                        week = self.manager.load_week(int(m.group(1)), int(m.group(2)))

            if not week and self.manager.weeks:
                last_key = sorted(self.manager.weeks.keys())[-1]
                week = self.manager.weeks[last_key]
            self.current_week = week

        if not self.current_week or not self.current_week.days:
            return

        if not self.current_day:
            for d in self.current_week.days:
                if d.day_number == today_day:
                    self.current_day = d
                    return
            self.current_day = self.current_week.days[-1]

    def _sync_markdown_bitacora(self) -> None:
        if not self.manager or not self.current_week:
            return
        try:
            import glob
            from brackets.generators.bitacora_renderer import BitacoraRenderer
            from brackets.utils.legacy_utils import generate_filename

            pattern = f"*Week{self.current_week.week_number:02d}.md"
            existing = glob.glob(os.path.join(self.base_dir, pattern))
            if existing:
                md_path = existing[0]
            else:
                md_path = generate_filename(
                    year=self.current_week.year,
                    month=self.current_week.month,
                    week=self.current_week.week_number,
                    directory=self.base_dir
                )
            BitacoraRenderer.render_and_save_week(self.current_week, self.manager, md_path)
        except Exception:
            pass

    def _select_task_flow(self) -> None:
        """Permite al usuario seleccionar una tarea del día, de la semana o crear una nueva."""
        if not self.manager or not self.current_week:
            return

        if self.engine.active_task_id and self.engine.active_task_title:
            self.print_fn(f"\n🎯 Tarea actual: [{self.engine.active_task_id}] {self.engine.active_task_title}")
            keep = self.input_fn("¿Continuar con esta tarea? [S/n/c para cambiar]: ").strip().lower()
            if keep in ("", "s", "si", "y", "yes"):
                return

        self.print_fn("\n" + "=" * 55)
        self.print_fn("🎯 SELECCIONA LA TAREA EN LA QUE VAS A TRABAJAR")
        self.print_fn("=" * 55)

        options_map: Dict[str, Any] = {}
        counter = 1

        # 1. Tareas de HOY
        today_tasks = []
        if self.current_day:
            for tid in self.current_day.task_ids:
                t = self.manager.tasks.get(tid)
                if t:
                    today_tasks.append(t)

        if today_tasks:
            loc = f"{self.current_day.location_emoji or '📅'} Día {self.current_day.day_number}"
            self.print_fn(f"\n📋 Tareas de HOY ({loc}):")
            for t in today_tasks:
                chk = "[x]" if t.is_done else "[ ]"
                proj = f" [{t.project_id}]" if t.project_id else ""
                key = str(counter)
                options_map[key] = t
                self.print_fn(f"  [{key}] {chk} {t.title}{proj}")
                counter += 1
        else:
            self.print_fn("\n📋 Tareas de HOY: (sin tareas)")

        # 2. Tareas de la SEMANA (week tasks + topics pendientes)
        week_tasks = []
        if self.current_week:
            for tid in self.current_week.week_task_ids:
                t = self.manager.tasks.get(tid)
                if t and not t.is_done:
                    week_tasks.append(t)
            for tid in self.current_week.topics_task_ids:
                t = self.manager.tasks.get(tid)
                if t and not t.is_done and t not in week_tasks:
                    week_tasks.append(t)

        if week_tasks:
            self.print_fn("\n⏳ Tareas de la SEMANA (pendientes):")
            for t in week_tasks:
                proj = f" [{t.project_id}]" if t.project_id else ""
                key = str(counter)
                options_map[key] = t
                self.print_fn(f"  [{key}] [ ] {t.title}{proj}")
                counter += 1

        self.print_fn("\n⚙️ Opciones:")
        self.print_fn("  [n] ➕ Crear una nueva tarea")
        self.print_fn("  [0] ⏩ Sin tarea específica (Trabajo libre)")

        choice = self.input_fn("\nElige una opción: ").strip()

        if choice in options_map:
            chosen_task = options_map[choice]
            self.engine.set_active_task(
                task_id=chosen_task.id,
                project_id=chosen_task.project_id,
                title=chosen_task.title
            )
            # Si era una tarea de la semana y tenemos día activo, agendarla en hoy si no estaba
            if chosen_task in week_tasks and self.current_day and chosen_task.id not in self.current_day.task_ids:
                self.current_day.task_ids.append(chosen_task.id)
                self.manager.save_week(self.current_week)
                self._sync_markdown_bitacora()
            self.print_fn(f"✅ Tarea asignada: [{chosen_task.id}] {chosen_task.title}")
        elif choice.lower() in ("n", "nueva"):
            self._create_task_flow()
        else:
            self.engine.set_active_task(None, None, None)
            self.print_fn("ℹ️ Iniciando sin tarea específica (Trabajo libre).")

    def _create_task_flow(self) -> None:
        """Crea una nueva tarea y la asocia al foco actual."""
        self.print_fn("\n➕ NUEVA TAREA")
        title = self.input_fn("Título de la tarea: ").strip()
        if not title:
            self.print_fn("⚠️ Título vacío. Continuando sin tarea asociada.")
            self.engine.set_active_task(None, None, None)
            return

        proj = self.input_fn("Etiqueta de proyecto (opcional, ej: GENERAL): ").strip() or None
        day_num = self.current_day.day_number if self.current_day else None
        year = self.current_week.year if self.current_week else datetime.now().year
        week_num = self.current_week.week_number if self.current_week else datetime.now().isocalendar()[1]

        task = self.manager.create_task(
            title=title,
            year=year,
            week_num=week_num,
            day_number=day_num,
            project_id=proj
        )
        if self.current_day and task.id not in self.current_day.task_ids:
            self.current_day.task_ids.append(task.id)
            self.manager.save_week(self.current_week)

        self._sync_markdown_bitacora()

        self.engine.set_active_task(
            task_id=task.id,
            project_id=task.project_id,
            title=task.title
        )
        day_info = f" a hoy (Día {day_num})" if day_num else ""
        self.print_fn(f"✅ Tarea creada y asignada{day_info}: [{task.id}] {task.title}")

    def _register_session(self, record: Dict) -> None:
        self.session_log.append(record)
        if self._event_log:
            self._event_log.append(
                "pomodoro_complete",
                sessions_today=self.engine.completed_focus_sessions,
                focus_minutes=self.config.focus_minutes,
                workday_progress=record.get("workday_progress"),
                task_id=record.get("task_id"),
                project_id=record.get("project_id"),
            )

    def _progress_bar(self) -> str:
        width = max(8, self.config.progress_bar_width)
        ratio = self.engine.progress()
        completed = int(width * ratio)
        bar = "#" * completed + "-" * (width - completed)
        return f"[{bar}] {int(ratio * 100):3d}%"

    def _render_status_line(self) -> str:
        task_label = ""
        if self.engine.active_task_title:
            title = self.engine.active_task_title
            if len(title) > 28:
                title = title[:25] + "..."
            tid = f"[{self.engine.active_task_id}] " if self.engine.active_task_id else ""
            task_label = f" | 🎯 {tid}{title}"
        elif self.engine.phase == "focus":
            task_label = " | 🎯 Trabajo libre"

        return (
            f"{self.engine.avatar()} {self.engine.phase_label()} "
            f"{self._progress_bar()} ⏱ {self.engine.remaining_hhmmss()}{task_label}"
        )

    def _notify_phase_end(self, event: str) -> None:
        self.print_fn("\a", end="")
        if event == "focus_finished":
            self.print_fn("\n✅ Sesión de foco finalizada.")
        elif event == "break_finished":
            self.print_fn("\n☕ Descanso finalizado.")

    def _run_phase(self, phase: str) -> Optional[str]:
        if phase == "focus":
            self.engine.start_focus()
            if self._event_log:
                self._event_log.append(
                    "pomodoro_start",
                    focus_minutes=self.config.focus_minutes,
                    task_id=self.engine.active_task_id,
                    project_id=self.engine.active_project_id,
                )
        else:
            self.engine.start_break()

        event = None
        try:
            while self.engine.is_running:
                self.print_fn("\r" + self._render_status_line(), end="", flush=True)
                time.sleep(max(1, self.config.tick_seconds))
                event = self.engine.tick(self.config.tick_seconds)
            self.print_fn()
        except KeyboardInterrupt:
            self.engine.pause()
            self.print_fn("\n⏸ Sesión pausada por usuario (Ctrl+C).")
            return "paused"

        if event:
            self._notify_phase_end(event)
        return event

    def _show_summary(self) -> None:
        progress = int(self.engine.workday_progress() * 100)
        worked_minutes = self.engine.worked_seconds_today // 60
        self.print_fn("\n📊 RESUMEN DE JORNADA")
        self.print_fn("-" * 36)
        self.print_fn(f"Sesiones foco completadas: {self.engine.completed_focus_sessions}")
        self.print_fn(f"Tiempo de foco acumulado: {worked_minutes} min")
        self.print_fn(f"Progreso jornada: {progress}%")
        if self.engine.active_task_title:
            self.print_fn(f"Tarea activa: [{self.engine.active_task_id}] {self.engine.active_task_title}")
        if self.session_log:
            self.print_fn(f"Último registro: {self.session_log[-1]}")

    def _configure(self) -> None:
        self.print_fn("\n⚙️ CONFIGURAR TIMER")
        self.print_fn("(Enter mantiene valor actual)")

        def ask_int(label: str, current: int) -> int:
            raw = self.input_fn(f"{label} [{current}]: ").strip()
            if not raw:
                return current
            try:
                value = int(raw)
                return max(1, value)
            except ValueError:
                self.print_fn("Valor inválido, se mantiene el actual.")
                return current

        self.config.focus_minutes = ask_int("Minutos foco", self.config.focus_minutes)
        self.config.break_minutes = ask_int("Minutos descanso", self.config.break_minutes)
        self.config.workday_minutes = ask_int("Minutos jornada", self.config.workday_minutes)
        self.config.progress_bar_width = ask_int("Ancho barra progreso", self.config.progress_bar_width)
        self.config.tick_seconds = ask_int("Refresco en segundos", self.config.tick_seconds)

        avatar_open = self.input_fn(f"Avatar ojos abiertos [{self.config.avatar_open}]: ").strip()
        avatar_closed = self.input_fn(f"Avatar parpadeo [{self.config.avatar_closed}]: ").strip()
        if avatar_open:
            self.config.avatar_open = avatar_open
        if avatar_closed:
            self.config.avatar_closed = avatar_closed

        save_timer_config(self.config, self.config_path)
        self.engine.config = self.config
        self.print_fn(f"✅ Configuración guardada en: {self.config_path}")

    def run_menu(self) -> None:
        while True:
            self.print_fn("\n⏲️ POMODORO TIMER")
            self.print_fn("=" * 36)
            if self.engine.active_task_title:
                self.print_fn(f"🎯 Tarea actual: [{self.engine.active_task_id}] {self.engine.active_task_title}")
                self.print_fn("-" * 36)
            self.print_fn("1. ▶️ Iniciar sesión de foco")
            self.print_fn("2. ⏸ Pausar sesión actual")
            self.print_fn("3. ▶️ Reanudar sesión pausada")
            self.print_fn("4. ♻️ Reset sesión actual")
            self.print_fn("5. 🎯 Seleccionar / Cambiar tarea")
            self.print_fn("6. ⚙️ Configurar timer")
            self.print_fn("7. 📊 Ver resumen")
            self.print_fn("0. ↩️ Salir")

            choice = self.input_fn("Opción: ").strip()

            if choice == "1":
                self._select_task_flow()
                event = self._run_phase("focus")
                if event == "focus_finished":
                    # Si había una tarea activa pendiente, preguntar si completarla
                    if self.engine.active_task_id and self.manager:
                        task = self.manager.tasks.get(self.engine.active_task_id)
                        if task and task.is_pending:
                            mark_done = self.input_fn(f"\n¿Marcar tarea '{task.title}' como completada [x]? (s/N): ").strip().lower()
                            if mark_done in ("s", "si", "y", "yes"):
                                task.status = "done"
                                task.completed_at = datetime.now().strftime("%Y-%m-%d")
                                self.manager.save_task(task)
                                if self.current_week:
                                    self.manager.save_week(self.current_week)
                                    self._sync_markdown_bitacora()
                                self.print_fn(f"✅ Tarea [{task.id}] marcada como completada.")

                    auto_break = self.input_fn("¿Iniciar descanso ahora? (s/n): ").strip().lower()
                    if auto_break in ("s", "si", "y", "yes"):
                        self._run_phase("break")
            elif choice == "2":
                self.engine.pause()
                self.print_fn("⏸ Timer pausado.")
            elif choice == "3":
                if self.engine.is_paused:
                    self.engine.resume()
                    resumed_phase = self.engine.phase if self.engine.phase in ("focus", "break") else "focus"
                    self._run_phase(resumed_phase)
                else:
                    self.print_fn("ℹ️ No hay sesión pausada.")
            elif choice == "4":
                self.engine.reset()
                self.print_fn("♻️ Sesión reseteada.")
            elif choice in ("5", "t"):
                self.engine.set_active_task(None, None, None)
                self._select_task_flow()
            elif choice == "6":
                self._configure()
            elif choice == "7":
                self._show_summary()
            elif choice == "0":
                self.print_fn("👋 Saliendo del timer.")
                break
            else:
                self.print_fn("❌ Opción inválida")


def run_pomodoro_standalone(
    base_dir: str = ".",
    event_log=None,
    entity_manager=None,
    current_week=None,
    current_day=None,
    input_fn=input,
    print_fn=print,
) -> None:
    """Punto de entrada reutilizable para menú Brackets y modo standalone."""
    app = PomodoroConsoleApp(
        base_dir=base_dir,
        event_log=event_log,
        entity_manager=entity_manager,
        current_week=current_week,
        current_day=current_day,
        input_fn=input_fn,
        print_fn=print_fn,
    )
    app.run_menu()


if __name__ == "__main__":
    run_pomodoro_standalone()
