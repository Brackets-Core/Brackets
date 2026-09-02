#!/usr/bin/env python3
"""Tests básicos del módulo pomodoro_timer."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from brackets.modules.pomodoro_timer import TimerConfig, PomodoroTimerEngine


class TestPomodoroTimer:
    def __init__(self):
        self.passed = 0
        self.failed = 0

    def _ok(self, name: str):
        print(f"✅ Test: {name}")
        self.passed += 1

    def _fail(self, name: str, error: Exception):
        print(f"❌ Test {name} falló: {error}")
        self.failed += 1

    def test_start_pause_resume_reset(self):
        name = "start/pause/resume/reset"
        try:
            cfg = TimerConfig(focus_minutes=1, break_minutes=1, workday_minutes=10)
            engine = PomodoroTimerEngine(cfg)

            engine.start_focus()
            assert engine.is_running is True
            assert engine.phase == "focus"

            engine.pause()
            assert engine.is_paused is True

            engine.resume()
            assert engine.is_paused is False

            engine.reset()
            assert engine.phase == "idle"
            assert engine.is_running is False
            assert engine.remaining_seconds == 0
            self._ok(name)
        except Exception as e:
            self._fail(name, e)

    def test_tick_and_finish_focus(self):
        name = "tick finaliza foco"
        try:
            cfg = TimerConfig(focus_minutes=1, break_minutes=1, workday_minutes=10)
            engine = PomodoroTimerEngine(cfg)
            events = []
            engine.set_session_completed_hook(lambda rec: events.append(rec))

            engine.start_focus()
            for _ in range(60):
                event = engine.tick(1)

            assert event == "focus_finished"
            assert engine.completed_focus_sessions == 1
            assert len(events) == 1
            assert events[0]["phase"] == "focus"
            self._ok(name)
        except Exception as e:
            self._fail(name, e)

    def test_progress_bounds(self):
        name = "progress en rango"
        try:
            cfg = TimerConfig(focus_minutes=1, break_minutes=1, workday_minutes=2)
            engine = PomodoroTimerEngine(cfg)

            engine.start_focus()
            p0 = engine.progress()
            assert 0.0 <= p0 <= 1.0

            for _ in range(30):
                engine.tick(1)
            p1 = engine.progress()
            assert p1 > p0
            assert 0.0 <= p1 <= 1.0
            self._ok(name)
        except Exception as e:
            self._fail(name, e)

    def test_active_task_association(self):
        name = "asociación de tarea al motor y registro"
        try:
            cfg = TimerConfig(focus_minutes=1, break_minutes=1, workday_minutes=10)
            engine = PomodoroTimerEngine(cfg)
            engine.set_active_task("TSK-0001", "GENERAL", "Revisar logs")

            assert engine.active_task_id == "TSK-0001"
            assert engine.active_project_id == "GENERAL"
            assert engine.active_task_title == "Revisar logs"

            engine.start_focus()
            for _ in range(60):
                engine.tick(1)

            assert engine.last_session_record is not None
            assert engine.last_session_record["task_id"] == "TSK-0001"
            assert engine.last_session_record["task_title"] == "Revisar logs"
            self._ok(name)
        except Exception as e:
            self._fail(name, e)

    def test_console_app_select_today_task(self):
        name = "selección de tarea del día en consola"
        import tempfile, shutil
        from brackets.modules.pomodoro_timer import PomodoroConsoleApp
        from brackets.managers.entity_manager import EntityManager
        from brackets.models.entities import DaySchedule, WeekSchedule

        tmp = tempfile.mkdtemp()
        try:
            mgr = EntityManager(os.path.join(tmp, "data"))
            week = WeekSchedule(year=2026, week_number=35, month=8, days=[
                DaySchedule(day_number=24, location_emoji="🏠", task_ids=[])
            ])
            mgr.save_week(week)
            task = mgr.create_task("Tarea Día 24", year=2026, week_num=35, day_number=24, project_id="TEST")

            inputs = ["1"] # Selecciona tarea 1 (del día)
            prints = []

            app = PomodoroConsoleApp(
                base_dir=tmp,
                entity_manager=mgr,
                current_week=week,
                current_day=week.days[0],
                input_fn=lambda p="": inputs.pop(0),
                print_fn=lambda *a, **k: prints.append(" ".join(str(x) for x in a))
            )

            app._select_task_flow()
            assert app.engine.active_task_id == task.id
            assert app.engine.active_task_title == "Tarea Día 24"
            assert app.engine.active_project_id == "TEST"
            self._ok(name)
        except Exception as e:
            self._fail(name, e)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_console_app_create_new_task(self):
        name = "creación de nueva tarea en selector de foco"
        import tempfile, shutil
        from brackets.modules.pomodoro_timer import PomodoroConsoleApp
        from brackets.managers.entity_manager import EntityManager
        from brackets.models.entities import DaySchedule, WeekSchedule

        tmp = tempfile.mkdtemp()
        try:
            mgr = EntityManager(os.path.join(tmp, "data"))
            week = WeekSchedule(year=2026, week_number=35, month=8, days=[
                DaySchedule(day_number=24, location_emoji="🏠", task_ids=[])
            ])
            mgr.save_week(week)

            inputs = [
                "n",                    # Opción crear nueva
                "Tarea Creada En Foco", # Título
                "PROJ_FOCO"             # Proyecto
            ]
            prints = []

            app = PomodoroConsoleApp(
                base_dir=tmp,
                entity_manager=mgr,
                current_week=week,
                current_day=week.days[0],
                input_fn=lambda p="": inputs.pop(0),
                print_fn=lambda *a, **k: prints.append(" ".join(str(x) for x in a))
            )

            app._select_task_flow()
            assert app.engine.active_task_title == "Tarea Creada En Foco"
            assert app.engine.active_project_id == "PROJ_FOCO"
            assert app.engine.active_task_id in week.days[0].task_ids

            # Verificar que la bitácora Markdown se ha sincronizado en disco y contiene la tarea
            import glob
            md_files = glob.glob(os.path.join(tmp, "*Week35.md"))
            with open(md_files[0], "r", encoding="utf-8") as f:
                md_content = f.read()
            assert "Tarea Creada En Foco" in md_content
            self._ok(name)
        except Exception as e:
            self._fail(name, e)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def run_all(self):
        print("\n🧪 TESTS: modules/pomodoro_timer.py")
        print("=" * 50)
        self.test_start_pause_resume_reset()
        self.test_tick_and_finish_focus()
        self.test_progress_bounds()
        self.test_active_task_association()
        self.test_console_app_select_today_task()
        self.test_console_app_create_new_task()
        print(f"\n📊 Resultado: ✅ {self.passed} | ❌ {self.failed}")
        return self.failed == 0


if __name__ == "__main__":
    tester = TestPomodoroTimer()
    success = tester.run_all()
    sys.exit(0 if success else 1)
