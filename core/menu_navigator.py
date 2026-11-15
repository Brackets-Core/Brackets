#!/usr/bin/env python3
"""
Componente unificado de navegación y captura de teclado interactiva para Brackets.
Soporta en todos los niveles:
- Flechas arriba/abajo (↑ / ↓) con cursor visual '>'.
- Selección con Enter.
- Selección directa mediante teclas rápidas (sin confirmación por Enter).
- Tecla universal para volver al nivel superior (0, v o Esc).
- Salto directo al Menú Principal (m o Home).
"""

from __future__ import annotations
import os
import sys
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple, Dict, Any


KEY_UP = "__UP__"
KEY_DOWN = "__DOWN__"
KEY_ENTER = "__ENTER__"
KEY_ESC = "__ESC__"

NAV_BACK = "back"
NAV_MAIN = "menu"
NAV_EXIT = "exit"


def read_single_key(prompt: str = "Selecciona una opción: ") -> str:
    """Lee una sola tecla para navegación rápida de menús (sin Enter)."""
    print(prompt, end="", flush=True)

    try:
        if os.name == "nt":
            import msvcrt

            key = msvcrt.getwch()
            if key in ("\x00", "\xe0"):
                # Teclas especiales (flechas/F-keys).
                extended = msvcrt.getwch().lower()
                print()
                if extended == "h":
                    return KEY_UP
                if extended == "p":
                    return KEY_DOWN
                return ""
            if key == "\x1b":
                print()
                return KEY_ESC
            if key in ("\r", "\n"):
                print()
                return KEY_ENTER
        else:
            import termios
            import tty
            import select

            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                key = sys.stdin.read(1)
                if key == "\x1b":
                    # Comprobar si hay más caracteres pendientes (secuencia de escape)
                    r, _, _ = select.select([sys.stdin], [], [], 0.05)
                    if r:
                        second = sys.stdin.read(1)
                        third = sys.stdin.read(1)
                        print()
                        if second == "[" and third == "A":
                            return KEY_UP
                        if second == "[" and third == "B":
                            return KEY_DOWN
                        return ""
                    else:
                        print()
                        return KEY_ESC
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

            if key in ("\r", "\n"):
                print()
                return KEY_ENTER

        if key in ("\x03",):
            raise KeyboardInterrupt

        print(key)
        return key.strip().lower()

    except Exception:
        # Fallback seguro para terminales no compatibles o entornos de test
        return input(prompt).strip().lower()


@dataclass
class MenuOption:
    """Representa una opción de menú."""
    key: str
    label: str
    action_id: str
    aliases: List[str] = field(default_factory=list)
    group: Optional[str] = None

    def matches(self, choice: str) -> bool:
        norm = choice.strip().lower()
        if not norm:
            return False
        if norm == self.key.strip().lower():
            return True
        for alias in self.aliases:
            if norm == alias.strip().lower():
                return True
        return False


class MenuNavigator:
    """Controlador genérico de renderizado y captura de selección interactiva."""

    def __init__(
        self,
        title: str,
        options: List[MenuOption],
        header_lines: Optional[List[str]] = None,
        show_back: bool = True,
        show_main_menu: bool = True,
        is_main_menu: bool = False,
        width: int = 65,
        print_fn: Optional[Callable[..., None]] = None,
        input_fn: Optional[Callable[[str], str]] = None,
        read_single_key_fn: Optional[Callable[[str], str]] = None,
        clear_screen_fn: Optional[Callable[[], None]] = None,
    ):
        self.title = title
        self.options = options
        self.header_lines = header_lines or []
        self.show_back = show_back and not is_main_menu
        self.show_main_menu = show_main_menu and not is_main_menu
        self.is_main_menu = is_main_menu
        self.width = width
        self.print = print_fn or print
        self.input = input_fn or input
        if read_single_key_fn is not None:
            self.read_single_key = read_single_key_fn
        elif input_fn is not None and input_fn is not input:
            self.read_single_key = lambda prompt="": self.input(prompt)
        else:
            self.read_single_key = read_single_key
        self.clear_screen = clear_screen_fn or (lambda: None)
        self.selected_index = 0

    def render(self) -> None:
        """Dibuja el menú en pantalla con el cursor en la opción seleccionada."""
        self.clear_screen()
        self.print("=" * self.width)
        self.print(self.title)
        self.print("=" * self.width)

        if self.header_lines:
            for line in self.header_lines:
                self.print(line)
            self.print("-" * self.width)

        # Agrupar opciones o renderizar en orden
        current_group = None
        for idx, opt in enumerate(self.options):
            if opt.group and opt.group != current_group:
                current_group = opt.group
                self.print(f"\n  {current_group}:")

            pointer = "> " if idx == self.selected_index else "  "
            indent = "    " if opt.group else "  "
            self.print(f"{pointer}{indent}[{opt.key}] {opt.label}")

        # Opciones de navegación estándar
        nav_lines = []
        if self.show_back:
            nav_lines.append("[0/Esc] ↩️ Volver")
        if self.show_main_menu:
            nav_lines.append("[m] 🏠 Menú Principal")
        if self.is_main_menu:
            nav_lines.append("[q/0] 👋 Salir")

        if nav_lines:
            self.print("\n  " + "   ".join(nav_lines))

        self.print("-" * self.width)
        self.print("↑/↓: Moverse | Enter/Tecla: Seleccionar | 0/Esc: Volver | m: Inicio")
        self.print("=" * self.width)

    def prompt(self) -> Tuple[str, Optional[MenuOption]]:
        """
        Bucle de interacción interactivo.
        Retorna una tupla:
        - ("action", MenuOption): Opción seleccionada
        - ("back", None): Volver al nivel anterior
        - ("menu", None): Saltar al Menú Principal
        - ("exit", None): Salir de la aplicación
        """
        if not self.options:
            return ("back", None)

        num_options = len(self.options)

        while True:
            self.selected_index = max(0, min(self.selected_index, num_options - 1))
            self.render()

            raw_choice = self.read_single_key("Selecciona una opción: ").strip()
            upper_choice = raw_choice.upper()
            lower_choice = raw_choice.lower()

            if upper_choice == KEY_UP:
                self.selected_index = (self.selected_index - 1) % num_options
                continue

            if upper_choice == KEY_DOWN:
                self.selected_index = (self.selected_index + 1) % num_options
                continue

            if upper_choice == KEY_ENTER:
                selected_option = self.options[self.selected_index]
                return ("action", selected_option)

            # Volver al nivel superior
            if upper_choice == KEY_ESC or lower_choice in ("0", "v", "back", "volver", "\x1b"):
                if self.is_main_menu:
                    return ("exit", None)
                return ("back", None)

            # Salto directo al Menú Principal
            if lower_choice in ("m", "home", "menu") and not self.is_main_menu:
                return ("menu", None)

            # Salir
            if lower_choice in ("q", "exit"):
                return ("exit", None)

            # Búsqueda de coincidencia por tecla directa
            for opt in self.options:
                if opt.matches(lower_choice):
                    return ("action", opt)

            # Si no coincide
            self.print("❌ Opción inválida.")
