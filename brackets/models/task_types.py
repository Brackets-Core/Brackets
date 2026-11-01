"""Registro extensible de tipos de tareas y premojis para Brackets.

Permite definir premojis (prefijos de emoji) y prefijos textuales para clasificar
automáticamente tipos de tareas (como reuniones) tanto en la edición Markdown
como en el renderizado de bitácoras y el Daily Hub interactivo.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class TaskTypeSpec:
    """Especificación de un tipo de tarea con su premoji y prefijos reconocidos."""
    key: str = ""                                               # Identificador único (ej: 'meeting', 'task')
    label: str = ""                                             # Etiqueta legible (ej: 'Reunión', 'Tarea')
    premoji: str = ""                                           # Premoji oficial (ej: '🫱🏼‍🫲🏽')
    text_prefixes: List[str] = field(default_factory=list)      # Prefijos de texto (ej: ['reunión:', 'reunion:'])
    emoji_aliases: List[str] = field(default_factory=list)      # Emojis equivalentes (ej: ['🤝', '🫱🏼‍🫲🏽'])
    name: str = ""                                              # Alias para key
    aliases: List[str] = field(default_factory=list)            # Alias para emoji_aliases

    def __post_init__(self):
        if not self.key and self.name:
            self.key = self.name
        elif not self.name and self.key:
            self.name = self.key
        if not self.emoji_aliases and self.aliases:
            self.emoji_aliases = list(self.aliases)
        elif not self.aliases and self.emoji_aliases:
            self.aliases = list(self.emoji_aliases)


# Premoji oficial para reunión: handshake multirracial con ZWJ
MEETING_PREMOJI = "\U0001faf1\U0001f3fc\u200d\U0001faf2\U0001f3fd"

DEFAULT_TASK_TYPES_YAML = """# =============================================================================
# Tipos de Tareas y Premojis de Brackets
# =============================================================================
# Configuración modular de tipos de tareas sin tocar código Python.
#
# Campos disponibles por cada tipo:
#   key: Identificador único en base de datos (tasks.yaml). Ej: meeting, bug, spike
#   label: Nombre descriptivo legible (para menús y reportes). Ej: Reunión
#   premoji: Emoji oficial que se antepondrá en el archivo .md y en el Daily Hub
#   text_prefixes: Prefijos textuales que al escribirse a mano en el .md se detectan
#                  automáticamente y se convierten en este tipo y premoji
#   emoji_aliases: Lista de emojis equivalentes que también se reconocerán
# =============================================================================

task_types:
  - key: meeting
    label: Reunión
    premoji: "🫱🏼‍🫲🏽"
    text_prefixes:
      - "reunión:"
      - "reunion:"
      - "reunión :"
      - "reunion :"
    emoji_aliases:
      - "🫱🏼‍🫲🏽"
      - "🫱🏼🫲🏽"
      - "🤝"

  - key: task
    label: Tarea
    premoji: ""
    text_prefixes: []
    emoji_aliases: []

# -----------------------------------------------------------------------------
# Ejemplos de nuevos tipos que puedes descomentar o personalizar:
# -----------------------------------------------------------------------------
#  - key: bug
#    label: Incidencia / Bug
#    premoji: "🐛"
#    text_prefixes:
#      - "bug:"
#      - "error:"
#      - "fix:"
#    emoji_aliases:
#      - "🐛"
#      - "🐞"
#
#  - key: spike
#    label: Investigación
#    premoji: "🔬"
#    text_prefixes:
#      - "spike:"
#      - "investigar:"
#    emoji_aliases:
#      - "🔬"
#      - "🧪"
#
#  - key: call
#    label: Llamada rápida
#    premoji: "📞"
#    text_prefixes:
#      - "call:"
#      - "llamada:"
#    emoji_aliases:
#      - "📞"
#      - "📲"
"""


class TaskTypeRegistry:
    """Catálogo central y extensible de tipos de tareas."""

    _specs: Dict[str, TaskTypeSpec] = {}

    @classmethod
    def register(cls, spec: TaskTypeSpec) -> None:
        """Registra o actualiza una especificación de tipo de tarea."""
        cls._specs[spec.key] = spec

    # Alias para compatibilidad de registro
    register_type = register

    @classmethod
    def get_spec(cls, key: str) -> Optional[TaskTypeSpec]:
        """Obtiene la especificación de un tipo de tarea."""
        return cls._specs.get(key)

    @classmethod
    def get_all_specs(cls) -> List[TaskTypeSpec]:
        """Devuelve la lista de todas las especificaciones registradas."""
        return list(cls._specs.values())

    get_all = get_all_specs

    @classmethod
    def get_all_specs_dict(cls) -> Dict[str, TaskTypeSpec]:
        """Devuelve un diccionario con todas las especificaciones registradas indexadas por su clave."""
        return cls._specs.copy()

    @classmethod
    def get_premoji(cls, key: str) -> str:
        """Obtiene el premoji representativo de un tipo de tarea."""
        spec = cls.get_spec(key)
        return spec.premoji if spec else ""

    @classmethod
    def reset_to_defaults(cls) -> None:
        """Restablece el catálogo a los tipos esenciales por defecto."""
        cls._specs.clear()
        cls.register(
            TaskTypeSpec(
                key="meeting",
                label="Reunión",
                premoji=MEETING_PREMOJI,
                text_prefixes=["reunión:", "reunion:", "reunión :", "reunion :"],
                emoji_aliases=[
                    MEETING_PREMOJI,
                    "\U0001faf1\U0001f3fc\U0001faf2\U0001f3fd",
                    "🤝",
                    "\U0001f91d"
                ]
            )
        )
        cls.register(
            TaskTypeSpec(
                key="task",
                label="Tarea",
                premoji="",
                text_prefixes=[],
                emoji_aliases=[]
            )
        )

    @classmethod
    def load_from_yaml(cls, yaml_path: Optional[str] = None) -> bool:
        """
        Carga las especificaciones de tipos de tareas desde un archivo YAML.
        Si yaml_path no existe, crea el archivo con la plantilla por defecto y ejemplos.
        """
        import yaml

        target_path = yaml_path
        if not target_path:
            # Buscar en ubicaciones habituales
            for cand in ["data/task_types.yaml", "../data/task_types.yaml"]:
                if os.path.exists(cand):
                    target_path = cand
                    break

        if not target_path:
            return False

        target_abs = os.path.abspath(target_path)

        if not os.path.exists(target_abs):
            try:
                os.makedirs(os.path.dirname(target_abs), exist_ok=True)
                with open(target_abs, "w", encoding="utf-8") as f:
                    f.write(DEFAULT_TASK_TYPES_YAML)
            except Exception:
                pass

        if os.path.exists(target_abs):
            try:
                with open(target_abs, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                raw_list = data.get("task_types", [])
                if isinstance(raw_list, list) and raw_list:
                    for item in raw_list:
                        if isinstance(item, dict):
                            key = item.get("key") or item.get("name") or ""
                            if not key:
                                continue
                            spec = TaskTypeSpec(
                                key=key,
                                label=item.get("label") or key.capitalize(),
                                premoji=item.get("premoji") or "",
                                text_prefixes=item.get("text_prefixes") or [],
                                emoji_aliases=item.get("emoji_aliases") or item.get("aliases") or []
                            )
                            cls.register(spec)
                    # Asegurar fallback de 'task'
                    if "task" not in cls._specs:
                        cls.register(TaskTypeSpec(key="task", label="Tarea", premoji=""))
                    return True
            except Exception:
                return False
        return False

    @classmethod
    def detect_task_type_and_clean_title(cls, raw_text: str) -> Tuple[str, str]:
        """
        Analiza el texto de una tarea para detectar si coincide con algún tipo registrado
        a través de sus premojis o prefijos de texto. Devuelve (task_type, clean_title).
        """
        text = raw_text.strip()

        # Comprobar contra cada tipo registrado (excluyendo 'task' que es el fallback)
        for key, spec in cls._specs.items():
            if key == "task":
                continue

            # 1. Comprobar prefijos de texto (ej: 'Reunión:', 'reunion:')
            for prefix in spec.text_prefixes:
                # Regex flexible para prefijo (case-insensitive, con o sin espacio tras dos puntos)
                pattern = rf'^{re.escape(prefix)}\s*'
                m = re.match(pattern, text, flags=re.IGNORECASE)
                if m:
                    clean = text[m.end():].strip()
                    # Si tras el prefijo textual había un premoji, limpiarlo también
                    all_emojis = sorted(
                        list(set(spec.emoji_aliases + ([spec.premoji] if spec.premoji else []))),
                        key=len,
                        reverse=True
                    )
                    for alias in all_emojis:
                        if clean.startswith(alias):
                            clean = clean[len(alias):].strip()
                    # Limpiar variaciones regex de handshake si es reunión
                    if key == "meeting":
                        clean = re.sub(
                            r'^([\U0001f91d]|[\U0001faf1-\U0001faf2][\U0001f3fb-\U0001f3ff]?\s*(?:\u200d\s*)?[\U0001faf1-\U0001faf2]?[\U0001f3fb-\U0001f3ff]?)\s*',
                            '',
                            clean
                        ).strip()
                    return key, clean

            # 2. Comprobar premojis y emojis equivalentes (ej: '🫱🏼‍🫲🏽', '🤝')
            all_emojis = sorted(
                list(set(spec.emoji_aliases + ([spec.premoji] if spec.premoji else []))),
                key=len,
                reverse=True
            )
            for emoji in all_emojis:
                if text.startswith(emoji):
                    clean = text[len(emoji):].strip()
                    # Si tras el emoji había un prefijo textual redundante, limpiarlo
                    for prefix in spec.text_prefixes:
                        m_sub = re.match(rf'^{re.escape(prefix)}\s*', clean, flags=re.IGNORECASE)
                        if m_sub:
                            clean = clean[m_sub.end():].strip()
                    return key, clean

            # 3. Regex especial para variaciones de apretón de manos con tonos de piel en reuniones
            if key == "meeting":
                # Detecta secuencias de handshake con/sin ZWJ (\u200d) y modificadores de piel
                m_hand = re.match(
                    r'^([\U0001f91d]|[\U0001faf1-\U0001faf2][\U0001f3fb-\U0001f3ff]?\s*(?:\u200d\s*)?[\U0001faf1-\U0001faf2]?[\U0001f3fb-\U0001f3ff]?)\s*',
                    text
                )
                if m_hand:
                    clean = text[m_hand.end():].strip()
                    # Limpiar prefijo textual si viene después ej "🫱🏼‍🫲🏽 Reunión: Foo"
                    for prefix in spec.text_prefixes:
                        m_sub = re.match(rf'^{re.escape(prefix)}\s*', clean, flags=re.IGNORECASE)
                        if m_sub:
                            clean = clean[m_sub.end():].strip()
                    return key, clean

        return "task", text

    @classmethod
    def format_title_with_premoji(cls, title: str, task_type: str) -> str:
        """
        Formatea el título anteponiendo el premoji si el tipo de tarea lo define.
        Evita duplicar el premoji si el título ya lo contiene.
        """
        clean_title = title.strip()
        spec = cls.get_spec(task_type)
        if not spec or not spec.premoji:
            return clean_title

        # Comprobar si ya empieza con el premoji o alguno de sus alias
        all_emojis = sorted(
            list(set(spec.emoji_aliases + [spec.premoji])),
            key=len,
            reverse=True
        )
        for emoji in all_emojis:
            if clean_title.startswith(emoji):
                clean_title = clean_title[len(emoji):].strip()

        # Si es reunión, limpiar también cualquier residuo regex de handshake
        if task_type == "meeting":
            clean_title = re.sub(
                r'^([\U0001f91d]|[\U0001faf1-\U0001faf2][\U0001f3fb-\U0001f3ff]?\s*(?:\u200d\s*)?[\U0001faf1-\U0001faf2]?[\U0001f3fb-\U0001f3ff]?)\s*',
                '',
                clean_title
            ).strip()

        return f"{spec.premoji} {clean_title}"


# Inicializar tipos por defecto
TaskTypeRegistry.reset_to_defaults()
