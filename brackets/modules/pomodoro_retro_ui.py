#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aplicación Pomodoro Retro para Brackets con Mascota (Tomatín).
Estética unificada cyber terminal / digital LCD (verde fósforo sobre fondo negro).
Modo Always-On-Top compacto (HUD) y completo en Tkinter nativo (0 dependencias).
"""

from __future__ import annotations
import os
import sys
import threading
from typing import Optional, List, Dict, Any

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
except ImportError:
    tk = None
    ttk = None
    messagebox = None

from brackets.modules.pomodoro_timer import PomodoroTimerEngine, TimerConfig, load_timer_config
from brackets.modules.pomodoro_pet_engine import (
    PetStateMachine,
    PetEmotion,
    COLOR_PALETTE,
    SLIME_SPRITES,
    TOMATIN_SPRITES,
)
from brackets.managers.entity_manager import EntityManager
from brackets.models.entities import Task


class PomodoroRetroApp:
    """Ventana de escritorio retro para el temporizador Pomodoro con Tomatín."""

    # Paleta de estilo Cyber Terminal / Digital LCD
    BG_COLOR = "#0D1117"        # Fondo negro azulado / Terminal oscuro
    PANEL_BG = "#161B22"        # Paneles y tarjetas oscuras
    BORDER_COLOR = "#30363D"    # Borde sutil
    BORDER_CYBER = "#238636"    # Borde verde matriz / terminal
    LCD_BG = "#05080A"          # Fondo ultra negro digital LCD
    LCD_FG = "#39FF14"          # Verde fósforo digital brillante
    LCD_ACCENT = "#00FF66"      # Verde fósforo medio
    LCD_CYAN = "#00F0FF"        # Azul cian digital
    LCD_AMBER = "#FFB703"       # Ámbar / Alerta digital
    LCD_RED = "#FF5555"         # Rojo digital
    MUTED_FG = "#8B949E"        # Gris atenuado terminal
    PIXEL_SIZE = 7              # Tamaño en px de cada celda del sprite 20x20 -> 140x140px

    # Dimensiones de ventana
    FULL_GEOMETRY = "320x540"
    MINI_GEOMETRY = "200x255"

    # Constantes retro para compatibilidad previa
    WIN_BG = BG_COLOR
    TITLE_BG = PANEL_BG
    TITLE_FG = LCD_FG
    BUBBLE_BG = PANEL_BG

    def __init__(
        self,
        vault_dir: str = ".",
        event_log=None,
        entity_manager: Optional[EntityManager] = None,
        auto_start: bool = False,
        current_week=None,
        current_day=None,
    ):
        if tk is None:
            raise RuntimeError("Tkinter no está disponible en este entorno Python.")

        self.vault_dir = os.path.abspath(vault_dir)
        self.event_log = event_log
        self.current_week = current_week
        self.current_day = current_day
        self.config, self.config_path = load_timer_config(self.vault_dir)
        self.engine = PomodoroTimerEngine(self.config)
        self.pet = PetStateMachine(pet_name="Tomatín")

        # Cargar EntityManager si es posible para listar tareas reales
        if entity_manager:
            self.entity_manager = entity_manager
        else:
            data_dir = os.path.join(self.vault_dir, "data")
            if os.path.exists(os.path.join(data_dir, "tables", "tasks.yaml")):
                self.entity_manager = EntityManager(data_dir)
            else:
                self.entity_manager = None

        # Configurar hook de completitud
        self.engine.set_session_completed_hook(self._on_session_completed)

        # Estado de ventana
        self.is_topmost: bool = True
        self.is_compact: bool = False
        self._drag_data = {"x": 0, "y": 0}
        self._timer_after_id: Optional[str] = None
        self._anim_after_id: Optional[str] = None

        # Inicializar ventana principal
        self.root = tk.Tk()
        self.root.title("🍅 Pomodoro - Tomatín")
        self.root.geometry(self.FULL_GEOMETRY)
        self.root.resizable(False, False)
        self.root.configure(bg=self.BG_COLOR)

        # Forzar Always-On-Top por defecto (estilo widget de productividad)
        self.root.wm_attributes("-topmost", self.is_topmost)

        # Estilo retro para ttk
        self._setup_retro_style()

        # Cargar assets de alta resolución para Tomatín si existen
        self._focus_images = []
        try:
            assets_dir = os.path.join(os.path.dirname(__file__), "assets", "pomodoro")
            imgs = []
            for i in range(1, 6):
                fp = os.path.join(assets_dir, f"tomatin_focus_{i}.png")
                if os.path.exists(fp):
                    imgs.append(tk.PhotoImage(file=fp))
            if imgs:
                self._focus_images = imgs
        except Exception:
            self._focus_images = []

        # Construir interfaz
        self._build_ui()

        # Iniciar loops de reloj y animación
        self._update_mascot_frame()
        self._update_timer_loop()

        if auto_start:
            self.action_play_pause()

    def _setup_retro_style(self) -> None:
        """Configura estilos de terminal retro para widgets ttk."""
        style = ttk.Style()
        style.theme_use("classic")
        style.configure(
            "Retro.TCombobox",
            fieldbackground=self.PANEL_BG,
            background=self.PANEL_BG,
            foreground=self.LCD_FG,
            arrowcolor=self.LCD_FG,
            darkcolor=self.BORDER_CYBER,
            lightcolor=self.BORDER_CYBER,
            bordercolor=self.BORDER_CYBER,
        )
        style.map(
            "Retro.TCombobox",
            fieldbackground=[("readonly", self.PANEL_BG)],
            foreground=[("readonly", self.LCD_FG)],
            selectbackground=[("readonly", self.BORDER_CYBER)],
            selectforeground=[("readonly", "#FFFFFF")],
        )

    def _build_ui(self) -> None:
        """Construye todos los elementos de la ventana retro-terminal."""
        # 1. Barra de título estilo retro-terminal
        self.title_bar = tk.Frame(
            self.root,
            bg=self.PANEL_BG,
            height=28,
            relief="flat",
            bd=1,
            highlightthickness=1,
            highlightbackground=self.BORDER_CYBER,
        )
        self.title_bar.pack(fill="x", padx=4, pady=(4, 2))
        self.title_bar.bind("<ButtonPress-1>", self._start_drag)
        self.title_bar.bind("<B1-Motion>", self._on_drag)

        self.title_icon_label = tk.Label(
            self.title_bar,
            text=" 🍅 Tomatín HUD",
            bg=self.PANEL_BG,
            fg=self.LCD_FG,
            font=("Consolas", 9, "bold"),
        )
        self.title_icon_label.pack(side="left", padx=2)
        self.title_icon_label.bind("<ButtonPress-1>", self._start_drag)
        self.title_icon_label.bind("<B1-Motion>", self._on_drag)

        # Botón de cerrar [✕]
        self.btn_close = tk.Button(
            self.title_bar,
            text="✕",
            font=("Consolas", 8, "bold"),
            bg=self.PANEL_BG,
            fg=self.LCD_RED,
            activebackground=self.LCD_RED,
            activeforeground="#000000",
            relief="flat",
            bd=0,
            padx=5,
            command=self.root.destroy,
        )
        self.btn_close.pack(side="right", padx=1, pady=1)

        # Botón Pin Always-On-Top [📌]
        self.btn_pin = tk.Button(
            self.title_bar,
            text="📌",
            font=("Consolas", 8),
            bg="#1F3A24" if self.is_topmost else self.PANEL_BG,
            fg=self.LCD_FG if self.is_topmost else self.MUTED_FG,
            activebackground=self.BORDER_CYBER,
            activeforeground="#FFFFFF",
            relief="flat",
            bd=0,
            padx=4,
            command=self._toggle_topmost,
        )
        self.btn_pin.pack(side="right", padx=1, pady=1)

        # Botón Modo Mini / Compacto HUD [-] / [+]
        self.btn_compact = tk.Button(
            self.title_bar,
            text="[-]",
            font=("Consolas", 8, "bold"),
            bg=self.PANEL_BG,
            fg=self.LCD_FG,
            activebackground=self.BORDER_CYBER,
            activeforeground="#000000",
            relief="flat",
            bd=0,
            padx=4,
            command=self.toggle_compact_mode,
        )
        self.btn_compact.pack(side="right", padx=1, pady=1)

        # 2. Marco principal contenedor
        self.main_frame = tk.Frame(
            self.root,
            bg=self.BG_COLOR,
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.BORDER_CYBER,
        )
        self.main_frame.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        # 3. Visor de Tomatín (Pantalla LCD oscura)
        self.pet_container = tk.Frame(
            self.main_frame,
            bg=self.LCD_BG,
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=self.BORDER_CYBER,
        )
        self.pet_container.pack(fill="x", padx=8, pady=6)

        self.canvas = tk.Canvas(
            self.pet_container,
            width=146,
            height=146,
            bg=self.LCD_BG,
            highlightthickness=0,
            cursor="hand2",
        )
        self.canvas.pack(pady=3)
        self.canvas.bind("<Button-1>", self._on_hud_clicked)

        # Diálogo / Frase de Tomatín
        self.dialogue_frame = tk.Frame(
            self.main_frame,
            bg=self.PANEL_BG,
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=self.BORDER_COLOR,
        )
        self.dialogue_frame.pack(fill="x", padx=10, pady=(0, 6))

        self.lbl_dialogue = tk.Label(
            self.dialogue_frame,
            text=self.pet.get_current_dialogue(),
            bg=self.PANEL_BG,
            fg=self.LCD_ACCENT,
            font=("Consolas", 8, "italic"),
            wraplength=260,
            justify="center",
            pady=3,
        )
        self.lbl_dialogue.pack(fill="x")

        # 4. Display Digital LCD (Reloj + Fase)
        self.lcd_frame = tk.Frame(
            self.main_frame,
            bg=self.LCD_BG,
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=self.BORDER_CYBER,
        )
        self.lcd_frame.pack(fill="x", padx=8, pady=4)

        self.top_lcd = tk.Frame(self.lcd_frame, bg=self.LCD_BG)
        self.top_lcd.pack(fill="x", padx=6, pady=(4, 0))

        self.lbl_phase = tk.Label(
            self.top_lcd,
            text="[ IDLE ]",
            bg=self.LCD_BG,
            fg=self.LCD_AMBER,
            font=("Consolas", 9, "bold"),
        )
        self.lbl_phase.pack(side="left")

        self.lbl_sessions = tk.Label(
            self.top_lcd,
            text=f"🍅 x {self.engine.completed_focus_sessions}",
            bg=self.LCD_BG,
            fg=self.LCD_FG,
            font=("Consolas", 9, "bold"),
        )
        self.lbl_sessions.pack(side="right")

        self.lbl_digits = tk.Label(
            self.lcd_frame,
            text=f"{self.config.focus_minutes:02d}:00",
            bg=self.LCD_BG,
            fg=self.LCD_FG,
            font=("Consolas", 30, "bold"),
            cursor="hand2",
        )
        self.lbl_digits.pack(pady=(0, 2))
        self.lbl_digits.bind("<Button-1>", self._on_hud_clicked)

        # Barra de progreso de bloques pixelados en LCD
        self.lbl_progress = tk.Label(
            self.lcd_frame,
            text="[░░░░░░░░░░░░░░░░░░░░]",
            bg=self.LCD_BG,
            fg=self.LCD_FG,
            font=("Consolas", 8),
            cursor="hand2",
        )
        self.lbl_progress.pack(pady=(0, 4))
        self.lbl_progress.bind("<Button-1>", self._on_hud_clicked)

        # 5. Selector de Tarea Activa (integrado con tasks.yaml)
        self.task_label = tk.Label(
            self.main_frame,
            text="🎯 Tarea vinculada:",
            bg=self.BG_COLOR,
            fg=self.LCD_FG,
            font=("Consolas", 8, "bold"),
            anchor="w",
        )
        self.task_label.pack(fill="x", padx=10, pady=(4, 1))

        self.task_choices = self._load_pending_tasks()
        self.task_var = tk.StringVar(value="-- Sin tarea (Modo libre) --")
        self.cmb_tasks = ttk.Combobox(
            self.main_frame,
            textvariable=self.task_var,
            values=[t["display"] for t in self.task_choices],
            state="readonly",
            style="Retro.TCombobox",
        )
        self.cmb_tasks.pack(fill="x", padx=10, pady=(0, 8))
        self.cmb_tasks.bind("<<ComboboxSelected>>", self._on_task_selected)

        # 6. Botonera de control retro (Estilo cyber terminal)
        self.btn_grid = tk.Frame(self.main_frame, bg=self.BG_COLOR)
        self.btn_grid.pack(fill="x", padx=8, pady=4)

        self.btn_play = tk.Button(
            self.btn_grid,
            text="▶ Iniciar",
            bg=self.PANEL_BG,
            fg=self.LCD_FG,
            activebackground=self.BORDER_CYBER,
            activeforeground="#000000",
            font=("Consolas", 9, "bold"),
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=self.BORDER_CYBER,
            command=self.action_play_pause,
        )
        self.btn_play.pack(side="left", padx=2, expand=True, fill="x")

        self.btn_break = tk.Button(
            self.btn_grid,
            text="☕ Descanso",
            bg=self.PANEL_BG,
            fg=self.LCD_CYAN,
            activebackground="#0077B8",
            activeforeground="#FFFFFF",
            font=("Consolas", 9),
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=self.BORDER_COLOR,
            command=self.action_start_break,
        )
        self.btn_break.pack(side="left", padx=2, expand=True, fill="x")

        self.btn_reset = tk.Button(
            self.btn_grid,
            text="⏹ Reset",
            bg=self.PANEL_BG,
            fg=self.LCD_RED,
            activebackground="#8B0000",
            activeforeground="#FFFFFF",
            font=("Consolas", 9),
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=self.BORDER_COLOR,
            command=self.action_reset,
        )
        self.btn_reset.pack(side="left", padx=2, expand=True, fill="x")

    def toggle_compact_mode(self) -> None:
        """Alterna entre el modo completo y el modo mini (HUD compacto)."""
        self.is_compact = not self.is_compact
        x = self.root.winfo_x()
        y = self.root.winfo_y()

        if self.is_compact:
            # Ocultar widgets que no van en mini mode
            self.dialogue_frame.pack_forget()
            self.top_lcd.pack_forget()
            self.task_label.pack_forget()
            self.cmb_tasks.pack_forget()
            self.btn_grid.pack_forget()

            # Ajustar padding compacto
            self.pet_container.pack_configure(padx=4, pady=(2, 2))
            self.lcd_frame.pack_configure(padx=4, pady=2)
            self.lbl_digits.configure(font=("Consolas", 22, "bold"))
            self.lbl_digits.pack_configure(pady=(2, 0))
            self.lbl_progress.pack_configure(pady=(0, 2))

            self.btn_compact.configure(text="[+]")
            self.root.geometry(f"{self.MINI_GEOMETRY}+{x}+{y}")
        else:
            # Restaurar orden completo
            self.pet_container.pack_forget()
            self.dialogue_frame.pack_forget()
            self.lcd_frame.pack_forget()
            self.task_label.pack_forget()
            self.cmb_tasks.pack_forget()
            self.btn_grid.pack_forget()
            self.top_lcd.pack_forget()
            self.lbl_digits.pack_forget()
            self.lbl_progress.pack_forget()

            # Repackear en orden original
            self.pet_container.pack(fill="x", padx=8, pady=6)
            self.dialogue_frame.pack(fill="x", padx=10, pady=(0, 6))
            self.lcd_frame.pack(fill="x", padx=8, pady=4)
            self.top_lcd.pack(fill="x", padx=6, pady=(4, 0))
            self.lbl_digits.configure(font=("Consolas", 30, "bold"))
            self.lbl_digits.pack(pady=(0, 2))
            self.lbl_progress.pack(pady=(0, 4))
            self.task_label.pack(fill="x", padx=10, pady=(4, 1))
            self.cmb_tasks.pack(fill="x", padx=10, pady=(0, 8))
            self.btn_grid.pack(fill="x", padx=8, pady=4)

            self.btn_compact.configure(text="[-]")
            self.root.geometry(f"{self.FULL_GEOMETRY}+{x}+{y}")

    def _on_hud_clicked(self, _event=None) -> None:
        """Permite pausar o reanudar al hacer clic sobre el personaje o el display digital."""
        self.action_play_pause()

    def _start_drag(self, event) -> None:
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _on_drag(self, event) -> None:
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        x = self.root.winfo_x() + dx
        y = self.root.winfo_y() + dy
        self.root.geometry(f"+{x}+{y}")

    def _toggle_topmost(self) -> None:
        self.is_topmost = not self.is_topmost
        self.root.wm_attributes("-topmost", self.is_topmost)
        self.btn_pin.configure(
            bg="#1F3A24" if self.is_topmost else self.PANEL_BG,
            fg=self.LCD_FG if self.is_topmost else self.MUTED_FG,
        )

    def _load_pending_tasks(self) -> List[Dict[str, Any]]:
        """Carga tareas pendientes desde EntityManager o devuelve lista por defecto."""
        items = [{"id": None, "title": None, "display": "-- Sin tarea (Modo libre) --"}]
        if not self.entity_manager:
            return items

        today_tids = list(self.current_day.task_ids) if (self.current_day and hasattr(self.current_day, "task_ids")) else []
        today_tasks = []
        for tid in today_tids:
            if tid in self.entity_manager.tasks:
                t = self.entity_manager.tasks[tid]
                if t.status == "pending":
                    today_tasks.append(t)

        other_tasks = [t for t in self.entity_manager.tasks.values() if t.status == "pending" and t.id not in today_tids]
        all_pending = today_tasks + other_tasks

        for t in all_pending[:30]:  # Primeras 30 tareas pendientes
            is_today = "⭐ " if t.id in today_tids else ""
            prefix = f"#[{t.project_id}] " if t.project_id else ""
            display_title = (t.title[:28] + "...") if len(t.title) > 30 else t.title
            items.append({
                "id": t.id,
                "project_id": t.project_id,
                "title": t.title,
                "display": f"{is_today}{prefix}{display_title}"
            })
        return items

    def _on_task_selected(self, _event=None) -> None:
        selected_display = self.task_var.get()
        matched = next((t for t in self.task_choices if t["display"] == selected_display), None)
        if matched and matched["id"]:
            self.engine.set_active_task(matched["id"], matched.get("project_id"), matched.get("title"))
        else:
            self.engine.set_active_task(None, None, None)

    def draw_sprite(self, sprite_matrix: List[str]) -> None:
        """Dibuja el sprite: render de alta resolución si está disponible o matriz pixel-art."""
        self.canvas.delete("all")
        if self._focus_images and self.pet.emotion == PetEmotion.FOCUS:
            img = self._focus_images[self.pet.frame_index % len(self._focus_images)]
            cw = int(self.canvas.cget("width"))
            ch = int(self.canvas.cget("height"))
            self.canvas.create_image(cw // 2, ch // 2, image=img)
            self._current_canvas_img = img  # Mantener referencia viva para Tkinter
            return

        offset_x = 3
        offset_y = 3
        ps = self.PIXEL_SIZE

        for row_idx, row in enumerate(sprite_matrix):
            y1 = offset_y + (row_idx * ps)
            y2 = y1 + ps
            for col_idx, char in enumerate(row):
                color = COLOR_PALETTE.get(char, "")
                if color:
                    x1 = offset_x + (col_idx * ps)
                    x2 = x1 + ps
                    self.canvas.create_rectangle(
                        x1, y1, x2, y2,
                        fill=color,
                        outline=color,
                    )

    def _update_mascot_frame(self) -> None:
        """Cicla el frame de animación de Tomatín y actualiza el diálogo."""
        frame, dialogue = self.pet.tick_animation()
        self.draw_sprite(frame)
        self.lbl_dialogue.configure(text=dialogue)
        # Cadencia de animación: 450ms
        self._anim_after_id = self.root.after(450, self._update_mascot_frame)

    def _update_timer_loop(self) -> None:
        """Ciclo de 1 segundo del motor de temporizador."""
        if self.engine.is_running and not self.engine.is_paused:
            event = self.engine.tick(1)
            if event:
                self.pet.handle_timer_event(event)
                self._play_retro_beep()

        self._render_lcd()
        self._timer_after_id = self.root.after(1000, self._update_timer_loop)

    def _render_lcd(self) -> None:
        """Actualiza etiquetas de reloj, fase y barra de progreso."""
        # Tiempo digital
        if self.engine.phase == "idle":
            self.lbl_digits.configure(text=f"{self.config.focus_minutes:02d}:00", fg=self.LCD_FG)
            self.lbl_phase.configure(text="[ IDLE ]", fg=self.LCD_AMBER)
            self.btn_play.configure(text="▶ Iniciar")
        else:
            self.lbl_digits.configure(text=self.engine.remaining_hhmmss())
            if self.engine.is_paused:
                self.lbl_digits.configure(fg=self.LCD_AMBER)
                self.lbl_phase.configure(text="[ PAUSA ]", fg=self.LCD_RED)
                self.btn_play.configure(text="▶ Continuar")
            elif self.engine.phase == "focus":
                self.lbl_digits.configure(fg=self.LCD_FG)
                self.lbl_phase.configure(text="[ FOCUS ]", fg=self.LCD_FG)
                self.btn_play.configure(text="⏸ Pausar")
            elif self.engine.phase == "break":
                self.lbl_digits.configure(fg=self.LCD_CYAN)
                self.lbl_phase.configure(text="[ BREAK ]", fg=self.LCD_CYAN)
                self.btn_play.configure(text="⏸ Pausar")

        # Contador de sesiones hoy
        self.lbl_sessions.configure(text=f"🍅 x {self.engine.completed_focus_sessions}")

        # Barra de progreso ASCII (20 bloques)
        prog = self.engine.progress()
        filled = int(round(prog * 20))
        bar = "█" * filled + "░" * (20 - filled)
        self.lbl_progress.configure(text=f"[{bar}]", fg=self.LCD_CYAN if self.engine.phase == "break" else self.LCD_FG)

    def _play_retro_beep(self) -> None:
        """Emite un tono de fin de sesión sin bloquear el hilo principal."""
        def beep():
            try:
                if sys.platform == "win32":
                    import winsound
                    # Tono 8-bit de 3 notas
                    winsound.Beep(523, 120)  # C5
                    winsound.Beep(659, 120)  # E5
                    winsound.Beep(784, 250)  # G5
                else:
                    sys.stdout.write("\a")
                    sys.stdout.flush()
            except Exception:
                pass

        threading.Thread(target=beep, daemon=True).start()

    def _on_session_completed(self, session_record: Dict[str, Any]) -> None:
        """Registra la sesión completada en el log y el evento."""
        if self.event_log:
            self.event_log.append(
                "pomodoro_session_completed",
                task_id=session_record.get("task_id"),
                project_id=session_record.get("project_id"),
                task_title=session_record.get("task_title"),
                duration_sec=session_record.get("planned_seconds"),
                source="retro_gui"
            )

    # ================= Acciones de Control =================

    def action_play_pause(self) -> None:
        """Inicia, pausa o reanuda el cronómetro."""
        if not self.engine.is_running:
            self.engine.start_focus()
            self.pet.handle_timer_event("focus_started")
        elif self.engine.is_paused:
            self.engine.resume()
            self.pet.handle_timer_event("resumed")
        else:
            self.engine.pause()
            self.pet.handle_timer_event("paused")
        self._render_lcd()

    def action_start_break(self) -> None:
        """Inicia el periodo de descanso de 5 minutos."""
        self.engine.start_break()
        self.pet.handle_timer_event("break_started")
        self._render_lcd()

    def action_reset(self) -> None:
        """Reinicia el cronómetro al estado de reposo."""
        self.engine.reset()
        self.pet.handle_timer_event("reset")
        self._render_lcd()

    def run(self) -> None:
        """Inicia el bucle de eventos de la interfaz Tkinter."""
        self.root.mainloop()


def launch_retro_pomodoro(
    vault_dir: str = ".",
    auto_start: bool = False,
    event_log=None,
    entity_manager: Optional[EntityManager] = None,
    current_week=None,
    current_day=None,
) -> None:
    """Punto de entrada para lanzar la app retro de Pomodoro."""
    app = PomodoroRetroApp(
        vault_dir=vault_dir,
        event_log=event_log,
        entity_manager=entity_manager,
        auto_start=auto_start,
        current_week=current_week,
        current_day=current_day,
    )
    app.run()


if __name__ == "__main__":
    vault_path = sys.argv[1] if len(sys.argv) > 1 else "."
    launch_retro_pomodoro(vault_path)
