#!/usr/bin/env python3
"""
Consolidador de archivos de un mes específico.
Refactorizado para usar BaseConsolidator y configuración centralizada.
"""

import os
import re
from typing import List, Tuple, Optional
from datetime import datetime

# Importaciones de nueva arquitectura
from brackets.core.base_consolidator import BaseConsolidator
from brackets.utils.file_finder import FileFinder
from brackets.utils.legacy_utils import safe_file_read, safe_file_write
from brackets.config import MONTH_NAMES, SEASON_EMOJIS, WORKING_DIRECTORY


class MonthConsolidator(BaseConsolidator):
    """Consolidador de archivos de un mes específico."""
    
    def __init__(self, directory: str = "."):
        super().__init__(directory)
        self.finder = FileFinder(directory)
    
    def get_season_emoji(self, month: int) -> str:
        """Obtiene el emoji de la estación según el mes."""
        for months, emoji in SEASON_EMOJIS.items():
            if month in months:
                return emoji
        return "📅"
    
    def get_files_for_month(self, year: int, month: int) -> Tuple[List[str], Optional[str], Optional[str]]:
        """
        Obtiene todos los archivos de un mes específico.
        Retorna: (weekly_files, monthly_topics_file, year_topics_file)
        """
        # Buscar archivos semanales
        weekly_files = []
        
        for file in os.listdir(self.directory):
            if re.match(rf'\[{year}\]\[{month:02d}\]Week\d{{2}}\.md', file):
                filepath = os.path.join(self.directory, file)
                # Extraer número de semana para ordenar
                match = re.search(r'Week(\d{2})', file)
                if match:
                    week_num = int(match.group(1))
                    weekly_files.append((filepath, week_num))
        
        # Ordenar por número de semana (descendente para orden inverso)
        weekly_files.sort(key=lambda x: x[1], reverse=True)
        weekly_files = [f[0] for f in weekly_files]
        
        # Buscar archivo mensual
        monthly_file = None
        monthly_pattern = f"[{year}][{month:02d}]MonthTopics.md"
        monthly_path = os.path.join(self.directory, monthly_pattern)
        if os.path.exists(monthly_path):
            monthly_file = monthly_path
        
        # Buscar archivo de año
        year_file = None
        year_pattern = f"[{year}][00]YearTopics.md"
        year_path = os.path.join(self.directory, year_pattern)
        if os.path.exists(year_path):
            year_file = year_path
        
        return weekly_files, monthly_file, year_file
    
    def delete_source_files(self, weekly_files: List[str], monthly_file: Optional[str], force: bool = False) -> bool:
        """Borra los archivos origen después de confirmar."""
        files_to_delete = weekly_files.copy()
        if monthly_file:
            files_to_delete.append(monthly_file)

        if not files_to_delete:
            return True

        if force or self.confirm_deletion(files_to_delete, "archivo"):
            self.delete_files_confirmed(files_to_delete)
            return True
        else:
            print("\n↩️  Operación de borrado cancelada")
            return False

    @staticmethod
    def _extract_and_strip_definitions(content: str) -> Tuple[str, dict]:
        """Extrae el bloque <!-- Definiciones --> y devuelve el contenido limpio junto a las definiciones."""
        defs = {}
        lines = content.split('\n')
        cleaned_lines = []
        in_defs = False
        for line in lines:
            stripped = line.strip()
            if (stripped.startswith("## ") and "definicion" in stripped.lower()) or ("<!--" in stripped and "definicion" in stripped.lower()):
                in_defs = True
                continue
            m = re.match(r'^\s*(\[[^\]\n]+\]):\s*(\S.*)$', line)
            if m:
                defs[m.group(1).strip()] = m.group(2).strip()
                continue
            if in_defs and not stripped:
                continue
            in_defs = False
            cleaned_lines.append(line)
        return '\n'.join(cleaned_lines), defs

    def consolidate(self, year: int, month: int) -> bool:
        """
        Consolida todos los archivos de un mes en un único archivo.
        El orden es inverso: semanas de mayor a menor.
        """
        return self.consolidate_month(year, month)
    
    def consolidate_month(
        self,
        year: int,
        month: int,
        interactive: bool = True,
        delete_source: bool = False
    ) -> bool:
        """
        Consolida todos los archivos y datos de un mes en un único archivo ejecutivo.
        El orden es inverso: semanas de mayor a menor.
        """
        print(f"\n🔍 Buscando archivos para {year}-{month:02d}...")
        
        weekly_files, monthly_file, year_file = self.get_files_for_month(year, month)
        
        if not weekly_files and not monthly_file:
            print(f"❌ No se encontraron archivos para {year}-{month:02d}")
            return False
        
        # Verificar si el consolidado ya existe
        output_filename = f"[{year}][{month:02d}].md"
        output_path = os.path.join(self.directory, output_filename)
        
        if os.path.exists(output_path) and interactive:
            action = self.handle_existing_output(output_filename)
            
            if action == 'delete_only':
                # Solo borrar archivos origen
                return self.delete_source_files(weekly_files, monthly_file)
            elif action != 'regenerate':
                print("\n↩️  Operación cancelada")
                return False
            # Si es 'regenerate', continúa con la regeneración
        
        print(f"\n📁 Archivos encontrados:")
        if monthly_file:
            print(f"  - Temas mensuales: {os.path.basename(monthly_file)}")
        for wf in weekly_files:
            print(f"  - {os.path.basename(wf)}")
        
        # Crear contenido consolidado
        season_emoji = self.get_season_emoji(month)
        month_name = MONTH_NAMES.get(month, f'Mes {month:02d}')
        
        content_parts = []
        
        # Encabezado principal
        content_parts.append(f"# {season_emoji} {month_name} - {year}")
        content_parts.append("")
        content_parts.append(f"> 📊 Consolidado Ejecutivo del mes {month:02d}/{year}")
        content_parts.append(f"> Generado el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        content_parts.append("")
        content_parts.append("---")
        content_parts.append("")
        
        # 1. Agregar temas mensuales si existe
        if monthly_file:
            content_parts.append("## 📋 Temas Mensuales")
            content_parts.append("")
            monthly_content = safe_file_read(monthly_file)
            if monthly_content:
                lines = monthly_content.split('\n')
                content_without_title = '\n'.join(lines[1:]).strip()
                content_parts.append(content_without_title)
                content_parts.append("")
                content_parts.append("---")
                content_parts.append("")

        # 2. SECCIÓN EJECUTIVA: LOGROS DEL MES (TAREAS COMPLETADAS POR PROYECTO)
        tasks_file = os.path.join(self.directory, "data", "tables", "tasks.yaml")
        tasks_done_this_month = []
        if os.path.exists(tasks_file):
            try:
                import yaml
                with open(tasks_file, "r", encoding="utf-8") as f:
                    tdata = yaml.safe_load(f)
                all_tasks = tdata.get("tasks", [])
                month_prefix = f"{year}-{month:02d}"
                tasks_done_this_month = [
                    t for t in all_tasks
                    if t.get("status") == "done" and str(t.get("completed_at", "")).startswith(month_prefix)
                ]
            except Exception:
                pass

        if tasks_done_this_month:
            content_parts.append("## 🏆 Logros del Mes (Tareas Completadas)")
            content_parts.append("")
            from collections import defaultdict
            by_proj = defaultdict(list)
            for t in tasks_done_this_month:
                proj = t.get("project_id") or "POR_ASIGNAR"
                by_proj[proj].append(t)

            for proj, tlist in sorted(by_proj.items(), key=lambda x: -len(x[1])):
                content_parts.append(f"### 📂 {proj} ({len(tlist)} tareas resueltas)")
                for t in sorted(tlist, key=lambda x: str(x.get("completed_at", ""))):
                    d_str = t.get("completed_at")
                    d_suffix = f" _(Resuelta el {d_str})_" if d_str else ""
                    content_parts.append(f"  - [x] {t['title']}{d_suffix}")
                content_parts.append("")
            content_parts.append("---")
            content_parts.append("")

        # 3. SECCIÓN EJECUTIVA: DECISIONES Y NOTAS CLAVE DEL MES
        notes_file = os.path.join(self.directory, "data", "tables", "notes", f"{year}-{month:02d}.yaml")
        if os.path.exists(notes_file):
            try:
                import yaml
                with open(notes_file, "r", encoding="utf-8") as f:
                    ndata = yaml.safe_load(f)
                notes = ndata.get("notes", [])
                if notes:
                    content_parts.append("## 📝 Decisiones y Notas Clave")
                    content_parts.append("")
                    for n in notes:
                        title = n.get("title") or "Nota"
                        content_parts.append(f"### {title}")
                        for item in n.get("content", []):
                            content_parts.append(f"  - {item}")
                        content_parts.append("")
                    content_parts.append("---")
                    content_parts.append("")
            except Exception:
                pass

        # 4. MÉTRICAS Y LOG DEL MES
        log_file = os.path.join(self.directory, "data", "log", f"{year}-{month:02d}.log")
        if os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    log_lines = f.readlines()
                pomodoros = sum(1 for l in log_lines if "[POMODORO]" in l)
                tasks_created = sum(1 for l in log_lines if "[TASK] created" in l)
                content_parts.append("## ⏱️ Registro de Actividad")
                content_parts.append(f"- **Eventos registrados en el mes:** {len(log_lines)}")
                content_parts.append(f"- **Nuevas tareas registradas:** {tasks_created}")
                content_parts.append(f"- **Tareas completadas:** {len(tasks_done_this_month)}")
                if pomodoros > 0:
                    content_parts.append(f"- **Sesiones Pomodoro de foco:** {pomodoros}")
                content_parts.append("")
                content_parts.append("---")
                content_parts.append("")
            except Exception:
                pass

        # 5. SEMANAS CONSOLIDADAS (en orden inverso, ya están ordenadas)
        all_month_definitions: dict = {}
        if weekly_files:
            content_parts.append("## 🗓️ Bitácoras Semanales del Mes")
            content_parts.append("")
            for i, weekly_file in enumerate(weekly_files, 1):
                match = re.search(r'Week(\d{2})', os.path.basename(weekly_file))
                week_num = match.group(1) if match else "??"

                content_parts.append(f"### 🗓️ Semana {week_num}")
                content_parts.append("")

                weekly_content = safe_file_read(weekly_file)
                if weekly_content:
                    cleaned_weekly_content, defs = self._extract_and_strip_definitions(weekly_content)
                    all_month_definitions.update(defs)

                    adjusted_content = self.adjust_markdown_headings(cleaned_weekly_content, skip_first_line=True)
                    content_parts.append(adjusted_content.strip())
                    content_parts.append("")
                    content_parts.append("---")
                    content_parts.append("")

        # 6. DEFINICIONES DEL MES (unificadas y deduplicadas al pie)
        if all_month_definitions:
            content_parts.append("## Definiciones")
            content_parts.append("<!-- Definiciones -->")
            for def_id, url in sorted(all_month_definitions.items()):
                content_parts.append(f"{def_id}: {url}")
            content_parts.append("")

        # Escribir archivo consolidado
        final_content = '\n'.join(content_parts)

        if safe_file_write(output_path, final_content):
            print(f"\n✅ Archivo consolidado creado: {output_filename}")
            print(f"📍 Ruta: {output_path}")

            # Registrar en log4brackets si está disponible
            try:
                from brackets.worklog.log4brackets import log4brackets
                log4brackets.log_consolidation(year, month, output_filename)
            except Exception:
                pass

            # Eliminar archivos origen: por defecto Sí al consolidar/compactar
            if interactive:
                delete = input("\n🗑️  ¿Deseas eliminar las bitácoras semanales consolidadas? (S/n): ").strip().lower()
                if delete not in ['n', 'no']:
                    self.delete_source_files(weekly_files, monthly_file, force=True)
            elif delete_source:
                self.delete_source_files(weekly_files, monthly_file, force=True)

            return True
        else:
            print(f"\n❌ Error al crear el archivo consolidado")
            return False

    def get_consolidated_months_with_source_files(self) -> List[Tuple[int, int, List[str]]]:
        """Encuentra meses que ya tienen su archivo consolidado [YYYY][MM].md pero conservan bitácoras semanales."""
        result = []
        for file in os.listdir(self.directory):
            m = re.match(r'^\[(\d{4})\]\[(\d{2})\]\.md$', file)
            if m:
                year = int(m.group(1))
                month = int(m.group(2))
                weekly_files, monthly_file, _ = self.get_files_for_month(year, month)
                files_to_clean = weekly_files.copy()
                if monthly_file:
                    files_to_clean.append(monthly_file)
                if files_to_clean:
                    result.append((year, month, files_to_clean))
        result.sort(key=lambda x: (x[0], x[1]))
        return result

    def cleanup_consolidated_source_files(
        self,
        year: Optional[int] = None,
        month: Optional[int] = None,
        interactive: bool = True
    ) -> int:
        """
        Elimina bitácoras semanales correspondientes a meses que ya han sido consolidados.
        """
        pending_cleanup = self.get_consolidated_months_with_source_files()
        if year and month:
            pending_cleanup = [item for item in pending_cleanup if item[0] == year and item[1] == month]

        if not pending_cleanup:
            print("✅ No hay bitácoras semanales de meses ya consolidados pendientes de borrar.")
            return 0

        total_deleted = 0
        print(f"\n🧹 LIMPIEZA DE BITÁCORAS DE MESES YA CONSOLIDADOS")
        print("=" * 55)
        for y, m, flist in pending_cleanup:
            print(f"  📅 Mes {y}-{m:02d}: {len(flist)} archivo(s) semanal(es)")
            for f in flist:
                print(f"     • {os.path.basename(f)}")

        if interactive:
            resp = input(f"\n⚠️ ¿Deseas eliminar estas bitácoras ya consolidadas? (S/n): ").strip().lower()
            if resp in ['n', 'no']:
                print("↩️  Operación cancelada.")
                return 0

        for _, _, flist in pending_cleanup:
            total_deleted += self.delete_files_confirmed(flist)

        print(f"\n✅ Se han eliminado {total_deleted} bitácoras semanales ya consolidadas.")
        return total_deleted

    def list_available_months(self) -> List[Tuple[int, int]]:
        """Lista todos los meses disponibles con archivos."""
        months_set = set()

        # Buscar todos los archivos de semanas y meses
        for file in os.listdir(self.directory):
            # Buscar patrón [YYYY][MM]
            match = re.match(r'\[(\d{4})\]\[(\d{2})\](?:Week\d{2}|MonthTopics)\.md', file)
            if match:
                year = int(match.group(1))
                month = int(match.group(2))
                if month > 0:  # Excluir el archivo [00]YearTopics
                    months_set.add((year, month))

        # Ordenar por año y mes (descendente)
        return sorted(list(months_set), reverse=True)

    def interactive_consolidate(self) -> bool:
        """Modo interactivo para consolidar un mes."""
        print("\n📦 CONSOLIDAR ARCHIVOS DE UN MES")
        print("=" * 40)

        consolidated_with_sources = self.get_consolidated_months_with_source_files()
        if consolidated_with_sources:
            print("🧹 Meses previamente consolidados con bitácoras semanales a limpiar:")
            for y, m, flist in consolidated_with_sources:
                print(f"  • {y}-{m:02d}: {len(flist)} bitácoras semanales")
            print("  (Escribe 'c' o 'clean' para limpiar estas bitácoras)")
            print("-" * 40)

        available_months = self.list_available_months()

        if not available_months and not consolidated_with_sources:
            print("❌ No se encontraron archivos de bitácoras para consolidar")
            return False

        if available_months:
            print("\nMeses pendientes de consolidar:")
            print("-" * 30)

            for i, (year, month) in enumerate(available_months, 1):
                month_name = MONTH_NAMES.get(month, f'Mes {month:02d}')
                print(f"{i:2d}. {year}-{month:02d} ({month_name})")

            print("\nO ingresa manualmente (formato: YYYY-MM)")
            print("-" * 30)

        choice = input("\nSelecciona opción (número, YYYY-MM o 'c' para limpiar ya consolidados): ").strip().lower()
        if choice in ('c', 'clean', 'limpiar'):
            return bool(self.cleanup_consolidated_source_files(interactive=True))

        year, month = None, None

        # Intentar como número de lista
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(available_months):
                year, month = available_months[choice_num - 1]
        except ValueError:
            # Intentar como formato YYYY-MM
            match = re.match(r'(\d{4})-(\d{2})', choice)
            if match:
                year = int(match.group(1))
                month = int(match.group(2))

        if year and month and 1 <= month <= 12:
            return self.consolidate_month(year, month)
        else:
            print("❌ Selección inválida")
            return False


def main():
    """Función principal para pruebas."""
    consolidator = MonthConsolidator()
    consolidator.interactive_consolidate()


if __name__ == "__main__":
    main()
