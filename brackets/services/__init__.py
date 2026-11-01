#!/usr/bin/env python3
"""
Capa de Servicios de Dominio (Service Layer) para Brackets.
"""

from brackets.services.recurring_task_service import RecurringTaskService
from brackets.services.task_deduplication_service import TaskDeduplicationService

__all__ = [
    "RecurringTaskService",
    "TaskDeduplicationService",
]
