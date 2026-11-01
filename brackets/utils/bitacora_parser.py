#!/usr/bin/env python3
"""
Parser sintáctico para bitácoras semanales en formato Markdown.
Desacopla la interpretación de texto (secciones, tareas, notas, definiciones y metadatos)
de la lógica relacional y transaccional de la base de datos.
"""

from __future__ import annotations
import re
from typing import List, Dict, Tuple, Any, Optional

from brackets.models.task_types import TaskTypeRegistry


class BitacoraMarkdownParser:
    """Parsea el contenido Markdown de una bitácora semanal en estructuras semánticas puras."""

    @staticmethod
    def parse_task_status_and_title(raw_text: str, is_checkbox_done: bool) -> Tuple[str, str, str]:
        """
        Determina el estado ('done', 'cancelled', 'pending'), el título limpio y el tipo de tarea
        utilizando TaskTypeRegistry para detectar premojis o prefijos textuales como 'Reunión:'.
        """
        text = raw_text.strip()
        status = "pending"

        # Comprobar si contiene delimitadores de tachado ~~
        if "~~" in text:
            clean = text.replace("~~", "").strip()
            clean = re.sub(r'^\s*\[[ xX]?\]\s*', '', clean).strip()
            if clean:
                status = "cancelled"
                text = clean
        elif is_checkbox_done:
            status = "done"

        # Detectar tipo de tarea y limpiar premojis o prefijos
        task_type, clean_title = TaskTypeRegistry.detect_task_type_and_clean_title(text)

        return status, clean_title, task_type

    @staticmethod
    def parse_project_tag(raw_text: str) -> Tuple[Optional[str], str]:
        """
        Extrae un tag de proyecto (ej: #[PROJECT], [PROJECT] al inicio, o #PROJECT)
        y devuelve (project_id, clean_title).
        """
        clean = raw_text.strip()

        # 1. Hashtag explícito con corchetes: #[PROJ-CODE] o #[PROJ_CODE]
        m_hash = re.search(r'#\[([A-Za-z0-9_-]+)\]', clean)
        if m_hash:
            proj_id = m_hash.group(1).strip()
            clean = (clean[:m_hash.start()] + clean[m_hash.end():]).strip()
            clean = re.sub(r'\s{2,}', ' ', clean)
            return proj_id, clean

        # 2. Corchete al inicio: [PROJ-CODE] Texto... (descartando si tiene emojis de definición como 🎫, 🔗, etc.)
        m_lead = re.match(r'^\[([A-Za-z0-9_-]+)\]\s*(.*)$', clean)
        if m_lead:
            cand = m_lead.group(1).strip()
            if len(cand) > 1 and not re.search(r'[🎫🦒🤖📺📂📁🔗📊🛠️]', cand):
                proj_id = cand
                clean = m_lead.group(2).strip()
                return proj_id, clean

        # 3. Hashtag simple al final: Texto... #PROJ_CODE
        m_simple = re.search(r'(?:^|\s)#([A-Z0-9_-]{2,})\b', clean)
        if m_simple:
            proj_id = m_simple.group(1).strip()
            clean = (clean[:m_simple.start()] + clean[m_simple.end():]).strip()
            clean = re.sub(r'\s{2,}', ' ', clean)
            return proj_id, clean

        return None, clean

    @classmethod
    def parse_sections(cls, content: str) -> Dict[str, Any]:
        """Trocea el documento Markdown en sus secciones semánticas."""
        lines = content.splitlines()
        current_section = None
        current_day_num = None

        topics_lines: List[str] = []
        week_tasks_lines: List[Tuple[str, str, str]] = []
        notes_raw_lines: List[str] = []
        days: Dict[int, List[Tuple[str, str, str]]] = {}
        days_meta: Dict[int, Dict[str, Any]] = {}
        definitions_lines: List[Tuple[str, str]] = []
        last_task_info = None

        for line in lines:
            stripped = line.strip()

            # Detectar encabezados nivel 2
            if stripped.startswith("## "):
                header = stripped[3:].strip()
                if "Topics" in header or "🎯" in header:
                    current_section = "topics"
                    current_day_num = None
                    continue
                elif "Week Tasks" in header or "Weekly Tasks" in header or "📋" in header or "Tareas" in header:
                    current_section = "week_tasks"
                    current_day_num = None
                    continue
                elif "Notes" in header or "📝" in header:
                    current_section = "notes"
                    current_day_num = None
                    continue
                elif "Definicion" in header or "🔗" in header:
                    current_section = "definitions"
                    current_day_num = None
                    continue
                elif "✅" in header:
                    # Legacy header "## ✅Topics"
                    current_section = "week_tasks"
                    current_day_num = None
                    continue
                else:
                    last_task_info = None
                    # Buscar número de día en el encabezado (ej: "🏠24", "🚗 25", "26", "🛠️29 (Intervención)")
                    match = re.search(r'\b(\d{1,2})\b', header)
                    if match:
                        current_section = "day"
                        current_day_num = int(match.group(1))
                        days.setdefault(current_day_num, [])

                        # Extraer emoji si existe antes o junto al número (incluyendo variation selectors como \ufe0f)
                        emoji_match = re.search(r'^([^\w\s\d()]+?)\s*\b\d{1,2}\b', header)
                        emoji = emoji_match.group(1).strip() if emoji_match else "🏠"

                        # Extraer nota entre paréntesis si existe
                        note_match = re.search(r'\(([^)]+)\)', header)
                        note = note_match.group(1).strip() if note_match else None

                        days_meta[current_day_num] = {
                            "emoji": emoji,
                            "note": note
                        }
                        continue
                    else:
                        current_section = None
                        current_day_num = None
                        continue

            if not stripped or stripped.startswith("---"):
                continue

            # Detectar sección de definiciones al pie
            if "<!--" in stripped and "definicion" in stripped.lower():
                current_section = "definitions"
                current_day_num = None
                continue

            # Detectar formato de definición Markdown [id]: url (en cualquier parte o bajo <!-- Definiciones -->)
            m_def = re.match(r'^\s*(\[[^\]\n]+\]):\s*(\S.*)$', line)
            if m_def:
                d_id = m_def.group(1).strip()
                d_url = m_def.group(2).strip()
                definitions_lines.append((d_id, d_url))
                continue

            # Normalizar líneas con tachado exterior tipo "~~- [ ] Tarea~~" o "~~- Tarea~~"
            norm_line = line
            stripped_line = stripped
            if stripped_line.startswith("~~-") and stripped_line.endswith("~~") and len(stripped_line) >= 5:
                lead_spaces = line[:len(line) - len(line.lstrip())]
                inner = stripped_line[2:-2].strip()
                m_inner = re.match(r'^-\s*(?:\[([ xX])\])?\s*(.*)$', inner)
                if m_inner:
                    chk = m_inner.group(1) or " "
                    body = m_inner.group(2)
                    norm_line = f"{lead_spaces}- [{chk}] ~~{body}~~"
                else:
                    norm_line = f"{lead_spaces}- ~~{inner[1:].strip()}~~"

            if current_section == "topics":
                last_task_info = None
                m_chk = re.match(r'^\s*-\s*\[([ xX])\]\s*(.*)$', norm_line)
                if m_chk:
                    t_text = m_chk.group(2).strip()
                    if t_text:
                        status, clean_title, task_type = cls.parse_task_status_and_title(t_text, m_chk.group(1).lower() == 'x')
                        week_tasks_lines.append([status, clean_title, task_type, None])
                        last_task_info = (week_tasks_lines, len(week_tasks_lines) - 1, len(norm_line) - len(norm_line.lstrip()))
                else:
                    m_item = re.match(r'^\s*-\s*(.*)$', norm_line)
                    if m_item:
                        t_text = m_item.group(1).strip()
                        if t_text and not t_text.startswith("---"):
                            topics_lines.append(t_text)
            elif current_section == "week_tasks":
                m = re.match(r'^(\s*)-\s*\[([ xX])\]\s*(.*)$', norm_line)
                if m:
                    base_indent = len(m.group(1))
                    t_text = m.group(3).strip()
                    if t_text:
                        status, clean_title, task_type = cls.parse_task_status_and_title(t_text, m.group(2).lower() == 'x')
                        week_tasks_lines.append([status, clean_title, task_type, None])
                        last_task_info = (week_tasks_lines, len(week_tasks_lines) - 1, base_indent)
                elif (last_task_info is not None 
                      and (len(norm_line) - len(norm_line.lstrip()) >= last_task_info[2] + 2)
                      and (len(norm_line) - len(norm_line.lstrip()) >= 4)
                      and not re.search(r'\[[ xX]?\]', norm_line)
                      and norm_line.strip().startswith(("- ", "* "))):
                    sub_m = re.match(r'^\s*[-*]\s*(.*)$', norm_line)
                    desc_text = sub_m.group(1).strip() if sub_m else norm_line.strip()
                    if desc_text:
                        t_list, t_idx, _ = last_task_info
                        if t_list[t_idx][3]:
                            t_list[t_idx][3] += f"\n{desc_text}"
                        else:
                            t_list[t_idx][3] = desc_text
                elif norm_line.strip().startswith("- "):
                    m_dash = re.match(r'^(\s*)-\s*(.*)$', norm_line)
                    base_indent = len(m_dash.group(1)) if m_dash else 0
                    t_text = norm_line.strip()[2:].strip()
                    if t_text:
                        status, clean_title, task_type = cls.parse_task_status_and_title(t_text, False)
                        week_tasks_lines.append([status, clean_title, task_type, None])
                        last_task_info = (week_tasks_lines, len(week_tasks_lines) - 1, base_indent)
                else:
                    last_task_info = None
            elif current_section == "notes":
                last_task_info = None
                notes_raw_lines.append(line)
            elif current_section == "day" and current_day_num is not None:
                m = re.match(r'^(\s*)-\s*\[([ xX])\]\s*(.*)$', norm_line)
                if m:
                    base_indent = len(m.group(1))
                    t_text = m.group(3).strip()
                    if t_text:
                        status, clean_title, task_type = cls.parse_task_status_and_title(t_text, m.group(2).lower() == 'x')
                        days[current_day_num].append([status, clean_title, task_type, None])
                        last_task_info = (days[current_day_num], len(days[current_day_num]) - 1, base_indent)
                elif (last_task_info is not None 
                      and (len(norm_line) - len(norm_line.lstrip()) >= last_task_info[2] + 2)
                      and (len(norm_line) - len(norm_line.lstrip()) >= 4)
                      and not re.search(r'\[[ xX]?\]', norm_line)
                      and norm_line.strip().startswith(("- ", "* "))):
                    sub_m = re.match(r'^\s*[-*]\s*(.*)$', norm_line)
                    desc_text = sub_m.group(1).strip() if sub_m else norm_line.strip()
                    if desc_text:
                        t_list, t_idx, _ = last_task_info
                        if t_list[t_idx][3]:
                            t_list[t_idx][3] += f"\n{desc_text}"
                        else:
                            t_list[t_idx][3] = desc_text
                elif norm_line.strip().startswith("- "):
                    m_dash = re.match(r'^(\s*)-\s*(.*)$', norm_line)
                    base_indent = len(m_dash.group(1)) if m_dash else 0
                    t_text = norm_line.strip()[2:].strip()
                    if t_text:
                        status, clean_title, task_type = cls.parse_task_status_and_title(t_text, False)
                        days[current_day_num].append([status, clean_title, task_type, None])
                        last_task_info = (days[current_day_num], len(days[current_day_num]) - 1, base_indent)
                else:
                    last_task_info = None

        # Parsear bloques de notas a partir de notes_raw_lines
        notes_blocks = cls.parse_notes_blocks(notes_raw_lines)

        week_tasks_tuples = [tuple(item) if isinstance(item, list) else item for item in week_tasks_lines]
        days_tuples = {
            d: [tuple(item) if isinstance(item, list) else item for item in items]
            for d, items in days.items()
        }

        return {
            "topics": topics_lines,
            "week_tasks": week_tasks_tuples,
            "notes_blocks": notes_blocks,
            "days": days_tuples,
            "days_meta": days_meta,
            "definitions": definitions_lines
        }

    @staticmethod
    def parse_notes_blocks(raw_lines: List[str]) -> List[Dict[str, Any]]:
        """Extrae bloques de notas con subencabezados (### Título o - ### Título) y sus viñetas."""
        blocks: List[Dict[str, Any]] = []
        current_title = None
        current_proj = None
        current_bullets: List[str] = []

        for line in raw_lines:
            stripped = line.strip()
            if stripped.startswith("### ") or stripped.startswith("- ### "):
                if current_title or current_bullets:
                    blocks.append({
                        "title": current_title,
                        "project_id": current_proj,
                        "content": current_bullets
                    })
                if stripped.startswith("- ### "):
                    header = stripped[6:].strip()
                else:
                    header = stripped[4:].strip()

                # Extraer proyecto si está presente como [PROJ] Título
                p_match = re.match(r'^\[([A-Za-z0-9_-]+)\]\s*(.*)$', header)
                if p_match:
                    current_proj = p_match.group(1).strip()
                    current_title = p_match.group(2).strip()
                else:
                    current_proj = None
                    current_title = header
                current_bullets = []
            elif stripped.startswith("- "):
                bullet = stripped[2:].strip()
                if bullet:
                    current_bullets.append(bullet)

        if current_title or current_bullets:
            blocks.append({
                "title": current_title,
                "project_id": current_proj,
                "content": current_bullets
            })

        return blocks
