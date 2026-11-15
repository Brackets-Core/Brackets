"""Módulo de funcionalidades específicas - Proyectos, aprendizaje, etc."""

# Placeholder para futuras funcionalidades (FASE 3+)
# from modules.holidays import HolidayManager
# from modules.projects import ProjectManager
# from modules.learning import LearningManager

from modules.pomodoro_timer import (
	TimerConfig,
	PomodoroTimerEngine,
	PomodoroConsoleApp,
	run_pomodoro_standalone,
)

__all__ = [
	"TimerConfig",
	"PomodoroTimerEngine",
	"PomodoroConsoleApp",
	"run_pomodoro_standalone",
]
