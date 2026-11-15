import os
import shutil
import tempfile
import unittest
from datetime import datetime
from worklog.log4brackets import Log4Brackets, get_logger
from managers.entity_manager import EntityManager
from modules.pomodoro_timer import PomodoroTimerEngine, TimerConfig

class TestLog4Brackets(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.data_dir = os.path.join(self.test_dir, "data")
        os.makedirs(self.data_dir, exist_ok=True)
        self.logger = Log4Brackets(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_single_line_format(self):
        line = self.logger.log_task_created(
            task_id="TSK-0001",
            project_id="PROJ_A",
            title="Tarea de prueba\ncon salto de linea",
            day_number=15
        )
        self.assertNotIn("\n", line)
        self.assertTrue(line.startswith("["))
        self.assertIn("[INFO]", line)
        self.assertIn("[TASK]", line)
        self.assertIn("created", line)
        self.assertIn("id=TSK-0001", line)
        self.assertIn("project=PROJ_A", line)
        self.assertIn("day=15", line)

    def test_monthly_file_partitioning(self):
        dt_jan = datetime(2026, 1, 15, 10, 0, 0)
        dt_feb = datetime(2026, 2, 20, 11, 30, 0)

        self.logger.log_task_created("TSK-0001", "PROJ_A", "Tarea de Enero", ts=dt_jan)
        self.logger.log_task_created("TSK-0002", "PROJ_B", "Tarea de Febrero", ts=dt_feb)

        jan_log = os.path.join(self.test_dir, "data", "log", "2026-01.log")
        feb_log = os.path.join(self.test_dir, "data", "log", "2026-02.log")

        self.assertTrue(os.path.exists(jan_log))
        self.assertTrue(os.path.exists(feb_log))

        with open(jan_log, "r", encoding="utf-8") as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 1)
        self.assertIn("Tarea de Enero", lines[0])

        with open(feb_log, "r", encoding="utf-8") as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 1)
        self.assertIn("Tarea de Febrero", lines[0])

    def test_pomodoro_logging(self):
        dt = datetime(2026, 8, 30, 14, 0, 0)
        line = self.logger.log_pomodoro(
            task_id="TSK-0100",
            project_id="KOERBER_E2E",
            duration_min=25,
            action="focus_completed",
            ts=dt
        )
        self.assertIn("[POMODORO]", line)
        self.assertIn("task=TSK-0100", line)
        self.assertIn("project=KOERBER_E2E", line)
        self.assertIn("duration=25m", line)

    def test_entity_manager_integration(self):
        em = EntityManager(self.data_dir)
        task = em.create_task("Nueva tarea desde EM", project_id="TEST_PROJ")
        em.toggle_task(task.id)

        log_file = os.path.join(self.test_dir, "data", "log", f"{datetime.now().year:04d}-{datetime.now().month:02d}.log")
        self.assertTrue(os.path.exists(log_file))

        with open(log_file, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("created", content)
        self.assertIn(task.id, content)
        self.assertIn("completed", content)

    def test_pomodoro_engine_integration(self):
        config = TimerConfig(focus_minutes=1, break_minutes=1)
        engine = PomodoroTimerEngine(config)
        engine.set_active_task("TSK-9999", "TEST_PROJ")
        engine.start_focus()
        event = engine.tick(engine.phase_total_seconds)
        self.assertEqual(event, "focus_finished")

if __name__ == "__main__":
    unittest.main()