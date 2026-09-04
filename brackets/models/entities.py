#!/usr/bin/env python3
"""
Modelos de Entidad para la Arquitectura Relacional YAML-First de Brackets.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any


@dataclass
class Project:
    """Entidad Proyecto para agrupar tareas, notas y referencias."""
    id: str  # ej: "AMR_LOGISTICS", "ROVO_AI"
    name: str  # ej: "Amr Logistics"
    description: Optional[str] = None
    status: str = "active"  # "active", "completed", "archived"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Project:
        return cls(
            id=data.get("id", ""),
            name=data.get("name", data.get("id", "")),
            description=data.get("description"),
            status=data.get("status", "active")
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Idea:
    """Entidad Idea / Propuesta para evaluar, aterrizar o descartar."""
    id: str  # ej: "IDEA-0001"
    title: str  # Título / Concepto de la idea
    content: List[str] = field(default_factory=list)  # Líneas de detalle o hipótesis
    status: str = "evaluating"  # "evaluating", "accepted", "discarded"
    created_at: str = ""  # "YYYY-MM-DD"
    project_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Idea:
        content_raw = data.get("content", [])
        if isinstance(content_raw, str):
            content_list = [content_raw]
        else:
            content_list = list(content_raw)

        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            content=content_list,
            status=data.get("status", "evaluating"),
            created_at=data.get("created_at", ""),
            project_id=data.get("project_id")
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Definition:
    """Entidad Definición / Enlace externo (Jira, Confluence, etc.)."""
    id: str  # ej: "🎫ATLM-12682" o "🦒EXPORT"
    url: str  # ej: "https://mangospain.atlassian.net/browse/ATLM-12682"
    title: Optional[str] = None
    type: str = "jira"  # "jira", "link", "custom"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Definition:
        return cls(
            id=data.get("id", ""),
            url=data.get("url", ""),
            title=data.get("title"),
            type=data.get("type", "jira")
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Topic:
    """Entidad Topic / Tema general de trabajo enmarcado en un proyecto."""
    id: str  # ej: "TOP-0001"
    title: str  # Título / descripción general del topic
    project_id: str  # Proyecto obligatorio al que pertenece
    status: str = "active"  # "active", "completed", "archived"
    created_at: str = ""  # "YYYY-MM-DD"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Topic:
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            project_id=data.get("project_id", ""),
            status=data.get("status", "active"),
            created_at=data.get("created_at", "")
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RecurringTask:
    """Definición de tarea o reunión recurrente."""
    id: str  # ej: "REC-0001"
    title: str  # ej: "Daily S^3"
    recurrence_type: str = "weekly_days"  # "weekly_days", "interval_weeks", "week_tasks"
    days_of_week: List[int] = field(default_factory=list)  # [0, 2, 4] para L, X, V (0=Lunes...6=Domingo)
    interval_weeks: int = 1  # cada N semanas (ej: 4)
    base_week: int = 1  # semana base para calcular módulo
    day_of_week: int = 4  # Para interval_weeks: 0=Lunes, 4=Viernes, etc.
    project_id: Optional[str] = None
    topic_id: Optional[str] = None
    active: bool = True
    created_at: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RecurringTask:
        raw_days = data.get("days_of_week", [])
        if isinstance(raw_days, (int, str)):
            days_list = [int(raw_days)]
        else:
            days_list = [int(x) for x in raw_days]

        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            recurrence_type=data.get("recurrence_type", "weekly_days"),
            days_of_week=days_list,
            interval_weeks=int(data.get("interval_weeks", 1)),
            base_week=int(data.get("base_week", 1)),
            day_of_week=int(data.get("day_of_week", 4)),
            project_id=data.get("project_id"),
            topic_id=data.get("topic_id"),
            active=data.get("active", True),
            created_at=data.get("created_at", "")
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Task:
    """Entidad Tarea independiente con trazabilidad temporal."""
    id: str
    title: str
    status: str = "pending"  # "pending", "done", "cancelled"
    created_at: str = ""  # "YYYY-MM-DD"
    completed_at: Optional[str] = None
    project_id: Optional[str] = None
    topic_id: Optional[str] = None
    recurring_id: Optional[str] = None

    @property
    def is_done(self) -> bool:
        return self.status.lower() == "done"

    @property
    def is_cancelled(self) -> bool:
        return self.status.lower() == "cancelled"

    @property
    def is_pending(self) -> bool:
        return self.status.lower() == "pending"

    @property
    def is_recurring(self) -> bool:
        return self.recurring_id is not None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Task:
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            status=data.get("status", "pending"),
            created_at=data.get("created_at", ""),
            completed_at=data.get("completed_at"),
            project_id=data.get("project_id"),
            topic_id=data.get("topic_id"),
            recurring_id=data.get("recurring_id")
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Note:
    """Entidad Nota de trabajo estructurada con título y viñetas de contenido."""
    id: str
    title: Optional[str] = None
    content: List[str] = field(default_factory=list)  # Líneas o viñetas de la nota
    created_at: str = ""
    month: Optional[str] = None  # "YYYY-MM", ej: "2026-02"
    week: Optional[int] = None
    project_id: Optional[str] = None
    topic_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Note:
        content_raw = data.get("content", [])
        if isinstance(content_raw, str):
            content_list = [content_raw]
        else:
            content_list = list(content_raw)
        
        proj_id = data.get("project_id") or data.get("project_ref")
        return cls(
            id=data.get("id", ""),
            title=data.get("title"),
            content=content_list,
            created_at=data.get("created_at", ""),
            month=data.get("month"),
            week=data.get("week"),
            project_id=proj_id,
            topic_id=data.get("topic_id")
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DaySchedule:
    """Configuración de un día dentro de la bitácora semanal."""
    day_number: int  # 17, 18, 19, etc.
    location_emoji: str = "🏠"  # 🏠, 🚗, 🏖️
    location_note: Optional[str] = None  # "Oficina", "Vacaciones"
    task_ids: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DaySchedule:
        return cls(
            day_number=int(data.get("day_number", 0)),
            location_emoji=data.get("location_emoji", "🏠"),
            location_note=data.get("location_note"),
            task_ids=data.get("task_ids", [])
        )

    @property
    def is_intervention(self) -> bool:
        """Indica si el día es de intervención, guardia o soporte especial fuera de rutina."""
        if self.location_emoji in ("🛠️", "🚨", "🔧", "⚡"):
            return True
        if self.location_note:
            note_lower = self.location_note.lower()
            if any(term in note_lower for term in ("intervenci", "guardia", "soporte", "on-call", "oncall")):
                return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WeekSchedule:
    """Estructura de calendario semanal que referencia las entidades de datos."""
    year: int
    month: int
    week_number: int
    weight: Optional[float] = None
    topic_ids: List[str] = field(default_factory=list)
    week_task_ids: List[str] = field(default_factory=list)
    note_ids: List[str] = field(default_factory=list)
    days: List[DaySchedule] = field(default_factory=list)
    topics_task_ids: List[str] = field(default_factory=list)  # Compatibilidad legacy

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WeekSchedule:
        days_data = [DaySchedule.from_dict(d) for d in data.get("days", [])]
        raw_topic_ids = data.get("topic_ids") or data.get("topics_ids") or []
        raw_week_tasks = data.get("week_task_ids") or data.get("weekly_task_ids") or []
        legacy_topics = data.get("topics_task_ids", [])

        # Si no había week_task_ids pero sí topics_task_ids legacy, inicializar
        if not raw_week_tasks and legacy_topics:
            raw_week_tasks = list(legacy_topics)

        return cls(
            year=int(data.get("year", 0)),
            month=int(data.get("month", 0)),
            week_number=int(data.get("week_number", 0)),
            weight=data.get("weight"),
            topic_ids=list(raw_topic_ids),
            week_task_ids=list(raw_week_tasks),
            note_ids=data.get("note_ids", []),
            days=days_data,
            topics_task_ids=list(legacy_topics)
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "year": self.year,
            "month": self.month,
            "week_number": self.week_number,
            "weight": self.weight,
            "topic_ids": self.topic_ids,
            "week_task_ids": self.week_task_ids,
            "note_ids": self.note_ids,
            "days": [d.to_dict() for d in self.days],
            "topics_task_ids": self.week_task_ids
        }
