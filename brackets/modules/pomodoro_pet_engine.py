#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Motor de mascota y estados emocionales para el Pomodoro Retro de Brackets.
Personaje: TOMATÍN, tomate kawaii pixel-art (basado en la hoja de sprites de referencia).
Sigue la filosofía Lego: desacoplado de la interfaz gráfica y 100% testeable.
"""

from __future__ import annotations
from enum import Enum
from typing import Dict, List, Tuple, Optional


class PetEmotion(str, Enum):
    """Estados emocionales y de actividad de la mascota."""
    IDLE = "idle"              # En espera, Tomatín sonriente / ideas (plantillas 1 y 14)
    FOCUS = "focus"            # En sesión de trabajo, con gafas tecleando en laptop (plantilla 6)
    SLEEP = "sleep"            # En pausa, dormido plácidamente en nube con Zzz (plantilla 3)
    CELEBRATE = "celebrate"    # Sesión completada, salto triunfal con confeti (plantilla 2)
    BREAK = "break"            # En descanso, café humeante y relax (plantilla 5)


# =====================================================================
# PALETA DE COLORES INDEXADA PARA TOMATÍN Y CYBER HUD (20x20)
# =====================================================================
# '.' -> Transparente / Fondo oscuro LCD (#0D1117 / #05080A)
# '#' -> Contorno pixel negro bien definido (#111111)
# 'R' -> Rojo cuerpo Tomatín (#E63946)
# 'r' -> Rojo sombra inferior / volumen (#9B111E)
# 'L' -> Rojo brillo suave / highlight (#FF6B7A)
# 'g' -> Verde hoja y tallo (#38B000)
# 'G' -> Verde sombra / tallo (#226F00)
# 'l' -> Verde hoja brillo (#70E000)
# 'P' -> Rubor mejillas rosado kawaii (#FF8FA3)
# 'W' -> Blanco ojos / brillo / texto (#FFFFFF)
# 'Z' -> Verde fósforo LCD / terminal / Zzz (#39FF14)
# 'Y' -> Amarillo brillante (bombilla, confeti) (#FFCD0F)
# 'y' -> Amarillo cálido / sombra (#D4A373)
# 'B' -> Azul cian pantalla laptop / nube (#23A8F2)
# 'b' -> Azul marino base laptop (#0057AA)
# 'd' -> Azul sombra profunda (#004E7C)
# 'C' -> Marrón café taza (#8B5E3C)
# 'c' -> Taza cerámica clara (#DDB892)
# 'S' -> Vapor gris suave (#A0AAB2)
# 'K' -> Gafas negras (#161B22)
# 'O' -> Naranja confeti (#F77F00)
# Claves de compatibilidad:
# 'p' -> Rosa brillo (#FB6F7B)
# 'D' -> Azul (#0057AA)
# 'A' -> Plata claro (#B9C0C7)
# 'H' -> Plata oscuro (#889096)
# 'o' -> Dorado (#CD8E02)

COLOR_PALETTE: Dict[str, str] = {
    ".": "",
    "#": "#111111",
    "R": "#E63946",
    "r": "#9B111E",
    "L": "#FF6B7A",
    "g": "#38B000",
    "G": "#226F00",
    "l": "#70E000",
    "P": "#FF8FA3",
    "W": "#FFFFFF",
    "Z": "#39FF14",
    "Y": "#FFCD0F",
    "y": "#D4A373",
    "B": "#23A8F2",
    "b": "#0057AA",
    "d": "#004E7C",
    "C": "#8B5E3C",
    "c": "#DDB892",
    "S": "#A0AAB2",
    "K": "#161B22",
    "O": "#F77F00",
    "p": "#FB6F7B",
    "D": "#0057AA",
    "A": "#B9C0C7",
    "H": "#889096",
    "o": "#CD8E02",
}

# ---------------------------------------------------------------------
# Sprites de Tomatín (20 filas x 20 columnas)
# ---------------------------------------------------------------------

# 1. IDLE (En espera)
# Frame 0: Plantilla 1 (ORIGINAL) - Tomatín base sonriente con kawaii ojos y rubor
TOMATIN_IDLE_0 = [
    "....................",
    ".........##.........",
    ".........#g#........",
    ".......###g####.....",
    "....###GgggGggG###..",
    "..##GG#gggg#gg#GG##.",
    ".#RR##gggggggg##RR#.",
    "#RLRRR###GG###RRRRR#",
    "#WLRRRRRRRRRRRRRRRR#",
    "#LRRRR#WRRRRR#WRRRR#",
    "#RRRRR###RRRR###RRR#",
    "#RRRPPRRR#RR#RPPPRR#",
    "#RRRPPRRRR##RRRPPRR#",
    "#RRRRRRRRRRRRRRRRRR#",
    "#rRRRRRRRRRRRRRRRRr#",
    ".#rRRRRRRRRRRRRRRr#.",
    "..#rrrrrrrrrrrrrr#..",
    "...##rrrrrrrrrr##...",
    ".....##########.....",
    "....................",
]

# Frame 1: Plantilla 14 (IDEAS!) - Bombilla flotante amarilla y guiño/parpadeo
TOMATIN_IDLE_1 = [
    ".............Y......",
    ".........##.Y#Y.....",
    ".........#g##YY#....",
    ".......###g##YY#....",
    "....###GgggGg##Y....",
    "..##GG#gggg#gg#GG##.",
    ".#RR##gggggggg##RR#.",
    "#RLRRR###GG###RRRRR#",
    "#WLRRRRRRRRRRRRRRRR#",
    "#LRRRR###RRRR#WRRRR#",
    "#RRRRRRRRRRRR###RRR#",
    "#RRRPPRRR#RR#RPPPRR#",
    "#RRRPPRRRR##RRRPPRR#",
    "#RRRRRRRRRRRRRRRRRR#",
    "#rRRRRRRRRRRRRRRRRr#",
    ".#rRRRRRRRRRRRRRRr#.",
    "..#rrrrrrrrrrrrrr#..",
    "...##rrrrrrrrrr##...",
    ".....##########.....",
    "....................",
]

# 2. FOCUS (Trabajando / Concentrado)
# Frame 0: Plantilla 6 (CONCENTRADO PC) - Gafas y laptop portátil abierta
TOMATIN_FOCUS_0 = [
    "....................",
    ".......##...........",
    ".......#g#..........",
    ".....###g####.......",
    "...##GgggGggG##.....",
    "..#RR#gggggg#RR#####",
    ".#RLRR##GG##RR#BBBB#",
    "#WLRRR#K#K##K##BWWB#",
    "#LRRR#K#WK#K#W#BBBB#",
    "#RRRR#K#K##K#K#BWWB#",
    "#RRRPPRRR#RR#R#BBBB#",
    "#RRRPPRRRR##RR######",
    "#rRRRRRRRR#RR#bbbbb#",
    ".#rRRRRRRR##########",
    "..#rrrrrrr#bbbbbbbb#",
    "...##rrrrrrrrrr##...",
    ".....##########.....",
    "....................",
    "....................",
    "....................",
]

# Frame 1: Tecleo activo y cursor terminal verde fósforo en pantalla
TOMATIN_FOCUS_1 = [
    "....................",
    ".......##...........",
    ".......#g#..........",
    ".....###g####.......",
    "...##GgggGggG##.....",
    "..#RR#gggggg#RR#####",
    ".#RLRR##GG##RR#BBBB#",
    "#WLRRR#K#K##K##BZZB#",
    "#LRRR#K#WK#K#W#BBBB#",
    "#RRRR#K#K##K#K#BZZB#",
    "#RRRPPRRR#RR#R#BBBB#",
    "#RRRPPRRRR##RR######",
    "#rRRRRRRRR#RR#bbbbb#",
    ".#rRRRRRRR##########",
    "..#rrrrrrr#bbbbbbbb#",
    "...##rrrrrrrrrr##...",
    ".....##########.....",
    "....................",
    "....................",
    "....................",
]

# 3. SLEEP (Pausa / Durmiendo)
# Frame 0: Plantilla 3 (DORMIDO) - Ojos cerrados sobre nube/almohada con Zzz
TOMATIN_SLEEP_0 = [
    "..............ZZ....",
    "...............Z....",
    ".........##...ZZ....",
    ".........#g#........",
    ".......###g####.....",
    "....###GgggGggG###..",
    "..##GG#gggg#gg#GG##.",
    ".#RR##gggggggg##RR#.",
    "#RLRRR###GG###RRRRR#",
    "#WLRRRRRRRRRRRRRRRR#",
    "#LRRRR###RRRR###RRR#",
    "#RRRRRRRRRRRRRRRRRR#",
    "#RRRPPRRR#RR#RPPPRR#",
    "#rRRRPPRR###RRPPPRr#",
    "..##rrrrrrrrrrrr##..",
    ".###WWWW###WWWW###..",
    "#WWWWWWBBBBBBBBBBW#.",
    "#WWWWBBBBBBBBBBBBBB#",
    ".##################.",
    "....................",
]

# Frame 1: Zzz flotando más alto y respiración suave
TOMATIN_SLEEP_1 = [
    "..........ZZ..ZZ....",
    "...........Z...Z....",
    ".........##Z..ZZ....",
    ".........#g#........",
    ".......###g####.....",
    "....###GgggGggG###..",
    "..##GG#gggg#gg#GG##.",
    ".#RR##gggggggg##RR#.",
    "#RLRRR###GG###RRRRR#",
    "#WLRRRRRRRRRRRRRRRR#",
    "#LRRRR###RRRR###RRR#",
    "#RRRRRRRRRRRRRRRRRR#",
    "#RRRPPRRR#RR#RPPPRR#",
    "#rRRRPPRR###RRPPPRr#",
    "..##rrrrrrrrrrrr##..",
    ".###WWWW###WWWW###..",
    "#WWWWWWBBBBBBBBBBW#.",
    "#WWWWBBBBBBBBBBBBBB#",
    ".##################.",
    "....................",
]

# 4. CELEBRATE (Sesión completada / Victoria)
# Frame 0: Plantilla 2 (CELEBRATING) - Brazos arriba, salto y confeti
TOMATIN_CELEBRATE_0 = [
    ".Y................B.",
    "..#......##......#..",
    "..#R.....#g#....R#..",
    "..#RR..###g####RR#..",
    "O..#RR#GgggGgg#R#..Z",
    "...#RR#gggg#gg#R#...",
    "..#RRR##gggg##RRR#..",
    ".#RLRRR###GG##RRRR#.",
    "#WLRRRRRRRRRRRRRRRR#",
    "#LRRRR##RRRRRR##RRR#",
    "#RRRR#WR#RRRR#WR#RR#",
    "#RRRPPRR######RRPPR#",
    "#RRRPPRRR#WW#RRRPPR#",
    "#RRRRRRRR####RRRRRR#",
    "#rRRRRRRRRRRRRRRRRr#",
    ".#rRRRRRRRRRRRRRRr#.",
    "..#r##rrrrrrrr##r#..",
    "...#RR#......#RR#...",
    "...####......####...",
    "..W..............Y..",
]

# Frame 1: Rebote feliz con confeti en movimiento
TOMATIN_CELEBRATE_1 = [
    "..Z..............Y..",
    "..#......##......#..",
    "..#R.....#g#....R#..",
    "..#RR..###g####RR#..",
    "B..#RR#GgggGgg#R#..O",
    "...#RR#gggg#gg#R#...",
    "..#RRR##gggg##RRR#..",
    ".#RLRRR###GG##RRRR#.",
    "#WLRRRRRRRRRRRRRRRR#",
    "#LRRRR##RRRRRR##RRR#",
    "#RRRR#WR#RRRR#WR#RR#",
    "#RRRPPRR######RRPPR#",
    "#RRRPPRRR#WW#RRRPPR#",
    "#RRRPPRRR#WW#RRRPPR#",
    "#rRRRRRRR####RRRRRr#",
    ".#rRRRRRRRRRRRRRRr#.",
    "..#r##rrrrrrrr##r#..",
    "..#RR#........#RR#..",
    "..####........####..",
    ".Y..............W...",
]

# 5. BREAK (Descanso)
# Frame 0: Plantilla 5 (TOMANDO CAFÉ) - Taza humeante y aroma
TOMATIN_BREAK_0 = [
    "....................",
    "................S...",
    ".........##....S.S..",
    ".........#g#....S...",
    ".......###g####.....",
    "....###GgggGggG###..",
    "..##GG#gggg#gg#GG##.",
    ".#RR##gggggggg##RR#.",
    "#RLRRR###GG###RRRRR#",
    "#WLRRRRRRRRRRRRR####",
    "#LRRRR#WRRRRR#W#ccc#",
    "#RRRRR###RRRR###Ccc#",
    "#RRRPPRRR#RR#RP#CCC#",
    "#RRRPPRRRR##RRPP###.",
    "#RRRRRRRRRRRRRRRRR#.",
    "#rRRRRRRRRRRRRRRRr#.",
    ".#rRRRRRRRRRRRRRRr#.",
    "..#rrrrrrrrrrrrrr#..",
    "...##rrrrrrrrrr##...",
    ".....##########.....",
]

# Frame 1: Humo subiendo y guiño/relax
TOMATIN_BREAK_1 = [
    "................S...",
    "...............S.S..",
    ".........##.....S...",
    ".........#g#...S....",
    ".......###g####.....",
    "....###GgggGggG###..",
    "..##GG#gggg#gg#GG##.",
    ".#RR##gggggggg##RR#.",
    "#RLRRR###GG###RRRRR#",
    "#WLRRRRRRRRRRRRR####",
    "#LRRRR###RRRR###ccc#",
    "#RRRRRRRRRRRRRR#Ccc#",
    "#RRRPPRRR#RR#RP#CCC#",
    "#RRRPPRRRR##RRPP###.",
    "#RRRRRRRRRRRRRRRRR#.",
    "#rRRRRRRRRRRRRRRRr#.",
    ".#rRRRRRRRRRRRRRRr#.",
    "..#rrrrrrrrrrrrrr#..",
    "...##rrrrrrrrrr##...",
    ".....##########.....",
]

# Diccionario principal de sprites de Tomatín
TOMATIN_SPRITES: Dict[PetEmotion, List[List[str]]] = {
    PetEmotion.IDLE: [TOMATIN_IDLE_0, TOMATIN_IDLE_1],
    PetEmotion.FOCUS: [TOMATIN_FOCUS_0, TOMATIN_FOCUS_1],
    PetEmotion.SLEEP: [TOMATIN_SLEEP_0, TOMATIN_SLEEP_1],
    PetEmotion.CELEBRATE: [TOMATIN_CELEBRATE_0, TOMATIN_CELEBRATE_1],
    PetEmotion.BREAK: [TOMATIN_BREAK_0, TOMATIN_BREAK_1],
}

# Alias para compatibilidad total con código previo
SLIME_IDLE_0 = TOMATIN_IDLE_0
SLIME_IDLE_1 = TOMATIN_IDLE_1
SLIME_FOCUS_0 = TOMATIN_FOCUS_0
SLIME_FOCUS_1 = TOMATIN_FOCUS_1
SLIME_SLEEP_0 = TOMATIN_SLEEP_0
SLIME_SLEEP_1 = TOMATIN_SLEEP_1
SLIME_CELEBRATE_0 = TOMATIN_CELEBRATE_0
SLIME_CELEBRATE_1 = TOMATIN_CELEBRATE_1
SLIME_BREAK_0 = TOMATIN_BREAK_0
SLIME_BREAK_1 = TOMATIN_BREAK_1
SLIME_SPRITES = TOMATIN_SPRITES

# Diálogos retro del personaje Tomatín
EMOTION_DIALOGUES: Dict[PetEmotion, List[str]] = {
    PetEmotion.IDLE: [
        "¿Listo para concentrarte? 🍅",
        "Elige una tarea y dale al Play.",
        "Tomatín listo para la sesión.",
        "¡Hoy va a ser un gran día!",
    ],
    PetEmotion.FOCUS: [
        "¡Concéntrate, tú puedes! 🍅",
        "Tomatín en modo flow...",
        "Cero distracciones, código limpio.",
        "Un pomodoro a la vez.",
    ],
    PetEmotion.SLEEP: [
        "Zzz... en pausa...",
        "Descansando los ojitos...",
        "Pulsa Continuar o toca la pantalla al volver.",
    ],
    PetEmotion.CELEBRATE: [
        "¡POMODORO COMPLETADO! 🎉",
        "¡Increíble trabajo! +25 min 🍅",
        "¡Tomatín está orgulloso de ti! ⭐",
    ],
    PetEmotion.BREAK: [
        "Hora de estirar las piernas ☕",
        "Bebe agua y relaja la vista.",
        "Descanso bien merecido.",
    ],
}


class PetStateMachine:
    """
    Máquina de estados para la mascota de escritorio.
    Controla la emoción actual, el avance de frames y el diálogo de Tomatín.
    """

    def __init__(self, pet_name: str = "Tomatín"):
        self.pet_name = pet_name
        self.emotion: PetEmotion = PetEmotion.IDLE
        self.frame_index: int = 0
        self.dialogue_index: int = 0
        self.ticks_in_state: int = 0

    def set_emotion(self, new_emotion: PetEmotion) -> None:
        """Cambia la emoción de la mascota si es diferente a la actual."""
        if self.emotion != new_emotion:
            self.emotion = new_emotion
            self.frame_index = 0
            self.dialogue_index = 0
            self.ticks_in_state = 0

    def tick_animation(self) -> Tuple[List[str], str]:
        """
        Avanza el reloj de animación (llamar periódicamente, ej: cada 450ms).
        Devuelve (matriz_de_pixeles, frase_actual).
        """
        frames = TOMATIN_SPRITES.get(self.emotion, [TOMATIN_IDLE_0])
        self.frame_index = (self.frame_index + 1) % len(frames)
        self.ticks_in_state += 1

        # Rotar diálogo cada ~10 ticks
        dialogues = EMOTION_DIALOGUES.get(self.emotion, ["..."])
        if self.ticks_in_state % 10 == 0:
            self.dialogue_index = (self.dialogue_index + 1) % len(dialogues)

        current_frame = frames[self.frame_index]
        current_dialogue = dialogues[self.dialogue_index % len(dialogues)]
        return current_frame, current_dialogue

    def get_current_sprite(self) -> List[str]:
        """Devuelve el sprite actual según emoción y frame."""
        frames = TOMATIN_SPRITES.get(self.emotion, [TOMATIN_IDLE_0])
        return frames[self.frame_index % len(frames)]

    def get_current_dialogue(self) -> str:
        """Devuelve la frase actual de la mascota."""
        dialogues = EMOTION_DIALOGUES.get(self.emotion, ["..."])
        return dialogues[self.dialogue_index % len(dialogues)]

    def handle_timer_event(self, event: str) -> None:
        """Mapea eventos de PomodoroTimerEngine a emociones de la mascota."""
        if not event:
            return

        ev = event.lower()
        if ev in ("focus_started", "resumed"):
            self.set_emotion(PetEmotion.FOCUS)
        elif ev in ("paused", "sleep"):
            self.set_emotion(PetEmotion.SLEEP)
        elif ev in ("focus_finished", "completed"):
            self.set_emotion(PetEmotion.CELEBRATE)
        elif ev in ("break_started", "break"):
            self.set_emotion(PetEmotion.BREAK)
        elif ev in ("reset", "idle", "break_finished"):
            self.set_emotion(PetEmotion.IDLE)
