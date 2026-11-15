#!/usr/bin/env python3
"""
Tests unitarios para NoteCrudController y los métodos CRUD de notas en EntityManager.
"""

import os
import shutil
import tempfile
import unittest
from managers.entity_manager import EntityManager
from models.entities import WeekSchedule, DaySchedule
from core.note_crud_controller import NoteCrudController


class TestCoreNoteCrudController(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.data_dir = os.path.join(self.tmp_dir, "data")
        self.entity_manager = EntityManager(self.data_dir)
        self.entity_manager.ensure_project("ALPHA", name="Project Alpha")
        self.entity_manager.ensure_project("BETA", name="Project Beta")

        # Crear semana base de prueba
        self.week = WeekSchedule(
            year=2026,
            month=8,
            week_number=35,
            days=[DaySchedule(day_number=24, location_emoji="🏠", location_note=None, task_ids=[])],
            topics_task_ids=[],
            note_ids=[]
        )
        self.entity_manager.save_week(self.week)
        self.output_lines = []

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _mock_print(self, *args, **kwargs):
        self.output_lines.append(" ".join(str(a) for a in args))

    # -------------------------------------------------------------------------
    # Tests de EntityManager (Capa de Negocio)
    # -------------------------------------------------------------------------
    def test_entity_manager_note_crud_lifecycle(self):
        """Verifica el ciclo completo de alta, consulta, actualización y baja en EntityManager."""
        # 1. Alta
        note = self.entity_manager.add_note(
            title="Reunión Inicial",
            content=["Punto 1", "Punto 2"],
            project_id="ALPHA",
            year=2026,
            week_num=35
        )
        self.assertIsNotNone(note.id)
        self.assertEqual(note.title, "Reunión Inicial")
        self.assertEqual(note.project_id, "ALPHA")
        self.assertEqual(len(note.content), 2)
        self.assertIn(note.id, self.week.note_ids)

        # 2. Consulta y Búsqueda
        found_alpha = self.entity_manager.list_notes(project_id="ALPHA")
        self.assertEqual(len(found_alpha), 1)

        search_res = self.entity_manager.search_notes(query="Punto 1")
        self.assertEqual(len(search_res), 1)
        self.assertEqual(search_res[0].id, note.id)

        # 3. Modificación
        updated = self.entity_manager.update_note(
            note_id=note.id,
            title="Reunión Inicial Modificada",
            content=["Nuevo Punto A", "Nuevo Punto B", "Nuevo Punto C"],
            project_id="BETA"
        )
        self.assertEqual(updated.title, "Reunión Inicial Modificada")
        self.assertEqual(updated.project_id, "BETA")
        self.assertEqual(len(updated.content), 3)

        # Verificar persistencia recargando EntityManager desde disco
        reloaded_mgr = EntityManager(self.data_dir)
        reloaded_note = reloaded_mgr.notes.get(note.id)
        self.assertIsNotNone(reloaded_note)
        self.assertEqual(reloaded_note.title, "Reunión Inicial Modificada")
        self.assertEqual(reloaded_note.project_id, "BETA")
        self.assertEqual(len(reloaded_note.content), 3)

        # 4. Baja
        deleted = reloaded_mgr.delete_note_complete(note.id)
        self.assertTrue(deleted)
        self.assertNotIn(note.id, reloaded_mgr.notes)

        # Verificar que se borró del disco
        reloaded_mgr_2 = EntityManager(self.data_dir)
        self.assertNotIn(note.id, reloaded_mgr_2.notes)

    # -------------------------------------------------------------------------
    # Tests de NoteCrudController (Capa Interactiva)
    # -------------------------------------------------------------------------
    def test_controller_create_new_note(self):
        """Simula crear una nota desde NoteCrudController."""
        inputs = [
            "Arquitectura del Sistema",  # Título
            "Diseño relacional",         # Viñeta 1
            "Renderizado unificado",     # Viñeta 2
            "",                          # Fin de viñetas
            "1",                         # Seleccionar proyecto ALPHA
            ""                           # Enter confirmación
        ]

        controller = NoteCrudController(
            entity_manager=self.entity_manager,
            current_week=self.week,
            vault_root=self.tmp_dir,
            input_fn=lambda _: inputs.pop(0),
            print_fn=self._mock_print
        )

        note = controller.create_new_note()
        self.assertIsNotNone(note)
        self.assertEqual(note.title, "Arquitectura del Sistema")
        self.assertEqual(note.project_id, "ALPHA")
        self.assertEqual(len(note.content), 2)

    def test_controller_create_new_note(self):
        """Simula crear una nota desde NoteCrudController."""
        inputs = [
            "Arquitectura del Sistema",  # Título
            "Diseño relacional",         # Viñeta 1
            "Renderizado unificado",     # Viñeta 2
            "",                          # Fin de viñetas
            "1",                         # Seleccionar proyecto ALPHA
            ""                           # Enter confirmación
        ]

        controller = NoteCrudController(
            entity_manager=self.entity_manager,
            current_week=self.week,
            vault_root=self.tmp_dir,
            input_fn=lambda _: inputs.pop(0),
            print_fn=self._mock_print
        )

        note = controller.create_new_note()
        self.assertIsNotNone(note)
        self.assertEqual(note.title, "Arquitectura del Sistema")
        self.assertEqual(note.project_id, "ALPHA")
        self.assertEqual(len(note.content), 2)

    def test_controller_edit_existing_note_scoped_to_week(self):
        """Simula editar una nota añadiendo viñetas directamente y luego cambiando metadatos opcionalmente."""
        note = self.entity_manager.add_note(
            title="Nota Base",
            content=["Viñeta 1"],
            project_id="ALPHA",
            year=2026,
            week_num=35
        )

        inputs = [
            "1",               # Seleccionar directamente la nota 1 de la semana activa
            "Viñeta Extra",    # Viñeta añadida directamente al final
            "",                # Fin de viñetas
            "s",               # ¿Modificar título o proyecto? Sí
            "Nota Editada",    # Nuevo título
            "2",               # Seleccionar proyecto BETA
            ""                 # Enter confirmación
        ]

        controller = NoteCrudController(
            entity_manager=self.entity_manager,
            current_week=self.week,
            vault_root=self.tmp_dir,
            input_fn=lambda _: inputs.pop(0),
            print_fn=self._mock_print
        )

        updated = controller.edit_existing_note()
        self.assertIsNotNone(updated)
        self.assertEqual(updated.title, "Nota Editada")
        self.assertEqual(updated.project_id, "BETA")
        self.assertEqual(len(updated.content), 2)
        self.assertEqual(updated.content[1], "Viñeta Extra")

    def test_controller_delete_note_scoped_to_week(self):
        """Simula eliminar una nota de la semana activa seleccionándola directamente."""
        note = self.entity_manager.add_note(
            title="Nota a Borrar",
            content=["Contenido"],
            project_id="ALPHA",
            year=2026,
            week_num=35
        )

        inputs = [
            "1",              # Seleccionar nota 1 de la semana
            "s",              # Confirmar borrado
            ""                # Enter confirmación
        ]

        controller = NoteCrudController(
            entity_manager=self.entity_manager,
            current_week=self.week,
            vault_root=self.tmp_dir,
            input_fn=lambda _: inputs.pop(0),
            print_fn=self._mock_print
        )

        res = controller.delete_note()
        self.assertTrue(res)
        self.assertNotIn(note.id, self.entity_manager.notes)

    def test_controller_query_notes_scoped_default(self):
        """Simula consultar notas en modo acotado (semana actual por defecto)."""
        self.entity_manager.add_note(
            title="Nota Semana Actual",
            content=["Detalle"],
            year=2026,
            week_num=35
        )

        inputs = [
            "1",  # Notas de la semana actual por defecto
            ""    # Enter continuar
        ]

        controller = NoteCrudController(
            entity_manager=self.entity_manager,
            current_week=self.week,
            vault_root=self.tmp_dir,
            input_fn=lambda _: inputs.pop(0),
            print_fn=self._mock_print
        )

        notes = controller.query_notes()
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0].title, "Nota Semana Actual")

    def test_controller_run_exit(self):
        """Simula abrir el menú CRUD y salir inmediatamente con '0'."""
        inputs = ["0"]
        controller = NoteCrudController(
            entity_manager=self.entity_manager,
            current_week=self.week,
            vault_root=self.tmp_dir,
            input_fn=lambda _: inputs.pop(0),
            print_fn=self._mock_print
        )
        res = controller.run()
        self.assertEqual(res, "back")


if __name__ == "__main__":
    unittest.main()
