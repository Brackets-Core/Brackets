#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests unitarios para el motor de mascota Pomodoro (Tomatín).
Totalmente desacoplado de la interfaz gráfica.
"""

import unittest
from brackets.modules.pomodoro_pet_engine import (
    PetEmotion,
    PetStateMachine,
    TOMATIN_SPRITES,
    SLIME_SPRITES,
    COLOR_PALETTE,
    EMOTION_DIALOGUES,
)


class TestPomodoroPetEngine(unittest.TestCase):
    """Test suite para PetStateMachine y sprites de Tomatín."""

    def setUp(self):
        self.pet = PetStateMachine(pet_name="Tomatín")

    def test_initial_state_is_idle(self):
        self.assertEqual(self.pet.emotion, PetEmotion.IDLE)
        self.assertEqual(self.pet.frame_index, 0)
        self.assertIn("¿Listo para concentrarte?", self.pet.get_current_dialogue())

    def test_sprite_dimensions_and_colors(self):
        """Verifica que todos los sprites de Tomatín sean cuadrículas válidas de 20x20 con colores conocidos."""
        for emotion, frames in TOMATIN_SPRITES.items():
            self.assertGreaterEqual(len(frames), 2, f"La emoción {emotion} debe tener al menos 2 frames")
            for frame_idx, frame in enumerate(frames):
                self.assertEqual(len(frame), 20, f"Frame {frame_idx} de {emotion} debe tener 20 filas")
                for row_idx, row in enumerate(frame):
                    self.assertEqual(len(row), 20, f"Fila {row_idx} en {emotion} frame {frame_idx} debe tener 20 cols")
                    for char in row:
                        self.assertIn(char, COLOR_PALETTE, f"Carácter '{char}' desconocido en paleta")

    def test_slime_sprites_alias_compatibility(self):
        """Verifica que SLIME_SPRITES sea un alias compatible hacia TOMATIN_SPRITES."""
        self.assertIs(SLIME_SPRITES, TOMATIN_SPRITES)
        for emotion in PetEmotion:
            self.assertIn(emotion, SLIME_SPRITES)

    def test_palette_contains_tomatin_key_colors(self):
        """Verifica que la paleta incluya los colores clave de Tomatín (rojo, sombra, hojas, rubor, outline)."""
        # Contorno pixel negro bien definido
        self.assertEqual(COLOR_PALETTE["#"], "#111111")
        # Rojo tomate cuerpo
        self.assertEqual(COLOR_PALETTE["R"], "#E63946")
        # Rojo sombra inferior
        self.assertEqual(COLOR_PALETTE["r"], "#9B111E")
        # Rojo brillo suave
        self.assertEqual(COLOR_PALETTE["L"], "#FF6B7A")
        # Verde hoja y tallo
        self.assertEqual(COLOR_PALETTE["g"], "#38B000")
        self.assertEqual(COLOR_PALETTE["G"], "#226F00")
        # Rubor kawaii mejillas
        self.assertEqual(COLOR_PALETTE["P"], "#FF8FA3")
        # Blanco ojos / texto / vapor
        self.assertEqual(COLOR_PALETTE["W"], "#FFFFFF")
        # Verde fósforo terminal LCD / Zzz
        self.assertEqual(COLOR_PALETTE["Z"], "#39FF14")
        # Laptop azul / nube
        self.assertEqual(COLOR_PALETTE["B"], "#23A8F2")
        # Café / taza
        self.assertEqual(COLOR_PALETTE["C"], "#8B5E3C")

    def test_state_transitions(self):
        """Verifica cambios de emoción según eventos del timer."""
        # Inicio de foco -> FOCUS
        self.pet.handle_timer_event("focus_started")
        self.assertEqual(self.pet.emotion, PetEmotion.FOCUS)
        self.assertIn("¡Concéntrate, tú puedes!", self.pet.get_current_dialogue())

        # Pausa -> SLEEP
        self.pet.handle_timer_event("paused")
        self.assertEqual(self.pet.emotion, PetEmotion.SLEEP)
        self.assertIn("Zzz... en pausa...", self.pet.get_current_dialogue())

        # Reanudar -> FOCUS
        self.pet.handle_timer_event("resumed")
        self.assertEqual(self.pet.emotion, PetEmotion.FOCUS)

        # Fin de sesión de foco -> CELEBRATE
        self.pet.handle_timer_event("focus_finished")
        self.assertEqual(self.pet.emotion, PetEmotion.CELEBRATE)
        self.assertIn("¡POMODORO COMPLETADO!", self.pet.get_current_dialogue())

        # Inicio de descanso -> BREAK
        self.pet.handle_timer_event("break_started")
        self.assertEqual(self.pet.emotion, PetEmotion.BREAK)
        self.assertIn("Hora de estirar las piernas", self.pet.get_current_dialogue())

        # Reset -> IDLE
        self.pet.handle_timer_event("reset")
        self.assertEqual(self.pet.emotion, PetEmotion.IDLE)

    def test_animation_tick(self):
        """Verifica el ciclado de frames con cada tick."""
        self.pet.set_emotion(PetEmotion.FOCUS)
        self.assertEqual(self.pet.frame_index, 0)

        # Tick 1 -> Frame 1
        frame, dialogue = self.pet.tick_animation()
        self.assertEqual(self.pet.frame_index, 1)
        self.assertIsInstance(frame, list)
        self.assertIsInstance(dialogue, str)

        # Tick 2 -> Vuelve a Frame 0
        self.pet.tick_animation()
        self.assertEqual(self.pet.frame_index, 0)


if __name__ == "__main__":
    unittest.main()
