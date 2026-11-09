/**
 * Brackets Web Hub — Frontend Vanilla JavaScript
 * Cero frameworks, cero dependencias, carga ultra rápida.
 */

// Estado de la aplicación
const state = {
  currentVault: null,
  activeYear: null,
  activeWeekNumber: null,
  activeDayNumber: null,
  hubData: null,
  captureMode: 'today_task', // 'today_task' | 'week_task' | 'note' | 'definition'
  createStatus: 'pending',   // 'pending' | 'done'
  deferredPrompt: null
};

// Elementos del DOM
const el = {
  vaultSelect: document.getElementById('vaultSelect'),
  btnHamburger: document.getElementById('btnHamburger'),
  hamburgerDrawer: document.getElementById('hamburgerDrawer'),
  hamburgerBackdrop: document.getElementById('hamburgerBackdrop'),
  btnCloseHamburger: document.getElementById('btnCloseHamburger'),
  hamburgerMenuContent: document.getElementById('hamburgerMenuContent'),
  btnPrevWeek: document.getElementById('btnPrevWeek'),
  btnNextWeek: document.getElementById('btnNextWeek'),
  weekBadge: document.getElementById('weekBadge'),
  weightBadge: document.getElementById('weightBadge'),
  btnQuickWeight: document.getElementById('btnQuickWeight'),
  btnQuickExtraDay: document.getElementById('btnQuickExtraDay'),
  btnQuickNewWeek: document.getElementById('btnQuickNewWeek'),
  daysStrip: document.getElementById('daysStrip'),
  activeDayTitle: document.getElementById('activeDayTitle'),
  locGroup: document.getElementById('locGroup'),
  todayTasksList: document.getElementById('todayTasksList'),
  weekTasksList: document.getElementById('weekTasksList'),
  todayCountBadge: document.getElementById('todayCountBadge'),
  weekCountBadge: document.getElementById('weekCountBadge'),
  topicsCountBadge: document.getElementById('topicsCountBadge'),
  notesCountBadge: document.getElementById('notesCountBadge'),
  defsCountBadge: document.getElementById('defsCountBadge'),
  topicsContainer: document.getElementById('topicsContainer'),
  notesContainer: document.getElementById('notesContainer'),
  definitionsContainer: document.getElementById('definitionsContainer'),

    // Inline Section Creation
  inputTodayTitle: document.getElementById('inputTodayTitle'),
  btnToggleTodayStatus: document.getElementById('btnToggleTodayStatus'),
  btnToggleTodayDesc: document.getElementById('btnToggleTodayDesc'),
  btnSubmitTodayTask: document.getElementById('btnSubmitTodayTask'),
  descBoxTodayTask: document.getElementById('descBoxTodayTask'),
  descTodayText: document.getElementById('descTodayText'),

  inputTopicTitle: document.getElementById('inputTopicTitle'),
  btnSubmitTopic: document.getElementById('btnSubmitTopic'),

  inputWeekTitle: document.getElementById('inputWeekTitle'),
  btnToggleWeekStatus: document.getElementById('btnToggleWeekStatus'),
  btnToggleWeekDesc: document.getElementById('btnToggleWeekDesc'),
  btnSubmitWeekTask: document.getElementById('btnSubmitWeekTask'),
  descBoxWeekTask: document.getElementById('descBoxWeekTask'),
  descWeekText: document.getElementById('descWeekText'),

  inputNoteTitle: document.getElementById('inputNoteTitle'),
  btnToggleNoteDesc: document.getElementById('btnToggleNoteDesc'),
  btnSubmitNote: document.getElementById('btnSubmitNote'),
  descBoxNote: document.getElementById('descBoxNote'),
  descNoteText: document.getElementById('descNoteText'),

  inputDefCode: document.getElementById('inputDefCode'),
  inputDefUrl: document.getElementById('inputDefUrl'),
  btnSubmitDef: document.getElementById('btnSubmitDef'),

  btnSoundToggle: document.getElementById('btnSoundToggle'),
  btnSync: document.getElementById('btnSync'),
  btnPwaInstall: document.getElementById('btnPwaInstall'),

  toastContainer: document.getElementById('toastContainer'),
  appModalOverlay: document.getElementById('appModalOverlay'),
  modalTitle: document.getElementById('modalTitle'),
  modalBody: document.getElementById('modalBody'),
  btnCloseModal: document.getElementById('btnCloseModal'),

  pomodoroBackdrop: document.getElementById('pomodoroBackdrop'),
  pomodoroWidget: document.getElementById('pomodoroFloatingWidget'),
  pomoDragHandle: document.getElementById('pomoDragHandle'),
  btnPomoBlurToggle: document.getElementById('btnPomoBlurToggle'),
  btnPomoMinimize: document.getElementById('btnPomoMinimize'),
  btnPomoClose: document.getElementById('btnPomoClose'),
  pomoTimeDisplay: document.getElementById('pomoTimeDisplay'),
  pomoTaskSelect: document.getElementById('pomoTaskSelect'),
  btnPomoStartPause: document.getElementById('btnPomoStartPause'),
  btnPomoReset: document.getElementById('btnPomoReset')
};

// ---------------------------------------------------------------------------
// Inicialización y Registro de PWA
// ---------------------------------------------------------------------------
// Cerrar popover de ubicación y menús desplegables al pulsar fuera o Esc
document.addEventListener('click', (e) => {
  if (!e.target.closest('#locationPopover') && !e.target.closest('.day-loc-btn')) {
    closeLocationPopover();
  }
  // No cerrar si el clic ocurre dentro del drawer, en el botón hamburguesa o en elementos de menú
  if (
    !e.target.closest('#hamburgerDrawer') &&
    !e.target.closest('#btnHamburger') &&
    !e.target.closest('.btn-hamburger') &&
    !e.target.closest('.menu-group')
  ) {
    closeAllTopMenuDropdowns();
  }
});

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    closeLocationPopover();
    closeAllTopMenuDropdowns();
    closeModal();
  }
});

window.addEventListener('resize', closeLocationPopover);

document.addEventListener('DOMContentLoaded', async () => {
  setupPwaInstall();
  setupEventListeners();
  setupPomodoroWidget();
  updateSoundToggleButton();
  setupCollapsibleSections();
  setupSectionReordering();
  renderHamburgerMenu([]);
  await loadVaults();
  await loadHub();
});

function setupCollapsibleSections() {
  const sections = document.querySelectorAll('.collapsible-section');
  sections.forEach((sec) => {
    const sectionId = sec.dataset.section;
    const btn = sec.querySelector('.section-header-btn');
    if (!sectionId || !btn) return;

    // Cargar estado persistido (localStorage). Por defecto 'false' (abierto)
    const isCollapsed = localStorage.getItem(`brackets_section_collapsed_${sectionId}`) === 'true';
    if (isCollapsed) {
      sec.classList.add('collapsed');
      btn.setAttribute('aria-expanded', 'false');
    } else {
      sec.classList.remove('collapsed');
      btn.setAttribute('aria-expanded', 'true');
    }

    btn.addEventListener('click', () => {
      const currentlyCollapsed = sec.classList.toggle('collapsed');
      btn.setAttribute('aria-expanded', currentlyCollapsed ? 'false' : 'true');
      localStorage.setItem(`brackets_section_collapsed_${sectionId}`, currentlyCollapsed ? 'true' : 'false');
    });
  });
}

function saveSectionsOrder() {
  const container = document.getElementById('sectionsContainer');
  if (!container) return;
  const sections = container.querySelectorAll(':scope > .collapsible-section');
  const order = Array.from(sections).map((s) => s.dataset.section).filter(Boolean);
  localStorage.setItem('brackets_sections_order', JSON.stringify(order));
}

function restoreSectionsOrder() {
  const container = document.getElementById('sectionsContainer');
  if (!container) return;
  const saved = localStorage.getItem('brackets_sections_order');
  if (!saved) return;
  try {
    const order = JSON.parse(saved);
    if (!Array.isArray(order)) return;
    order.forEach((key) => {
      const sec = container.querySelector(`:scope > .collapsible-section[data-section="${key}"]`);
      if (sec) {
        container.appendChild(sec);
      }
    });
  } catch (err) {
    console.error('Error restaurando orden de secciones:', err);
  }
}

function setupSectionReordering() {
  restoreSectionsOrder();
  const container = document.getElementById('sectionsContainer');
  if (!container) return;

  const sections = container.querySelectorAll(':scope > .collapsible-section');
  sections.forEach((sec) => {
    const btnUp = sec.querySelector('.btn-section-up');
    const btnDown = sec.querySelector('.btn-section-down');

    if (btnUp) {
      btnUp.addEventListener('click', (e) => {
        e.stopPropagation();
        const prev = sec.previousElementSibling;
        if (prev && prev.classList.contains('collapsible-section')) {
          sec.parentNode.insertBefore(sec, prev);
          saveSectionsOrder();
        }
      });
    }

    if (btnDown) {
      btnDown.addEventListener('click', (e) => {
        e.stopPropagation();
        const next = sec.nextElementSibling;
        if (next && next.classList.contains('collapsible-section')) {
          sec.parentNode.insertBefore(next, sec);
          saveSectionsOrder();
        }
      });
    }

    const handle = sec.querySelector('.section-drag-handle');
    if (handle) {
      handle.addEventListener('dragstart', (e) => {
        sec.classList.add('dragging-section');
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', sec.dataset.section);
      });

      handle.addEventListener('dragend', () => {
        sec.classList.remove('dragging-section');
        container.querySelectorAll('.drag-over-section').forEach(s => s.classList.remove('drag-over-section'));
        saveSectionsOrder();
      });
    }

    sec.addEventListener('dragover', (e) => {
      const draggingSec = container.querySelector('.dragging-section');
      if (!draggingSec || draggingSec === sec) return;
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      container.querySelectorAll('.drag-over-section').forEach(s => {
        if (s !== sec) s.classList.remove('drag-over-section');
      });
      sec.classList.add('drag-over-section');
    });

    sec.addEventListener('dragleave', () => {
      sec.classList.remove('drag-over-section');
    });

    sec.addEventListener('drop', (e) => {
      const draggingSec = container.querySelector('.dragging-section');
      sec.classList.remove('drag-over-section');
      if (draggingSec && draggingSec !== sec) {
        e.preventDefault();
        const allSecs = Array.from(container.children);
        const dragIdx = allSecs.indexOf(draggingSec);
        const targetIdx = allSecs.indexOf(sec);
        if (dragIdx < targetIdx) {
          sec.after(draggingSec);
        } else {
          sec.before(draggingSec);
        }
        saveSectionsOrder();
      }
    });
  });
}

// ---------------------------------------------------------------------------
// Reordenación de elementos (Tasks, Notes, Topics, Definitions)
// ---------------------------------------------------------------------------
async function saveItemsOrder(reorderType, container, dayNumber = null) {
  if (!container) return;
  const cards = container.querySelectorAll(':scope > [data-id]');
  const ids = Array.from(cards).map((c) => c.getAttribute('data-id')).filter(Boolean);
  try {
    await fetch('/api/reorder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        vault: state.currentVault,
        type: reorderType,
        ids: ids,
        day_number: dayNumber !== null ? dayNumber : state.activeDayNumber,
        year: state.activeYear,
        week: state.activeWeekNumber
      })
    });
  } catch (err) {
    console.error('Error al guardar nuevo orden de elementos:', err);
  }
}

function bindItemNavButtons(card, container, reorderType, dayNumber = null) {
  const btnUp = card.querySelector('.btn-item-up');
  const btnDown = card.querySelector('.btn-item-down');
  if (btnUp) {
    btnUp.onclick = async (e) => {
      e.stopPropagation();
      const prev = card.previousElementSibling;
      if (prev && prev.hasAttribute('data-id')) {
        card.parentNode.insertBefore(card, prev);
        await saveItemsOrder(reorderType, container, dayNumber);
      }
    };
  }
  if (btnDown) {
    btnDown.onclick = async (e) => {
      e.stopPropagation();
      const next = card.nextElementSibling;
      if (next && next.hasAttribute('data-id')) {
        card.parentNode.insertBefore(next, card);
        await saveItemsOrder(reorderType, container, dayNumber);
      }
    };
  }
}

let currentDraggedItem = null;

function setupDragAndDropForContainer(container, reorderType, dayNumber = null) {
  container.addEventListener('dragstart', (e) => {
    const handle = e.target.closest('.drag-handle-item');
    if (!handle) return;
    const card = handle.closest('[data-id]');
    if (!card) return;
    currentDraggedItem = card;
    card.classList.add('item-dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', card.getAttribute('data-id'));
  });

  container.addEventListener('dragover', (e) => {
    if (!currentDraggedItem) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    const targetCard = e.target.closest('[data-id]');
    if (!targetCard || targetCard === currentDraggedItem || targetCard.parentNode !== container) return;

    const rect = targetCard.getBoundingClientRect();
    const isAbove = e.clientY < rect.top + rect.height / 2;
    container.querySelectorAll('.item-drop-above, .item-drop-below').forEach((el) => {
      if (el !== targetCard) {
        el.classList.remove('item-drop-above', 'item-drop-below');
      }
    });

    if (isAbove) {
      targetCard.classList.add('item-drop-above');
      targetCard.classList.remove('item-drop-below');
    } else {
      targetCard.classList.add('item-drop-below');
      targetCard.classList.remove('item-drop-above');
    }
  });

  container.addEventListener('dragleave', (e) => {
    const targetCard = e.target.closest('[data-id]');
    if (targetCard) {
      targetCard.classList.remove('item-drop-above', 'item-drop-below');
    }
  });

  container.addEventListener('drop', async (e) => {
    if (!currentDraggedItem) return;
    e.preventDefault();
    const targetCard = e.target.closest('[data-id]');
    container.querySelectorAll('.item-drop-above, .item-drop-below').forEach((el) => {
      el.classList.remove('item-drop-above', 'item-drop-below');
    });

    if (targetCard && targetCard !== currentDraggedItem && targetCard.parentNode === container) {
      const rect = targetCard.getBoundingClientRect();
      const isAbove = e.clientY < rect.top + rect.height / 2;
      if (isAbove) {
        container.insertBefore(currentDraggedItem, targetCard);
      } else {
        container.insertBefore(currentDraggedItem, targetCard.nextSibling);
      }
      await saveItemsOrder(reorderType, container, dayNumber);
    }
  });

  container.addEventListener('dragend', () => {
    if (currentDraggedItem) {
      currentDraggedItem.classList.remove('item-dragging');
      currentDraggedItem = null;
    }
    container.querySelectorAll('.item-drop-above, .item-drop-below').forEach((el) => {
      el.classList.remove('item-drop-above', 'item-drop-below');
    });
  });
}

function isAppRunningStandalone() {
  return (
    window.matchMedia('(display-mode: standalone)').matches ||
    window.matchMedia('(display-mode: minimal-ui)').matches ||
    window.matchMedia('(display-mode: window-controls-overlay)').matches ||
    window.matchMedia('(display-mode: fullscreen)').matches ||
    ('standalone' in navigator && navigator.standalone === true) ||
    localStorage.getItem('brackets_pwa_installed') === 'true'
  );
}

function setupPwaInstall() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('./sw.js').catch((err) => {
      console.warn('Service Worker registration failed:', err);
    });
  }

  if (isAppRunningStandalone()) {
    if (el.btnPwaInstall) el.btnPwaInstall.style.display = 'none';
    return;
  }

  window.addEventListener('beforeinstallprompt', (e) => {
    if (isAppRunningStandalone()) {
      if (el.btnPwaInstall) el.btnPwaInstall.style.display = 'none';
      return;
    }
    e.preventDefault();
    state.deferredPrompt = e;
    if (el.btnPwaInstall) {
      el.btnPwaInstall.style.display = 'inline-flex';
    }
  });

  window.addEventListener('appinstalled', () => {
    localStorage.setItem('brackets_pwa_installed', 'true');
    if (el.btnPwaInstall) el.btnPwaInstall.style.display = 'none';
    state.deferredPrompt = null;
  });

  if (el.btnPwaInstall) {
    el.btnPwaInstall.addEventListener('click', async () => {
      if (!state.deferredPrompt) return;
      state.deferredPrompt.prompt();
      const { outcome } = await state.deferredPrompt.userChoice;
      if (outcome === 'accepted') {
        localStorage.setItem('brackets_pwa_installed', 'true');
        el.btnPwaInstall.style.display = 'none';
      }
      state.deferredPrompt = null;
    });
  }
}

// ---------------------------------------------------------------------------
// Sistema de Sonidos y Efectos (Web Audio API)
// ---------------------------------------------------------------------------
let audioCtx = null;

function getAudioContext() {
  if (!audioCtx) {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (AudioContextClass) {
      audioCtx = new AudioContextClass();
    }
  }
  if (audioCtx && audioCtx.state === 'suspended') {
    audioCtx.resume();
  }
  return audioCtx;
}

function isSoundEnabled() {
  const saved = localStorage.getItem('brackets_sound_enabled');
  return saved !== 'false';
}

function setSoundEnabled(enabled) {
  localStorage.setItem('brackets_sound_enabled', enabled ? 'true' : 'false');
  updateSoundToggleButton();
}

function updateSoundToggleButton() {
  if (!el.btnSoundToggle) return;
  const enabled = isSoundEnabled();
  const icon = enabled ? '🔊' : '🔇';
  const label = enabled ? 'Sonido: Activado' : 'Sonido: Silenciado';
  el.btnSoundToggle.innerHTML = `<span class="drawer-sound-icon">${icon}</span> <span class="drawer-sound-label">${label}</span>`;
  el.btnSoundToggle.title = enabled ? 'Sonido activado (clic para silenciar)' : 'Sonido silenciado (clic para activar)';
  el.btnSoundToggle.setAttribute('aria-label', enabled ? 'Silenciar sonidos' : 'Activar sonidos');
}

function playTone(ctx, freq, startTime, duration, type = 'sine', maxGain = 0.15) {
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();

  osc.type = type;
  osc.frequency.setValueAtTime(freq, startTime);

  gain.gain.setValueAtTime(0.0001, startTime);
  gain.gain.exponentialRampToValueAtTime(maxGain, startTime + 0.02);
  gain.gain.exponentialRampToValueAtTime(0.0001, startTime + duration);

  osc.connect(gain);
  gain.connect(ctx.destination);

  osc.start(startTime);
  osc.stop(startTime + duration + 0.05);
}

function playTaskDoneSound() {
  if (!isSoundEnabled()) return;
  try {
    const ctx = getAudioContext();
    if (!ctx) return;
    const now = ctx.currentTime;

    // Chime melodico suave: Sol5 (784Hz) -> Do6 (1046.5Hz)
    playTone(ctx, 784, now, 0.12, 'sine', 0.14);
    playTone(ctx, 1046.5, now + 0.08, 0.24, 'sine', 0.18);
    playTone(ctx, 1046.5 * 2, now + 0.08, 0.16, 'triangle', 0.04);
  } catch (err) {
    console.warn('No se pudo reproducir el sonido de tarea:', err);
  }
}

function playAllDoneSound() {
  if (!isSoundEnabled()) return;
  try {
    const ctx = getAudioContext();
    if (!ctx) return;
    const now = ctx.currentTime;

    // Fanfarria arpegiada alegre: C5 -> E5 -> G5 -> C6 -> E6 + acorde brillante
    const notes = [
      { f: 523.25, t: 0.00, d: 0.14, v: 0.13 },
      { f: 659.25, t: 0.09, d: 0.14, v: 0.14 },
      { f: 783.99, t: 0.18, d: 0.16, v: 0.16 },
      { f: 1046.50, t: 0.27, d: 0.35, v: 0.20 },
      { f: 1318.51, t: 0.35, d: 0.42, v: 0.18 },
      { f: 1567.98, t: 0.42, d: 0.50, v: 0.15 }
    ];

    notes.forEach((n) => {
      playTone(ctx, n.f, now + n.t, n.d, 'sine', n.v);
      playTone(ctx, n.f * 1.5, now + n.t, n.d * 0.7, 'triangle', n.v * 0.25);
    });
  } catch (err) {
    console.warn('No se pudo reproducir el sonido de fin de jornada:', err);
  }
}

function triggerCelebrationEffect() {
  const colors = ['#6366f1', '#10b981', '#f59e0b', '#ec4899', '#3b82f6', '#a855f7'];
  const container = document.createElement('div');
  container.className = 'celebration-container';
  container.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;pointer-events:none;z-index:9999;overflow:hidden;';

  const count = 36;
  for (let i = 0; i < count; i++) {
    const particle = document.createElement('div');
    const color = colors[Math.floor(Math.random() * colors.length)];
    const size = Math.floor(Math.random() * 8 + 6);
    const startX = window.innerWidth / 2 + (Math.random() * 240 - 120);
    const startY = window.innerHeight * 0.35;
    const destX = (Math.random() - 0.5) * window.innerWidth * 0.85;
    const destY = Math.random() * 320 + 80;
    const rotate = Math.random() * 720 - 360;

    particle.style.cssText = `
      position: absolute;
      top: ${startY}px;
      left: ${startX}px;
      width: ${size}px;
      height: ${size * (Math.random() > 0.5 ? 1 : 1.4)}px;
      background-color: ${color};
      border-radius: ${Math.random() > 0.5 ? '50%' : '2px'};
      opacity: 1;
      transform: translate(0, 0) rotate(0deg);
      transition: transform 1.2s cubic-bezier(0.25, 1, 0.5, 1), opacity 1.2s ease-out;
    `;
    container.appendChild(particle);

    requestAnimationFrame(() => {
      particle.style.transform = `translate(${destX}px, ${destY}px) rotate(${rotate}deg)`;
      particle.style.opacity = '0';
    });
  }

  document.body.appendChild(container);
  setTimeout(() => container.remove(), 1400);
}

function checkAndPlayTaskCompletion(taskId, sectionType) {
  if (sectionType === 'today_tasks') {
    const todayList = (state.hubData && state.hubData.today_tasks) ? state.hubData.today_tasks : [];
    const pendingTasks = todayList.filter((t) => !t.is_done && t.status !== 'done');
    const isThisPending = pendingTasks.some((t) => t.id === taskId);
    const remainingAfterThis = isThisPending ? pendingTasks.length - 1 : pendingTasks.length;

    if (todayList.length > 0 && remainingAfterThis === 0) {
      playAllDoneSound();
      triggerCelebrationEffect();
    } else {
      playTaskDoneSound();
    }
  } else {
    playTaskDoneSound();
  }
}

// ---------------------------------------------------------------------------
// Event Listeners
// ---------------------------------------------------------------------------

function setupEventListeners() {
  // Cambio de Vault
  if (el.vaultSelect) {
    el.vaultSelect.addEventListener('change', async (e) => {
      state.currentVault = e.target.value;
      state.activeYear = null;
      state.activeWeekNumber = null;
      state.activeDayNumber = null;
      await loadHub();
    });
  }

  // Cerrar modal con botón X o haciendo clic en el fondo
  if (el.btnCloseModal) {
    el.btnCloseModal.addEventListener('click', closeModal);
  }
  if (el.appModalOverlay) {
    el.appModalOverlay.addEventListener('click', (e) => {
      if (e.target === el.appModalOverlay) closeModal();
    });
  }

  // Menú Hamburguesa Drawer
  if (el.btnHamburger) {
    el.btnHamburger.addEventListener('click', (e) => {
      e.stopPropagation();
      openHamburgerMenu();
    });
  }
  if (el.btnCloseHamburger) {
    el.btnCloseHamburger.addEventListener('click', (e) => {
      e.stopPropagation();
      closeHamburgerMenu();
    });
  }
  if (el.hamburgerBackdrop) {
    el.hamburgerBackdrop.addEventListener('click', (e) => {
      e.stopPropagation();
      closeHamburgerMenu();
    });
  }

  // Navegación rápida de semanas y botones del banner
  if (el.btnPrevWeek) {
    el.btnPrevWeek.addEventListener('click', () => navigateAdjacentWeek(1));
  }
  if (el.btnNextWeek) {
    el.btnNextWeek.addEventListener('click', () => {
      if (el.btnNextWeek.classList.contains('is-create-next')) {
        executeMenuCommand('next_weekly');
      } else {
        navigateAdjacentWeek(-1);
      }
    });
  }
  if (el.weekBadge) {
    el.weekBadge.addEventListener('click', () => executeMenuCommand('switch_week'));
  }
  if (el.weightBadge) {
    el.weightBadge.addEventListener('click', () => executeMenuCommand('set_weight'));
  }
  if (el.btnQuickWeight) {
    el.btnQuickWeight.addEventListener('click', () => executeMenuCommand('set_weight'));
  }
  if (el.btnQuickExtraDay) {
    el.btnQuickExtraDay.addEventListener('click', () => executeMenuCommand('add_extra_day'));
  }
  if (el.btnQuickNewWeek) {
    el.btnQuickNewWeek.addEventListener('click', () => executeMenuCommand('next_weekly'));
  }

  // Botón Alternar Sonido
  if (el.btnSoundToggle) {
    el.btnSoundToggle.addEventListener('click', (e) => {
      e.stopPropagation();
      const nextState = !isSoundEnabled();
      setSoundEnabled(nextState);
      updateSoundToggleButton();
      if (nextState) {
        playTaskDoneSound();
      }
      showToast(nextState ? '🔊 Sonidos activados' : '🔇 Sonidos silenciados', 'info');
    });
  }

  // Botón Sincronizar
  if (el.btnSync) {
    el.btnSync.addEventListener('click', async () => {
      el.btnSync.style.opacity = '0.5';
      try {
        const res = await fetch('/api/sync', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            vault: state.currentVault,
            year: state.activeYear,
            week: state.activeWeekNumber
          })
        });
        const data = await res.json();
        if (data.status === 'ok') {
          showToast(`Sincronizada ${data.file || 'semana actual'}`, 'success');
          await loadHub();
        }
      } catch (err) {
        console.error('Error al sincronizar:', err);
      } finally {
        el.btnSync.style.opacity = '1';
      }
    });
  }

  // 1. Tareas de Hoy
  if (el.btnToggleTodayStatus) {
    el.btnToggleTodayStatus.addEventListener('click', () => {
      state.todayStatus = state.todayStatus === 'pending' ? 'done' : 'pending';
      el.btnToggleTodayStatus.textContent = state.todayStatus === 'done' ? '✓ Hecha [x]' : 'Pendiente [ ]';
      el.btnToggleTodayStatus.classList.toggle('done', state.todayStatus === 'done');
    });
  }

  if (el.btnToggleTodayDesc) {
    el.btnToggleTodayDesc.addEventListener('click', () => {
      if (!el.descBoxTodayTask) return;
      const isHidden = el.descBoxTodayTask.style.display === 'none';
      el.descBoxTodayTask.style.display = isHidden ? 'block' : 'none';
      el.btnToggleTodayDesc.classList.toggle('active', isHidden);
      if (isHidden && el.descTodayText) el.descTodayText.focus();
    });
  }

  if (el.btnSubmitTodayTask) {
    el.btnSubmitTodayTask.addEventListener('click', createTodayTask);
  }

  if (el.inputTodayTitle) {
    el.inputTodayTitle.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        createTodayTask();
      }
    });
  }

  if (el.descTodayText) {
    el.descTodayText.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        createTodayTask();
      }
    });
  }

  // 2. Topics de la Semana
  if (el.btnSubmitTopic) {
    el.btnSubmitTopic.addEventListener('click', createTopic);
  }

  if (el.inputTopicTitle) {
    el.inputTopicTitle.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        createTopic();
      }
    });
  }

  // 3. Tareas de la Semana
  if (el.btnToggleWeekStatus) {
    el.btnToggleWeekStatus.addEventListener('click', () => {
      state.weekStatus = state.weekStatus === 'pending' ? 'done' : 'pending';
      el.btnToggleWeekStatus.textContent = state.weekStatus === 'done' ? '✓ Hecha [x]' : 'Pendiente [ ]';
      el.btnToggleWeekStatus.classList.toggle('done', state.weekStatus === 'done');
    });
  }

  if (el.btnToggleWeekDesc) {
    el.btnToggleWeekDesc.addEventListener('click', () => {
      if (!el.descBoxWeekTask) return;
      const isHidden = el.descBoxWeekTask.style.display === 'none';
      el.descBoxWeekTask.style.display = isHidden ? 'block' : 'none';
      el.btnToggleWeekDesc.classList.toggle('active', isHidden);
      if (isHidden && el.descWeekText) el.descWeekText.focus();
    });
  }

  if (el.btnSubmitWeekTask) {
    el.btnSubmitWeekTask.addEventListener('click', createWeekTask);
  }

  if (el.inputWeekTitle) {
    el.inputWeekTitle.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        createWeekTask();
      }
    });
  }

  if (el.descWeekText) {
    el.descWeekText.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        createWeekTask();
      }
    });
  }

  // 4. Notas de la Semana
  if (el.btnToggleNoteDesc) {
    el.btnToggleNoteDesc.addEventListener('click', () => {
      if (!el.descBoxNote) return;
      const isHidden = el.descBoxNote.style.display === 'none';
      el.descBoxNote.style.display = isHidden ? 'block' : 'none';
      el.btnToggleNoteDesc.classList.toggle('active', isHidden);
      if (isHidden && el.descNoteText) el.descNoteText.focus();
    });
  }

  if (el.btnSubmitNote) {
    el.btnSubmitNote.addEventListener('click', createNote);
  }

  if (el.inputNoteTitle) {
    el.inputNoteTitle.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (el.descBoxNote && el.descBoxNote.style.display === 'none') {
          el.descBoxNote.style.display = 'block';
          if (el.btnToggleNoteDesc) el.btnToggleNoteDesc.classList.add('active');
          if (el.descNoteText) el.descNoteText.focus();
        } else {
          createNote();
        }
      }
    });
  }

  if (el.descNoteText) {
    el.descNoteText.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        createNote();
      }
    });
  }

  // 5. Definiciones y Enlaces
  if (el.btnSubmitDef) {
    el.btnSubmitDef.addEventListener('click', createDefinition);
  }

  if (el.inputDefCode) {
    el.inputDefCode.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (el.inputDefUrl && !el.inputDefUrl.value.trim() && !isTicketFormat(el.inputDefCode.value)) {
          el.inputDefUrl.focus();
        } else {
          createDefinition();
        }
      }
    });
  }

  if (el.inputDefUrl) {
    el.inputDefUrl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        createDefinition();
      }
    });
  }

  // Atajo N global para enfocar la creación de Tarea de Hoy
  document.addEventListener('keydown', (e) => {
    const isInput = ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName);
    if ((e.key === 'n' || e.key === 'N') && !isInput && !e.ctrlKey && !e.metaKey && !e.altKey) {
      e.preventDefault();
      if (el.inputTodayTitle) el.inputTodayTitle.focus();
    }
  });
}

function isTicketFormat(text) {
  if (!text) return false;
  const clean = text.replace(/[\[\]\U0001f3ab]/g, '').trim();
  return /^[A-Za-z]+-\d+$/.test(clean);
}

// ---------------------------------------------------------------------------
// Creación Directa en Cada Sección
// ---------------------------------------------------------------------------

async function createTodayTask() {
  if (!el.inputTodayTitle) return;
  const title = el.inputTodayTitle.value.trim();
  if (!title) {
    el.inputTodayTitle.focus();
    return;
  }
  const desc = el.descTodayText ? el.descTodayText.value.trim() : '';
  const target = state.activeDayNumber ? `day:${state.activeDayNumber}` : 'today';

  if (el.btnSubmitTodayTask) el.btnSubmitTodayTask.disabled = true;
  try {
    const res = await fetch('/api/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        vault: state.currentVault,
        title: title,
        target: target,
        status: state.todayStatus || 'pending',
        description: desc || null,
        year: state.activeYear,
        week: state.activeWeekNumber
      })
    });
    if (res.ok) {
      el.inputTodayTitle.value = '';
      if (el.descTodayText) el.descTodayText.value = '';
      if (el.descBoxTodayTask) el.descBoxTodayTask.style.display = 'none';
      if (el.btnToggleTodayDesc) el.btnToggleTodayDesc.classList.remove('active');
      await loadHub();
    }
  } catch (err) {
    console.error('Error creando tarea de hoy:', err);
  } finally {
    if (el.btnSubmitTodayTask) el.btnSubmitTodayTask.disabled = false;
    el.inputTodayTitle.focus();
  }
}

async function createTopic() {
  if (!el.inputTopicTitle) return;
  const title = el.inputTopicTitle.value.trim();
  if (!title) {
    el.inputTopicTitle.focus();
    return;
  }

  if (el.btnSubmitTopic) el.btnSubmitTopic.disabled = true;
  try {
    const res = await fetch('/api/topics', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        vault: state.currentVault,
        title: title,
        year: state.activeYear,
        week: state.activeWeekNumber
      })
    });
    if (res.ok) {
      el.inputTopicTitle.value = '';
      await loadHub();
    }
  } catch (err) {
    console.error('Error creando topic:', err);
  } finally {
    if (el.btnSubmitTopic) el.btnSubmitTopic.disabled = false;
    el.inputTopicTitle.focus();
  }
}

async function createWeekTask() {
  if (!el.inputWeekTitle) return;
  const title = el.inputWeekTitle.value.trim();
  if (!title) {
    el.inputWeekTitle.focus();
    return;
  }
  const desc = el.descWeekText ? el.descWeekText.value.trim() : '';

  if (el.btnSubmitWeekTask) el.btnSubmitWeekTask.disabled = true;
  try {
    const res = await fetch('/api/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        vault: state.currentVault,
        title: title,
        target: 'week',
        status: state.weekStatus || 'pending',
        description: desc || null,
        year: state.activeYear,
        week: state.activeWeekNumber
      })
    });
    if (res.ok) {
      el.inputWeekTitle.value = '';
      if (el.descWeekText) el.descWeekText.value = '';
      if (el.descBoxWeekTask) el.descBoxWeekTask.style.display = 'none';
      if (el.btnToggleWeekDesc) el.btnToggleWeekDesc.classList.remove('active');
      await loadHub();
    }
  } catch (err) {
    console.error('Error creando tarea semanal:', err);
  } finally {
    if (el.btnSubmitWeekTask) el.btnSubmitWeekTask.disabled = false;
    el.inputWeekTitle.focus();
  }
}

async function createNote() {
  if (!el.inputNoteTitle) return;
  const title = el.inputNoteTitle.value.trim();
  const rawContent = el.descNoteText ? el.descNoteText.value.trim() : '';

  if (!title && !rawContent) {
    el.inputNoteTitle.focus();
    return;
  }

  const bullets = rawContent
    ? rawContent.split('\n').map((l) => l.trim()).filter((l) => l.length > 0)
    : [];

  if (el.btnSubmitNote) el.btnSubmitNote.disabled = true;
  try {
    const res = await fetch('/api/notes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        vault: state.currentVault,
        title: title,
        content: bullets,
        year: state.activeYear,
        week: state.activeWeekNumber
      })
    });
    if (res.ok) {
      el.inputNoteTitle.value = '';
      if (el.descNoteText) el.descNoteText.value = '';
      if (el.descBoxNote) el.descBoxNote.style.display = 'none';
      if (el.btnToggleNoteDesc) el.btnToggleNoteDesc.classList.remove('active');
      await loadHub();
    }
  } catch (err) {
    console.error('Error creando nota:', err);
  } finally {
    if (el.btnSubmitNote) el.btnSubmitNote.disabled = false;
    el.inputNoteTitle.focus();
  }
}

async function createDefinition() {
  if (!el.inputDefCode) return;
  const code = el.inputDefCode.value.trim();
  const url = el.inputDefUrl ? el.inputDefUrl.value.trim() : '';

  if (!code) {
    el.inputDefCode.focus();
    return;
  }

  if (el.btnSubmitDef) el.btnSubmitDef.disabled = true;
  try {
    const res = await fetch('/api/definitions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        vault: state.currentVault,
        code: code,
        url: url || null,
        year: state.activeYear,
        week: state.activeWeekNumber
      })
    });
    if (res.ok) {
      el.inputDefCode.value = '';
      if (el.inputDefUrl) el.inputDefUrl.value = '';
      await loadHub();
    }
  } catch (err) {
    console.error('Error creando definición:', err);
  } finally {
    if (el.btnSubmitDef) el.btnSubmitDef.disabled = false;
    el.inputDefCode.focus();
  }
}

// ---------------------------------------------------------------------------
// Carga de Datos desde la API
// ---------------------------------------------------------------------------
async function loadVaults() {
  try {
    const res = await fetch('/api/vaults');
    const data = await res.json();
    if (!el.vaultSelect) return;
    el.vaultSelect.innerHTML = '';

    data.vaults.forEach((v) => {
      const opt = document.createElement('option');
      opt.value = v.name;
      opt.textContent = `${v.vault_type === 'personal' ? '🌱' : '💼'} ${v.name}`;
      el.vaultSelect.appendChild(opt);
    });

    if (data.vaults.length > 0) {
      state.currentVault = data.vaults[0].name;
    }
  } catch (err) {
    console.error('Error cargando vaults:', err);
  }
}

async function loadHub() {
  try {
    let url = `/api/hub?vault=${encodeURIComponent(state.currentVault || '')}`;
    if (state.activeDayNumber) {
      url += `&day=${state.activeDayNumber}`;
    }
    if (state.activeYear) {
      url += `&year=${state.activeYear}`;
    }
    if (state.activeWeekNumber) {
      url += `&week=${state.activeWeekNumber}`;
    }

    const res = await fetch(url);
    const data = await res.json();
    state.hubData = data;
    if (data.week) {
      state.activeYear = data.week.year;
      state.activeWeekNumber = data.week.week_number;
    }

    renderHub(data);
  } catch (err) {
    console.error('Error cargando Daily Hub:', err);
  }
}

// ---------------------------------------------------------------------------
// Renderizado de Componentes
// ---------------------------------------------------------------------------
function renderHub(data) {
  renderHamburgerMenu(data.top_menu || []);
  updatePomodoroTaskOptions(data);

  if (!data.week) {
    if (el.todayTasksList) {
      el.todayTasksList.innerHTML = `<div class="empty-state">${data.message || 'No hay semana activa.'}</div>`;
    }
    updateTaskCountBadge(el.todayCountBadge, []);
    updateTaskCountBadge(el.weekCountBadge, []);
    updateSimpleCountBadge(el.topicsCountBadge, 0);
    updateSimpleCountBadge(el.notesCountBadge, 0);
    updateSimpleCountBadge(el.defsCountBadge, 0);
    return;
  }

  // 1. Banner de Semana y flechas de navegación
  if (el.weekBadge) {
    el.weekBadge.textContent = `🗓️ Semana ${data.week.week_number} (${data.week.year})`;
  }
  const weeksList = data.available_weeks || [];
  const curKey = `${data.week.year}-W${String(data.week.week_number).padStart(2, '0')}`;
  const curIdx = weeksList.findIndex((w) => w.key === curKey);
  if (el.btnPrevWeek) {
    el.btnPrevWeek.disabled = (curIdx === -1 || curIdx >= weeksList.length - 1);
  }
  if (el.btnNextWeek) {
    if (curIdx <= 0) {
      // Semana más reciente: modo creación de siguiente semana (azul brillante)
      el.btnNextWeek.disabled = false;
      el.btnNextWeek.classList.add('is-create-next');
      el.btnNextWeek.title = 'Estás en la última semana. Clic para crear la siguiente bitácora semanal';
    } else {
      el.btnNextWeek.disabled = false;
      el.btnNextWeek.classList.remove('is-create-next');
      el.btnNextWeek.title = 'Semana siguiente';
    }
  }

  if (el.weightBadge) {
    if (data.week.weight) {
      el.weightBadge.textContent = `⚖️ ${data.week.weight} kg`;
      el.weightBadge.style.display = 'inline-block';
      if (el.btnQuickWeight) el.btnQuickWeight.style.display = 'none';
    } else {
      el.weightBadge.style.display = 'none';
      if (el.btnQuickWeight) el.btnQuickWeight.style.display = 'inline-block';
    }
  }

  // 2. Tira de Días con selector interactivo de ubicación en el emoji
  if (el.daysStrip) {
    el.daysStrip.innerHTML = '';
    data.days.forEach((day) => {
      const chip = document.createElement('div');
      chip.className = `day-chip ${day.is_active ? 'active' : ''} ${day.is_today ? 'today' : ''}`;
      const weekdayFallbacks = ['L', 'M', 'X', 'J', 'V', 'S', 'D'];
      const weekdayLetter = day.weekday_letter || weekdayFallbacks[data.days.indexOf(day) % 7] || 'L';
      chip.innerHTML = `
        <span class="day-weekday-letter" title="${escapeHtml(day.weekday_name || '')}">${escapeHtml(weekdayLetter)}</span>
        <button class="day-loc-btn" type="button" title="Cambiar ubicación (${day.location_emoji || '🏠'})" aria-label="Cambiar ubicación">
          <span class="day-loc-emoji">${day.location_emoji || '🏠'}</span>
        </button>
        <span class="day-number">Día ${day.day_number}</span>
        <span class="day-badge-count">${day.task_count} tareas</span>
      `;

      // Clic en el chip (fuera del botón de ubicación) selecciona el día activo
      chip.addEventListener('click', (e) => {
        if (e.target.closest('.day-loc-btn')) return;
        state.activeDayNumber = day.day_number;
        loadHub();
      });

      // Clic en el botón/emoji de ubicación abre el selector de ubicación
      const locBtn = chip.querySelector('.day-loc-btn');
      if (locBtn) {
        locBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          toggleLocationPopover(day.day_number, day.location_emoji || '🏠', locBtn);
        });
      }

      el.daysStrip.appendChild(chip);
    });
  }

  // 3. Encabezado del Día Activo (si existe en el DOM)
  if (data.active_day && el.activeDayTitle) {
    const noteText = data.active_day.location_note ? ` (${data.active_day.location_note})` : '';
    el.activeDayTitle.textContent = `${data.active_day.location_emoji} Día ${data.active_day.day_number}${noteText}`;
  }

  // Actualizar placeholder del input según el día activo
  if (el.inputTodayTitle) {
    if (data.active_day && !data.active_day.is_today) {
      el.inputTodayTitle.placeholder = `Nueva tarea para Día ${data.active_day.day_number}... (ej: Reunión: Sync #[PROYECTO])`;
    } else {
      el.inputTodayTitle.placeholder = `Nueva tarea para hoy... (ej: Reunión: Sync #[PROYECTO])`;
    }
  }

  // 4. Lista de Tareas de Hoy
  const activeDayNum = data.active_day ? data.active_day.day_number : (state.activeDayNumber || null);
  renderTaskList(el.todayTasksList, data.today_tasks, 'No hay tareas asignadas para hoy.', 'today_tasks', activeDayNum);
  updateTaskCountBadge(el.todayCountBadge, data.today_tasks);

  // 5. Lista de Tareas de la Semana
  renderTaskList(el.weekTasksList, data.week_tasks, 'No hay tareas semanales pendientes.', 'week_tasks', null);
  updateTaskCountBadge(el.weekCountBadge, data.week_tasks);

  // 5.5 Lista de Topics de la Semana
  renderTopicsList(data.topics);
  updateSimpleCountBadge(el.topicsCountBadge, (data.topics || []).length);

  // 6. Lista de Notas
  renderNotesList(data.notes);
  updateSimpleCountBadge(el.notesCountBadge, (data.notes || []).length);

  // 7. Lista de Definiciones y Enlaces
  renderDefinitionsList(data.definitions);
  updateSimpleCountBadge(el.defsCountBadge, (data.definitions || []).length);
}

function updateTaskCountBadge(badgeEl, tasks) {
  if (!badgeEl) return;
  const list = tasks || [];
  const total = list.length;
  const done = list.filter((t) => t.is_done || t.status === 'done').length;

  badgeEl.textContent = `[${done}/${total}]`;
  badgeEl.classList.remove('completed', 'in-progress', 'empty');

  if (total === 0) {
    badgeEl.classList.add('empty');
  } else if (done === total) {
    badgeEl.classList.add('completed');
  } else {
    badgeEl.classList.add('in-progress');
  }
}

function updateSimpleCountBadge(badgeEl, count) {
  if (!badgeEl) return;
  badgeEl.textContent = `[${count}]`;
  badgeEl.classList.remove('completed', 'in-progress', 'empty');
  if (count === 0) {
    badgeEl.classList.add('empty');
  } else {
    badgeEl.classList.add('completed');
  }
}

const LOCATION_OPTIONS = [
  { emoji: '🏠', label: 'Casa' },
  { emoji: '🚗', label: 'Oficina' },
  { emoji: '💻', label: 'Remoto' },
  { emoji: '🏖️', label: 'Libre' }
];

function closeLocationPopover() {
  const existing = document.getElementById('locationPopover');
  if (existing) {
    existing.remove();
  }
}

function toggleLocationPopover(dayNumber, currentEmoji, anchorEl) {
  const existing = document.getElementById('locationPopover');
  if (existing) {
    const prevDay = existing.dataset.dayNumber;
    existing.remove();
    if (prevDay === String(dayNumber)) {
      return;
    }
  }

  const popover = document.createElement('div');
  popover.id = 'locationPopover';
  popover.className = 'location-popover';
  popover.dataset.dayNumber = String(dayNumber);

  popover.innerHTML = `
    <div class="location-popover-header">Ubicación Día ${dayNumber}</div>
  `;

  LOCATION_OPTIONS.forEach((loc) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = `btn-popover-loc ${currentEmoji === loc.emoji ? 'active' : ''}`;
    btn.innerHTML = `
      <span class="loc-emoji">${loc.emoji}</span>
      <span class="loc-label">${loc.label}</span>
    `;
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      closeLocationPopover();
      try {
        await fetch(`/api/days/${dayNumber}/location`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            vault: state.currentVault,
            emoji: loc.emoji,
            year: state.activeYear,
            week: state.activeWeekNumber
          })
        });
        state.activeDayNumber = dayNumber;
        await loadHub();
      } catch (err) {
        console.error('Error al cambiar ubicación:', err);
      }
    });
    popover.appendChild(btn);
  });

  document.body.appendChild(popover);

  // Posicionar debajo del botón ancla
  const rect = anchorEl.getBoundingClientRect();
  popover.style.top = `${rect.bottom + 6}px`;
  popover.style.left = `${rect.left + rect.width / 2}px`;
  popover.style.transform = 'translateX(-50%)';

  const popoverRect = popover.getBoundingClientRect();
  if (popoverRect.left < 8) {
    popover.style.left = '8px';
    popover.style.transform = 'none';
  } else if (popoverRect.right > window.innerWidth - 8) {
    popover.style.left = `${window.innerWidth - popoverRect.width - 8}px`;
    popover.style.transform = 'none';
  }
}

function renderTaskList(container, tasks, emptyMsg, reorderType = null, dayNumber = null) {
  if (!container) return;
  container.innerHTML = '';
  if (!tasks || tasks.length === 0) {
    container.innerHTML = `<div class="empty-state">${emptyMsg}</div>`;
    return;
  }

  tasks.forEach((task) => {
    const card = document.createElement('div');
    card.className = `task-card ${task.is_done ? 'done' : ''} ${task.is_cancelled ? 'cancelled' : ''}`;
    card.setAttribute('data-id', task.id);

    function renderNormalView() {
      card.className = `task-card ${task.is_done ? 'done' : ''} ${task.is_cancelled ? 'cancelled' : ''}`;
      const premojiSpan = task.premoji ? `<span class="task-premoji">${task.premoji}</span>` : '';
      const projSpan = task.project_id ? `<span class="task-project-tag">${escapeHtml(task.project_id)}</span>` : '';

      let descHtml = '';
      if (task.description) {
        const lines = task.description.split('\n').filter((l) => l.trim().length > 0);
        descHtml = `<div class="task-desc-box">${lines.map((l) => `<div class="task-desc-line">💬 ${escapeHtml(l)}</div>`).join('')}</div>`;
      }

      const moveTodayBtn = (reorderType === 'week_tasks')
        ? `<button class="btn-item-action btn-move-today" type="button" title="Trasladar tarea a hoy"><span class="btn-move-today-icon">📅</span><span class="btn-move-today-label">Hoy</span></button>`
        : '';

      card.innerHTML = `
        <div class="task-main-row">
          <span class="drag-handle-item" draggable="true" title="Arrastrar para mover">⋮⋮</span>
          <input type="checkbox" class="task-checkbox" ${task.is_done ? 'checked' : ''}>
          <div class="task-content">
            ${premojiSpan}
            <span class="task-title">${escapeHtml(task.title)}</span>
            ${projSpan}
          </div>
          ${moveTodayBtn}
          <div class="item-reorder-btns">
            <button class="btn-item-nav btn-item-up" type="button" title="Subir">▲</button>
            <button class="btn-item-nav btn-item-down" type="button" title="Bajar">▼</button>
          </div>
        </div>
        ${descHtml}
      `;

      bindItemNavButtons(card, container, reorderType, dayNumber);

      const btnMoveToday = card.querySelector('.btn-move-today');
      if (btnMoveToday) {
        btnMoveToday.addEventListener('click', async (e) => {
          e.stopPropagation();
          const activeDay = (state.hubData && state.hubData.active_day) ? state.hubData.active_day.day_number : (state.activeDayNumber || 'today');
          btnMoveToday.disabled = true;
          try {
            const res = await fetch(`/api/tasks/${task.id}`, {
              method: 'PATCH',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                vault: state.currentVault,
                target: `day:${activeDay}`,
                year: state.activeYear,
                week: state.activeWeekNumber
              })
            });
            if (res.ok) {
              showToast(`Tarea trasladada a hoy (Día ${activeDay})`, 'success');
              await loadHub();
            }
          } catch (err) {
            console.error('Error al trasladar tarea a hoy:', err);
          } finally {
            btnMoveToday.disabled = false;
          }
        });
      }

      const chk = card.querySelector('.task-checkbox');
      chk.addEventListener('change', async (e) => {
        e.stopPropagation();
        const willBeDone = chk.checked;
        if (willBeDone) {
          checkAndPlayTaskCompletion(task.id, reorderType);
        }
        try {
          await fetch(`/api/tasks/${task.id}/toggle`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              vault: state.currentVault,
              year: state.activeYear,
              week: state.activeWeekNumber
            })
          });
          if (reorderType === 'week_tasks' && willBeDone) {
            showToast('Tarea completada y trasladada a hoy', 'success');
          }
          await loadHub();
        } catch (err) {
          console.error('Error al cambiar estado de tarea:', err);
        }
      });

      card.onclick = (e) => {
        if (e.target.closest('.task-checkbox') || e.target.closest('.edit-form-box') || e.target.closest('.drag-handle-item') || e.target.closest('.item-reorder-btns') || e.target.closest('.btn-move-today')) return;
        renderEditView();
      };
    }

    function renderEditView() {
      const fullTitle = task.project_id && !task.title.includes(task.project_id)
        ? `${task.title} #[${task.project_id}]`
        : task.title;

      const days = (state.hubData && state.hubData.days) ? state.hubData.days : [];
      const currentTarget = task.is_week_task ? 'week' : (task.day_number ? `day:${task.day_number}` : (state.activeDayNumber ? `day:${state.activeDayNumber}` : 'today'));

      let targetOpts = `<option value="week" ${task.is_week_task ? 'selected' : ''}>⏳ Tarea Semana</option>`;
      days.forEach((d) => {
        const isSel = (!task.is_week_task && task.day_number === d.day_number);
        targetOpts += `<option value="day:${d.day_number}" ${isSel ? 'selected' : ''}>${d.location_emoji || '📅'} Día ${d.day_number}</option>`;
      });

      card.innerHTML = `
        <div class="edit-form-box">
          <input class="edit-input edit-task-title" type="text" value="${escapeHtml(fullTitle)}" placeholder="Título de la tarea...">
          <textarea class="edit-textarea edit-task-desc" rows="2" placeholder="Descripción / sub-viñetas (opcional)...">${escapeHtml(task.description || '')}</textarea>
          <div class="edit-actions-row">
            <div class="edit-actions-left">
              <select class="edit-select edit-task-target">
                ${targetOpts}
              </select>
              <select class="edit-select edit-task-status">
                <option value="pending" ${task.status === 'pending' ? 'selected' : ''}>[ ] Pendiente</option>
                <option value="done" ${task.status === 'done' ? 'selected' : ''}>[x] Hecha</option>
                <option value="cancelled" ${task.status === 'cancelled' ? 'selected' : ''}>[~] Cancelada</option>
              </select>
            </div>
            <div class="edit-actions-right">
              <button class="btn-edit-save btn-save-task" type="button">Guardar ✓</button>
              <button class="btn-edit-cancel btn-cancel-task" type="button">Cancelar ✕</button>
              <button class="btn-edit-delete btn-delete-task" title="Eliminar tarea" type="button">🗑️</button>
            </div>
          </div>
        </div>
      `;

      const inputTitle = card.querySelector('.edit-task-title');
      const inputDesc = card.querySelector('.edit-task-desc');
      const selectTarget = card.querySelector('.edit-task-target');
      const selectStatus = card.querySelector('.edit-task-status');
      const btnSave = card.querySelector('.btn-save-task');
      const btnCancel = card.querySelector('.btn-cancel-task');
      const btnDelete = card.querySelector('.btn-delete-task');

      inputTitle.focus();

      async function saveTask() {
        const newTitle = inputTitle.value.trim();
        if (!newTitle) return;
        const wasDone = task.is_done || task.status === 'done';
        const nowDone = selectStatus.value === 'done';
        if (!wasDone && nowDone) {
          checkAndPlayTaskCompletion(task.id, selectTarget.value === 'week' ? 'week_tasks' : 'today_tasks');
        }
        btnSave.disabled = true;
        try {
          const res = await fetch(`/api/tasks/${task.id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              vault: state.currentVault,
              title: newTitle,
              description: inputDesc.value.trim() || null,
              target: selectTarget.value,
              status: selectStatus.value,
              year: state.activeYear,
              week: state.activeWeekNumber
            })
          });
          if (res.ok) {
            await loadHub();
          }
        } catch (err) {
          console.error('Error guardando tarea:', err);
        } finally {
          btnSave.disabled = false;
        }
      }

      const editBox = card.querySelector('.edit-form-box');
      if (editBox) editBox.onclick = (e) => e.stopPropagation();

      btnSave.addEventListener('click', (e) => { e.stopPropagation(); saveTask(); });
      btnCancel.addEventListener('click', (e) => { e.stopPropagation(); renderNormalView(); });

      btnDelete.addEventListener('click', async () => {
        if (!confirm(`¿Eliminar la tarea "${task.title}"?`)) return;
        btnDelete.disabled = true;
        try {
          const res = await fetch(`/api/tasks/${task.id}?vault=${encodeURIComponent(state.currentVault || '')}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              vault: state.currentVault,
              year: state.activeYear,
              week: state.activeWeekNumber
            })
          });
          if (res.ok) {
            await loadHub();
          }
        } catch (err) {
          console.error('Error eliminando tarea:', err);
        }
      });

      inputTitle.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); saveTask(); }
        if (e.key === 'Escape') { renderNormalView(); }
      });
      inputDesc.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); saveTask(); }
        if (e.key === 'Escape') { renderNormalView(); }
      });
    }

    renderNormalView();
    container.appendChild(card);
  });
  if (reorderType) {
    setupDragAndDropForContainer(container, reorderType, dayNumber);
  }
}

function renderNotesList(notes) {
  if (!el.notesContainer) return;
  el.notesContainer.innerHTML = '';
  if (!notes || notes.length === 0) {
    el.notesContainer.innerHTML = `<div class="empty-state">No hay notas registradas en esta semana.</div>`;
    return;
  }

  notes.forEach((note) => {
    const card = document.createElement('div');
    card.className = 'note-card';
    card.setAttribute('data-id', note.id);

    function renderNormalView() {
      const bulletsHtml = (note.content || [])
        .map((b) => `<li class="note-bullet">${escapeHtml(b)}</li>`)
        .join('');

      card.innerHTML = `
        <div class="note-header" style="display:flex; align-items:center; justify-content:space-between;">
          <div style="display:flex; align-items:center; gap:8px;">
            <span class="drag-handle-item" draggable="true" title="Arrastrar para mover">⋮⋮</span>
            <span>📌 ${escapeHtml(note.title || 'Nota')}</span>
            ${note.project_id ? `<span class="task-project-tag">${escapeHtml(note.project_id)}</span>` : ''}
          </div>
          <div class="item-reorder-btns">
            <button class="btn-item-nav btn-item-up" type="button" title="Subir">▲</button>
            <button class="btn-item-nav btn-item-down" type="button" title="Bajar">▼</button>
          </div>
        </div>
        ${bulletsHtml ? `<ul>${bulletsHtml}</ul>` : ''}
      `;

      bindItemNavButtons(card, el.notesContainer, 'notes', null);

      card.onclick = (e) => {
        if (e.target.closest('.edit-form-box') || e.target.closest('.drag-handle-item') || e.target.closest('.item-reorder-btns')) return;
        renderEditView();
      };
    }

    function renderEditView() {
      const fullTitle = note.project_id && note.title && !note.title.includes(note.project_id)
        ? `${note.title} #[${note.project_id}]`
        : (note.title || '');

      card.innerHTML = `
        <div class="edit-form-box">
          <input class="edit-input edit-note-title" type="text" value="${escapeHtml(fullTitle)}" placeholder="Título de la nota (ej: Decisiones #[Proyecto])">
          <textarea class="edit-textarea edit-note-content" rows="4" placeholder="Viñetas (una por línea)...">${escapeHtml((note.content || []).join('\n'))}</textarea>
          <div class="edit-actions-row">
            <div class="edit-actions-left"></div>
            <div class="edit-actions-right">
              <button class="btn-edit-save btn-save-note" type="button">Guardar ✓</button>
              <button class="btn-edit-cancel btn-cancel-note" type="button">Cancelar ✕</button>
              <button class="btn-edit-delete btn-delete-note" title="Eliminar nota" type="button">🗑️</button>
            </div>
          </div>
        </div>
      `;

      const inputTitle = card.querySelector('.edit-note-title');
      const inputContent = card.querySelector('.edit-note-content');
      const btnSave = card.querySelector('.btn-save-note');
      const btnCancel = card.querySelector('.btn-cancel-note');
      const btnDelete = card.querySelector('.btn-delete-note');

      inputTitle.focus();

      async function saveNote() {
        const rawContent = inputContent.value.trim();
        const bullets = rawContent ? rawContent.split('\n').map((l) => l.trim()).filter((l) => l.length > 0) : [];
        btnSave.disabled = true;
        try {
          const res = await fetch(`/api/notes/${note.id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              vault: state.currentVault,
              title: inputTitle.value.trim(),
              content: bullets,
              year: state.activeYear,
              week: state.activeWeekNumber
            })
          });
          if (res.ok) {
            await loadHub();
          }
        } catch (err) {
          console.error('Error guardando nota:', err);
        } finally {
          btnSave.disabled = false;
        }
      }

      const editBox = card.querySelector('.edit-form-box');
      if (editBox) editBox.onclick = (e) => e.stopPropagation();

      btnSave.addEventListener('click', (e) => { e.stopPropagation(); saveNote(); });
      btnCancel.addEventListener('click', (e) => { e.stopPropagation(); renderNormalView(); });

      btnDelete.addEventListener('click', async () => {
        if (!confirm(`¿Eliminar la nota "${note.title || note.id}"?`)) return;
        btnDelete.disabled = true;
        try {
          const res = await fetch(`/api/notes/${note.id}?vault=${encodeURIComponent(state.currentVault || '')}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              vault: state.currentVault,
              year: state.activeYear,
              week: state.activeWeekNumber
            })
          });
          if (res.ok) {
            await loadHub();
          }
        } catch (err) {
          console.error('Error eliminando nota:', err);
        }
      });

      inputTitle.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); saveNote(); }
        if (e.key === 'Escape') { renderNormalView(); }
      });
      inputContent.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); saveNote(); }
        if (e.key === 'Escape') { renderNormalView(); }
      });
    }

    renderNormalView();
    el.notesContainer.appendChild(card);
  });
  setupDragAndDropForContainer(el.notesContainer, 'notes', null);
}

function parseDefinitionDisplay(def) {
  let raw = (def.id || '').trim();
  if (raw.startsWith('[') && raw.endsWith(']')) {
    raw = raw.slice(1, -1).trim();
  }

  let icon = '🔗';
  let badgeType = 'link';
  let code = raw;

  if (raw.includes('🎫')) {
    icon = '🎫';
    badgeType = 'jira';
    code = raw.replace(/🎫/g, '').trim();
  } else if (raw.includes('📊')) {
    icon = '📊';
    badgeType = 'dashboard';
    code = raw.replace(/📊/g, '').trim();
  } else if (raw.includes('🤖') || raw.includes('🧠') || raw.includes('🥑')) {
    icon = '🤖';
    badgeType = 'ai';
    code = raw.replace(/[🤖🧠🥑]/g, '').trim();
  } else if (def.type === 'jira' || /^[A-Za-z0-9]+-\d+$/i.test(code)) {
    icon = '🎫';
    badgeType = 'jira';
  }

  let title = (def.title || '').trim();
  if (title.startsWith('[') && title.endsWith(']')) {
    title = title.slice(1, -1).trim();
  }
  title = title.replace(/[🎫📊🤖🧠🥑]/g, '').trim();

  const showTitle = Boolean(title && title.toLowerCase() !== code.toLowerCase());

  return { icon, badgeType, code, showTitle, title };
}

function renderDefinitionsList(definitions) {
  if (!el.definitionsContainer) return;
  el.definitionsContainer.innerHTML = '';
  if (!definitions || definitions.length === 0) {
    el.definitionsContainer.innerHTML = `<div class="empty-state">No hay definiciones ni enlaces en esta semana.</div>`;
    return;
  }

  definitions.forEach((def) => {
    const card = document.createElement('div');
    card.className = 'definition-card';
    card.setAttribute('data-id', def.id);

    function renderNormalView() {
      const parsed = parseDefinitionDisplay(def);
      const titleHtml = parsed.showTitle ? `<span class="def-custom-title">${escapeHtml(parsed.title)}</span>` : '';
      const linkHtml = def.url
        ? `<a href="${escapeHtml(def.url)}" class="def-url-link" target="_blank" rel="noopener noreferrer" title="Abrir: ${escapeHtml(def.url)}">
             <span class="def-url-text">${escapeHtml(def.url)}</span>
             <span class="def-link-arrow">↗</span>
           </a>`
        : '<span class="def-no-link">(Sin URL asignada)</span>';

      card.innerHTML = `
        <div class="def-main-row">
          <span class="drag-handle-item" draggable="true" title="Arrastrar para mover">⋮⋮</span>
          <div class="def-badge def-badge-${parsed.badgeType}">
            <span class="def-badge-icon">${parsed.icon}</span>
            <span class="def-badge-code">${escapeHtml(parsed.code)}</span>
          </div>
          ${titleHtml}
          ${linkHtml}
          <div class="item-reorder-btns">
            <button class="btn-item-nav btn-item-up" type="button" title="Subir">▲</button>
            <button class="btn-item-nav btn-item-down" type="button" title="Bajar">▼</button>
          </div>
        </div>
      `;

      bindItemNavButtons(card, el.definitionsContainer, 'definitions', null);

      card.onclick = (e) => {
        if (e.target.closest('.def-url-link') || e.target.closest('.edit-form-box') || e.target.closest('.drag-handle-item') || e.target.closest('.item-reorder-btns')) return;
        renderEditView();
      };
    }

    function renderEditView() {
      card.innerHTML = `
        <div class="edit-form-box">
          <div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:6px;">
            <input class="edit-input edit-def-code" style="flex:0 0 180px;" type="text" value="${escapeHtml(def.id)}" placeholder="Código (ej: [🎫EXP-119781])">
            <input class="edit-input edit-def-url" style="flex:1; min-width:200px;" type="text" value="${escapeHtml(def.url || '')}" placeholder="URL">
          </div>
          <div class="edit-actions-row">
            <div class="edit-actions-left"></div>
            <div class="edit-actions-right">
              <button class="btn-edit-save btn-save-def" type="button">Guardar ✓</button>
              <button class="btn-edit-cancel btn-cancel-def" type="button">Cancelar ✕</button>
              <button class="btn-edit-delete btn-delete-def" title="Eliminar definición" type="button">🗑️</button>
            </div>
          </div>
        </div>
      `;

      const inputCode = card.querySelector('.edit-def-code');
      const inputUrl = card.querySelector('.edit-def-url');
      const btnSave = card.querySelector('.btn-save-def');
      const btnCancel = card.querySelector('.btn-cancel-def');
      const btnDelete = card.querySelector('.btn-delete-def');

      inputCode.focus();

      async function saveDef() {
        const newCode = inputCode.value.trim();
        if (!newCode) return;
        btnSave.disabled = true;
        try {
          const res = await fetch(`/api/definitions/${encodeURIComponent(def.id)}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              vault: state.currentVault,
              new_id: newCode,
              url: inputUrl.value.trim() || null,
              year: state.activeYear,
              week: state.activeWeekNumber
            })
          });
          if (res.ok) {
            await loadHub();
          }
        } catch (err) {
          console.error('Error guardando definición:', err);
        } finally {
          btnSave.disabled = false;
        }
      }

      const editBox = card.querySelector('.edit-form-box');
      if (editBox) editBox.onclick = (e) => e.stopPropagation();

      btnSave.addEventListener('click', (e) => { e.stopPropagation(); saveDef(); });
      btnCancel.addEventListener('click', (e) => { e.stopPropagation(); renderNormalView(); });

      btnDelete.addEventListener('click', async () => {
        if (!confirm(`¿Eliminar la definición "${def.id}"?`)) return;
        btnDelete.disabled = true;
        try {
          const res = await fetch(`/api/definitions/${encodeURIComponent(def.id)}?vault=${encodeURIComponent(state.currentVault || '')}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              vault: state.currentVault,
              year: state.activeYear,
              week: state.activeWeekNumber
            })
          });
          if (res.ok) {
            await loadHub();
          }
        } catch (err) {
          console.error('Error eliminando definición:', err);
        }
      });

      inputCode.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); saveDef(); }
        if (e.key === 'Escape') { renderNormalView(); }
      });
      inputUrl.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); saveDef(); }
        if (e.key === 'Escape') { renderNormalView(); }
      });
    }

    renderNormalView();
    el.definitionsContainer.appendChild(card);
  });
  setupDragAndDropForContainer(el.definitionsContainer, 'definitions', null);
}

// ---------------------------------------------------------------------------
// Acciones de Creación (Tareas, Notas y Definiciones)
// ---------------------------------------------------------------------------
// Helper de escape HTML
function escapeHtml(text) {
  if (!text) return '';
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function renderTopicsList(topics) {
  if (!el.topicsContainer) return;
  el.topicsContainer.innerHTML = '';
  if (!topics || topics.length === 0) {
    el.topicsContainer.innerHTML = '<div class="empty-state">No hay topics definidos en esta semana.</div>';
    return;
  }

  topics.forEach((topic) => {
    const card = document.createElement('div');
    card.className = 'topic-card';
    card.setAttribute('data-id', topic.id);

    function renderNormalView() {
      const projTag = topic.project_id ? `<span class="task-project-tag">${escapeHtml(topic.project_id)}</span>` : '';
      card.innerHTML = `
        <div class="topic-main-info" style="display:flex; align-items:center; gap:8px; width:100%;">
          <span class="drag-handle-item" draggable="true" title="Arrastrar para mover">⋮⋮</span>
          <span>🎯</span>
          <span class="topic-title">${escapeHtml(topic.title)}</span>
          ${projTag}
          <div class="item-reorder-btns">
            <button class="btn-item-nav btn-item-up" type="button" title="Subir">▲</button>
            <button class="btn-item-nav btn-item-down" type="button" title="Bajar">▼</button>
          </div>
        </div>
      `;

      bindItemNavButtons(card, el.topicsContainer, 'topics', null);

      card.onclick = (e) => {
        if (e.target.closest('.edit-form-box') || e.target.closest('.drag-handle-item') || e.target.closest('.item-reorder-btns')) return;
        renderEditView();
      };
    }

    function renderEditView() {
      const fullTitle = topic.project_id && topic.project_id !== 'GENERAL' && !topic.title.includes(topic.project_id)
        ? `${topic.title} #[${topic.project_id}]`
        : topic.title;

      card.innerHTML = `
        <div class="edit-form-box">
          <input class="edit-input edit-topic-title" type="text" value="${escapeHtml(fullTitle)}" placeholder="Título del topic (ej: Core Engine #[Core])">
          <div class="edit-actions-row">
            <div class="edit-actions-left"></div>
            <div class="edit-actions-right">
              <button class="btn-edit-save btn-save-topic" type="button">Guardar ✓</button>
              <button class="btn-edit-cancel btn-cancel-topic" type="button">Cancelar ✕</button>
              <button class="btn-edit-delete btn-delete-topic" title="Eliminar topic" type="button">🗑️</button>
            </div>
          </div>
        </div>
      `;

      const inputTitle = card.querySelector('.edit-topic-title');
      const btnSave = card.querySelector('.btn-save-topic');
      const btnCancel = card.querySelector('.btn-cancel-topic');
      const btnDelete = card.querySelector('.btn-delete-topic');

      inputTitle.focus();

      async function saveTopic() {
        const newTitle = inputTitle.value.trim();
        if (!newTitle) return;
        btnSave.disabled = true;
        try {
          const res = await fetch(`/api/topics/${topic.id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              vault: state.currentVault,
              title: newTitle,
              year: state.activeYear,
              week: state.activeWeekNumber
            })
          });
          if (res.ok) {
            await loadHub();
          }
        } catch (err) {
          console.error('Error guardando topic:', err);
        } finally {
          btnSave.disabled = false;
        }
      }

      const editBox = card.querySelector('.edit-form-box');
      if (editBox) editBox.onclick = (e) => e.stopPropagation();

      btnSave.addEventListener('click', (e) => { e.stopPropagation(); saveTopic(); });
      btnCancel.addEventListener('click', (e) => { e.stopPropagation(); renderNormalView(); });

      btnDelete.addEventListener('click', async () => {
        if (!confirm(`¿Eliminar el topic "${topic.title}"?`)) return;
        btnDelete.disabled = true;
        try {
          const res = await fetch(`/api/topics/${topic.id}?vault=${encodeURIComponent(state.currentVault || '')}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              vault: state.currentVault,
              year: state.activeYear,
              week: state.activeWeekNumber
            })
          });
          if (res.ok) {
            await loadHub();
          }
        } catch (err) {
          console.error('Error eliminando topic:', err);
        }
      });

      inputTitle.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); saveTopic(); }
        if (e.key === 'Escape') { renderNormalView(); }
      });
    }

    renderNormalView();
    el.topicsContainer.appendChild(card);
  });
  setupDragAndDropForContainer(el.topicsContainer, 'topics', null);
}

// ---------------------------------------------------------------------------
// Sistema de Notificaciones Toast y Modales
// ---------------------------------------------------------------------------
function showToast(message, type = 'info') {
  if (!el.toastContainer) return;
  const toast = document.createElement('div');
  toast.className = `toast-msg ${type}`;
  toast.textContent = message;
  el.toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.25s ease';
    setTimeout(() => toast.remove(), 260);
  }, 3200);
}

function openModal(title, htmlContent) {
  if (!el.appModalOverlay || !el.modalTitle || !el.modalBody) return;
  el.modalTitle.textContent = title;
  el.modalBody.innerHTML = htmlContent;
  el.appModalOverlay.style.display = 'flex';
}

function closeModal() {
  if (el.appModalOverlay) {
    el.appModalOverlay.style.display = 'none';
  }
}

// ---------------------------------------------------------------------------
// ---------------------------------------------------------------------------
// Menú Hamburguesa Declarativo (Acciones CLI en Web Hub)
// ---------------------------------------------------------------------------
let lastRenderedMenuJson = '';

function openHamburgerMenu() {
  if (el.hamburgerDrawer) el.hamburgerDrawer.style.display = 'flex';
  if (el.hamburgerBackdrop) el.hamburgerBackdrop.style.display = 'block';
  if (el.btnHamburger) el.btnHamburger.setAttribute('aria-expanded', 'true');
}

function closeHamburgerMenu() {
  if (el.hamburgerDrawer) el.hamburgerDrawer.style.display = 'none';
  if (el.hamburgerBackdrop) el.hamburgerBackdrop.style.display = 'none';
  if (el.btnHamburger) el.btnHamburger.setAttribute('aria-expanded', 'false');
}

function renderHamburgerMenu(groups) {
  if (!el.hamburgerMenuContent || !Array.isArray(groups) || groups.length === 0) return;
  const jsonKey = JSON.stringify(groups);
  if (jsonKey === lastRenderedMenuJson) return;
  lastRenderedMenuJson = jsonKey;

  el.hamburgerMenuContent.innerHTML = '';
  groups.forEach((group) => {
    const groupDiv = document.createElement('div');
    groupDiv.className = 'hamburger-group';
    groupDiv.dataset.groupId = group.id;

    const title = document.createElement('div');
    title.className = 'hamburger-group-title';
    title.textContent = group.label;
    groupDiv.appendChild(title);

    (group.items || []).forEach((item) => {
      if (item.command === 'set_weight') return; // Omitir peso en notas generales/trabajo

      const itemBtn = document.createElement('button');
      itemBtn.type = 'button';
      itemBtn.className = 'hamburger-item-btn';
      itemBtn.dataset.command = item.command;
      itemBtn.innerHTML = `<span>${escapeHtml(item.label)}</span>`;
      itemBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        closeHamburgerMenu();
        executeMenuCommand(item.command);
      });
      groupDiv.appendChild(itemBtn);
    });

    el.hamburgerMenuContent.appendChild(groupDiv);
  });
}

// Alias para compatibilidad
function renderTopMenuBar(groups) {
  renderHamburgerMenu(groups);
}

async function navigateAdjacentWeek(offsetIndex) {
  const weeks = (state.hubData && state.hubData.available_weeks) ? state.hubData.available_weeks : [];
  if (!weeks.length || !state.hubData || !state.hubData.week) return;
  const curKey = `${state.hubData.week.year}-W${String(state.hubData.week.week_number).padStart(2, '0')}`;
  const curIdx = weeks.findIndex((w) => w.key === curKey);
  const targetIdx = curIdx + offsetIndex;
  if (targetIdx >= 0 && targetIdx < weeks.length) {
    const target = weeks[targetIdx];
    state.activeYear = target.year;
    state.activeWeekNumber = target.week_number;
    state.activeDayNumber = null;
    await loadHub();
    showToast(`Semana ${target.week_number} (${target.year}) cargada`, 'info');
  }
}

async function executeMenuCommand(command) {
  switch (command) {
    case 'next_weekly':
      return openNextWeeklyModal();
    case 'switch_week':
      return openSwitchWeekModal();
    case 'add_extra_day':
      return openAddExtraDayModal();
    case 'set_weight':
      return openSetWeightModal();
    case 'sync_current_week':
      return runSyncCurrentWeek();
    case 'sync_all_weeks':
      return runSyncAllWeeks();
    case 'apply_recurring':
      return runApplyRecurring();
    case 'manage_recurring':
      return openManageRecurringModal();
    case 'apply_calendar':
      return runApplyCalendar();
    case 'projects_overview':
      return openProjectsOverviewModal();
    case 'backlog_manager':
      return openBacklogManagerModal();
    case 'ideas_manager':
      return openIdeasManagerModal();
    case 'schedule_week_to_today':
      return openScheduleWeekToTodayModal();
    case 'consolidate_month':
      return openConsolidateMonthModal();
    case 'consolidate_year':
      return openConsolidateYearModal();
    case 'pomodoro_timer':
      return togglePomodoroWidget(true);
    case 'work_calendar':
      return openWorkCalendarModal();
    case 'toggle_all_sections':
      return toggleAllCollapsibleSections();
    default:
      showToast(`Comando no reconocido: ${command}`, 'error');
  }
}

// ---------------------------------------------------------------------------
// Implementación de Comandos y Modales CLI
// ---------------------------------------------------------------------------
function openNextWeeklyModal() {
  const curWeight = (state.hubData && state.hubData.week && state.hubData.week.weight) ? state.hubData.week.weight : '';
  openModal('➕ Crear Siguiente Bitácora Semanal', `
    <p style="color:var(--text-muted);">
      Genera automáticamente la siguiente semana ISO, arrastra las tareas pendientes de la semana actual (aplicando la regla de 2 semanas hacia el Backlog), asigna ubicaciones según tu calendario laboral e inyecta las tareas recurrentes activas.
    </p>
    <div class="modal-form-row">
      <input id="modalNextWeekWeight" class="edit-input" style="flex:1;" type="number" step="0.1" placeholder="Peso semanal opcional en kg (ej: 81.5)" value="${escapeHtml(String(curWeight))}">
      <button id="btnConfirmNextWeek" class="btn-edit-save" type="button">Crear Semana ➔</button>
    </div>
  `);

  const btn = document.getElementById('btnConfirmNextWeek');
  const inputWeight = document.getElementById('modalNextWeekWeight');
  if (btn) {
    btn.addEventListener('click', async () => {
      btn.disabled = true;
      try {
        const wVal = inputWeight && inputWeight.value.trim() ? parseFloat(inputWeight.value.trim()) : null;
        const res = await fetch('/api/weeks/next', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ vault: state.currentVault, weight: wVal })
        });
        const data = await res.json();
        if (res.ok && data.success) {
          closeModal();
          state.activeYear = data.year;
          state.activeWeekNumber = data.week_number;
          state.activeDayNumber = null;
          await loadHub();
          playTaskDoneSound();
          showToast(`Creada Semana ${data.week_number} (${data.rolled_tasks} arrastradas, ${data.injected_recurring} recurrentes)`, 'success');
        } else {
          showToast(data.error || 'Error creando semana', 'error');
        }
      } catch (err) {
        showToast('Error de red al crear semana', 'error');
      } finally {
        btn.disabled = false;
      }
    });
  }
}

async function openSwitchWeekModal() {
  openModal('🗓️ Cambiar / Navegar Semana', `<div style="color:var(--text-muted);">Cargando semanas...</div>`);
  try {
    const res = await fetch(`/api/weeks?vault=${encodeURIComponent(state.currentVault || '')}`);
    const data = await res.json();
    const weeks = data.weeks || [];
    const curKey = state.hubData && state.hubData.week
      ? `${state.hubData.week.year}-W${String(state.hubData.week.week_number).padStart(2, '0')}`
      : '';

    let listHtml = weeks.map((w) => {
      const isCurrent = w.key === curKey;
      return `
        <div class="modal-list-item" style="${isCurrent ? 'border-color:var(--accent);background:var(--accent-soft);' : ''}">
          <div>
            <strong>🗓️ Semana ${w.week_number} (${w.year})</strong>
            <span style="color:var(--text-dim);font-size:0.78rem;margin-left:8px;">${escapeHtml(w.file || w.key)}</span>
          </div>
          <button type="button" class="btn-edit-save btn-select-week" data-year="${w.year}" data-week="${w.week_number}">
            ${isCurrent ? 'Activa ✓' : 'Abrir'}
          </button>
        </div>
      `;
    }).join('');

    if (!listHtml) {
      listHtml = `<div class="empty-state">No hay semanas registradas en este vault.</div>`;
    }

    el.modalBody.innerHTML = `
      <div class="modal-section-title">Semanas disponibles en ${escapeHtml(state.currentVault || '')} (${weeks.length})</div>
      <div class="modal-list">${listHtml}</div>
    `;

    el.modalBody.querySelectorAll('.btn-select-week').forEach((b) => {
      b.addEventListener('click', async () => {
        state.activeYear = parseInt(b.dataset.year, 10);
        state.activeWeekNumber = parseInt(b.dataset.week, 10);
        state.activeDayNumber = null;
        closeModal();
        await loadHub();
        showToast(`Semana ${state.activeWeekNumber} (${state.activeYear}) abierta`, 'info');
      });
    });
  } catch (err) {
    el.modalBody.innerHTML = `<div class="empty-state">Error cargando lista de semanas.</div>`;
  }
}

function openAddExtraDayModal() {
  const now = new Date();
  openModal('🛠️ Añadir Día Extra / Intervención', `
    <p style="color:var(--text-muted);">
      Añade un día adicional (ej. Sábado o Domingo de guardia o intervención) a la bitácora semanal activa.
    </p>
    <div class="modal-form-row">
      <input id="modalExtraDayNum" class="edit-input" style="flex:0 0 110px;" type="number" min="1" max="31" value="${now.getDate()}" placeholder="Día (1-31)">
      <select id="modalExtraDayEmoji" class="edit-select" style="flex:0 0 150px;">
        <option value="🛠️">🛠️ Intervención</option>
        <option value="🏠">🏠 Casa / Remoto</option>
        <option value="🚗">🚗 Oficina</option>
        <option value="🏖️">🏖️ Festivo / Libre</option>
      </select>
      <input id="modalExtraDayNote" class="edit-input" style="flex:1;" type="text" value="Intervención" placeholder="Nota opcional (ej: Guardia)">
    </div>
    <div style="display:flex;justify-content:flex-end;margin-top:6px;">
      <button id="btnConfirmExtraDay" class="btn-edit-save" type="button">Añadir Día ✓</button>
    </div>
  `);

  const btn = document.getElementById('btnConfirmExtraDay');
  if (btn) {
    btn.addEventListener('click', async () => {
      const dayNum = parseInt(document.getElementById('modalExtraDayNum').value, 10);
      const emoji = document.getElementById('modalExtraDayEmoji').value;
      const note = document.getElementById('modalExtraDayNote').value.trim();
      if (!dayNum || dayNum < 1 || dayNum > 31) {
        showToast('Introduce un día válido entre 1 y 31', 'error');
        return;
      }
      btn.disabled = true;
      try {
        const res = await fetch('/api/weeks/extra-day', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            vault: state.currentVault,
            day_number: dayNum,
            emoji: emoji,
            note: note || null,
            year: state.activeYear,
            week: state.activeWeekNumber
          })
        });
        if (res.ok) {
          closeModal();
          state.activeDayNumber = dayNum;
          await loadHub();
          showToast(`Día ${dayNum} añadido a la semana`, 'success');
        }
      } catch (err) {
        showToast('Error añadiendo día extra', 'error');
      } finally {
        btn.disabled = false;
      }
    });
  }
}

function openSetWeightModal() {
  const curWeight = (state.hubData && state.hubData.week && state.hubData.week.weight) ? state.hubData.week.weight : '';
  openModal('⚖️ Registrar Peso Semanal (kg)', `
    <div class="modal-form-row">
      <input id="modalWeightInput" class="edit-input" style="flex:1;" type="number" step="0.1" value="${escapeHtml(String(curWeight))}" placeholder="Ej: 81.4 (dejar vacío para borrar)">
      <button id="btnSaveWeight" class="btn-edit-save" type="button">Guardar ✓</button>
    </div>
  `);

  const input = document.getElementById('modalWeightInput');
  const btn = document.getElementById('btnSaveWeight');
  if (input) input.focus();
  if (btn) {
    btn.addEventListener('click', async () => {
      btn.disabled = true;
      try {
        const res = await fetch('/api/weeks/weight', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            vault: state.currentVault,
            weight: input ? input.value.trim() : null,
            year: state.activeYear,
            week: state.activeWeekNumber
          })
        });
        const data = await res.json();
        if (res.ok && data.success) {
          closeModal();
          await loadHub();
          showToast(data.weight ? `Peso actualizado: ${data.weight} kg` : 'Peso semanal eliminado', 'success');
        } else {
          showToast(data.error || 'Valor inválido', 'error');
        }
      } catch (err) {
        showToast('Error guardando peso', 'error');
      } finally {
        btn.disabled = false;
      }
    });
  }
}

async function runSyncCurrentWeek() {
  try {
    const res = await fetch('/api/sync', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        vault: state.currentVault,
        year: state.activeYear,
        week: state.activeWeekNumber
      })
    });
    const data = await res.json();
    if (data.status === 'ok') {
      await loadHub();
      showToast(`Sincronizada ${data.file || 'semana activa'}`, 'success');
    } else {
      showToast(data.message || 'No se pudo sincronizar', 'error');
    }
  } catch (err) {
    showToast('Error al sincronizar semana actual', 'error');
  }
}

async function runSyncAllWeeks() {
  showToast('Sincronizando todas las bitácoras del vault...', 'info');
  try {
    const res = await fetch('/api/sync/all', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ vault: state.currentVault })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      await loadHub();
      showToast(`Sincronizadas ${data.count} bitácoras semanales`, 'success');
    }
  } catch (err) {
    showToast('Error al sincronizar todas las semanas', 'error');
  }
}

async function runApplyRecurring() {
  try {
    const res = await fetch('/api/recurring/apply', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        vault: state.currentVault,
        year: state.activeYear,
        week: state.activeWeekNumber
      })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      await loadHub();
      showToast(`Inyectadas ${data.injected} tareas recurrentes en la semana`, 'success');
    }
  } catch (err) {
    showToast('Error inyectando tareas recurrentes', 'error');
  }
}

async function runApplyCalendar() {
  try {
    const res = await fetch('/api/calendar/apply', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        vault: state.currentVault,
        year: state.activeYear,
        week: state.activeWeekNumber
      })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      await loadHub();
      showToast(data.changed ? 'Calendario laboral aplicado a la semana' : 'El calendario ya estaba al día', 'success');
    }
  } catch (err) {
    showToast('Error aplicando calendario laboral', 'error');
  }
}

async function openManageRecurringModal() {
  openModal('🔁 Gestionar Tareas Recurrentes y Reuniones', `<div>Cargando recurrencias...</div>`);
  try {
    const res = await fetch(`/api/recurring?vault=${encodeURIComponent(state.currentVault || '')}`);
    const data = await res.json();
    const list = data.recurring_tasks || [];
    const dayLabels = ['L', 'M', 'X', 'J', 'V', 'S', 'D'];

    const itemsHtml = list.map((r) => {
      let schedDesc = 'Semanal (sin día fijo)';
      if (r.recurrence_type === 'weekly_days') {
        const daysStr = (r.days_of_week || []).map((d) => dayLabels[d] || d).join(', ');
        schedDesc = `Días: ${daysStr || 'Ninguno'}`;
      } else if (r.recurrence_type === 'interval_weeks') {
        schedDesc = `Cada ${r.interval_weeks} sem (${dayLabels[r.day_of_week] || 'V'})`;
      }
      return `
        <div class="modal-list-item" style="${r.active ? '' : 'opacity:0.55;'}">
          <div style="flex:1;min-width:0;">
            <div>
              <span>${r.premoji || '🔄'}</span>
              <strong>${escapeHtml(r.title)}</strong>
              ${r.project_id ? `<span class="task-project-tag">${escapeHtml(r.project_id)}</span>` : ''}
            </div>
            <div style="font-size:0.75rem;color:var(--text-muted);">${escapeHtml(schedDesc)} • ${r.active ? '🟢 Activa' : '⏸️ Pausada'}</div>
          </div>
          <div style="display:flex;gap:6px;">
            <button type="button" class="btn-edit-cancel btn-toggle-rec" data-id="${r.id}">${r.active ? '⏸️' : '▶️'}</button>
            <button type="button" class="btn-edit-delete btn-del-rec" data-id="${r.id}">🗑️</button>
          </div>
        </div>
      `;
    }).join('');

    el.modalBody.innerHTML = `
      <div class="modal-section-title">Nueva Tarea / Reunión Recurrente</div>
      <div class="edit-form-box" style="background:var(--bg-card);padding:10px;border-radius:var(--radius-md);border:1px solid var(--border);">
        <input id="recTitleInput" class="edit-input" type="text" placeholder="Título (ej: Reunión: Daily Sync #[PROYECTO])">
        <div class="modal-form-row">
          <select id="recTypeSelect" class="edit-select" style="flex:1;">
            <option value="weekly_days">📅 Días fijos de la semana</option>
            <option value="interval_weeks">⏱️ Cada N semanas</option>
            <option value="week_tasks">⏳ Tarea general de la semana</option>
          </select>
          <input id="recIntervalInput" class="edit-input" style="width:90px;display:none;" type="number" min="1" max="52" value="2" title="Intervalo de semanas">
        </div>
        <div id="recDaysRow" class="weekday-pills">
          ${dayLabels.map((lbl, idx) => `<button type="button" class="weekday-pill ${idx === 0 ? 'active' : ''}" data-day="${idx}">${lbl}</button>`).join('')}
        </div>
        <div style="display:flex;justify-content:flex-end;">
          <button id="btnCreateRec" class="btn-edit-save" type="button">➕ Crear e Inyectar</button>
        </div>
      </div>
      <div class="modal-section-title">Definiciones registradas (${list.length})</div>
      <div class="modal-list">${itemsHtml || '<div class="empty-state">No hay tareas recurrentes definidas.</div>'}</div>
    `;

    // Eventos de selección de días
    const recTypeSelect = document.getElementById('recTypeSelect');
    const recIntervalInput = document.getElementById('recIntervalInput');
    const recDaysRow = document.getElementById('recDaysRow');

    recTypeSelect.addEventListener('change', () => {
      const val = recTypeSelect.value;
      recIntervalInput.style.display = val === 'interval_weeks' ? 'block' : 'none';
      recDaysRow.style.display = val === 'week_tasks' ? 'none' : 'flex';
    });

    el.modalBody.querySelectorAll('.weekday-pill').forEach((pill) => {
      pill.addEventListener('click', () => {
        if (recTypeSelect.value === 'interval_weeks') {
          el.modalBody.querySelectorAll('.weekday-pill').forEach((p) => p.classList.remove('active'));
          pill.classList.add('active');
        } else {
          pill.classList.toggle('active');
        }
      });
    });

    document.getElementById('btnCreateRec').addEventListener('click', async () => {
      const title = document.getElementById('recTitleInput').value.trim();
      if (!title) return;
      const rtype = recTypeSelect.value;
      const selectedDays = Array.from(el.modalBody.querySelectorAll('.weekday-pill.active')).map((p) => parseInt(p.dataset.day, 10));
      const resCreate = await fetch('/api/recurring', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          vault: state.currentVault,
          title: title,
          recurrence_type: rtype,
          days_of_week: selectedDays,
          interval_weeks: parseInt(recIntervalInput.value, 10) || 1,
          day_of_week: selectedDays[0] ?? 4,
          year: state.activeYear,
          week: state.activeWeekNumber
        })
      });
      if (resCreate.ok) {
        await loadHub();
        openManageRecurringModal();
        showToast('Tarea recurrente creada e inyectada', 'success');
      }
    });

    el.modalBody.querySelectorAll('.btn-toggle-rec').forEach((btn) => {
      btn.addEventListener('click', async () => {
        await fetch(`/api/recurring/${encodeURIComponent(btn.dataset.id)}/toggle`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ vault: state.currentVault })
        });
        openManageRecurringModal();
      });
    });

    el.modalBody.querySelectorAll('.btn-del-rec').forEach((btn) => {
      btn.addEventListener('click', async () => {
        if (!confirm('¿Eliminar esta definición recurrente?')) return;
        await fetch(`/api/recurring/${encodeURIComponent(btn.dataset.id)}?vault=${encodeURIComponent(state.currentVault || '')}`, {
          method: 'DELETE'
        });
        openManageRecurringModal();
      });
    });
  } catch (err) {
    el.modalBody.innerHTML = `<div class="empty-state">Error cargando tareas recurrentes.</div>`;
  }
}

async function openProjectsOverviewModal() {
  openModal('📊 Estado Global de Proyectos y Métricas', `<div>Calculando métricas...</div>`);
  try {
    const res = await fetch(`/api/projects?vault=${encodeURIComponent(state.currentVault || '')}`);
    const data = await res.json();
    const projects = data.projects || [];

    const projRows = projects.map((p) => {
      const s = p.stats || {};
      return `
        <div class="modal-list-item" style="flex-direction:column;align-items:stretch;">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
              <strong>📁 ${escapeHtml(p.id)}</strong>
              <span style="color:var(--text-muted);font-size:0.8rem;margin-left:6px;">${escapeHtml(p.name || '')}</span>
            </div>
            <span style="font-family:var(--font-mono);font-size:0.8rem;font-weight:700;color:var(--success);">${s.completion_rate || 0}%</span>
          </div>
          <div class="progress-bar-track">
            <div class="progress-bar-fill" style="width:${Math.min(100, s.completion_rate || 0)}%;"></div>
          </div>
          <div style="display:flex;gap:12px;font-size:0.75rem;color:var(--text-muted);margin-top:4px;">
            <span>✅ Hechas: ${s.done_tasks || 0}</span>
            <span>⏳ Pendientes: ${s.pending_tasks || 0}</span>
            <span>🗂️ En Backlog: ${s.backlog_tasks || 0}</span>
            <span>💡 Ideas: ${s.total_ideas || 0}</span>
          </div>
        </div>
      `;
    }).join('');

    el.modalBody.innerHTML = `
      <div class="modal-metric-grid">
        <div class="modal-metric-card">
          <div class="modal-metric-val">${data.global_completion_rate || 0}%</div>
          <div class="modal-metric-lbl">Completado Global</div>
        </div>
        <div class="modal-metric-card">
          <div class="modal-metric-val">${data.total_done || 0}/${data.total_tasks || 0}</div>
          <div class="modal-metric-lbl">Tareas Hechas</div>
        </div>
        <div class="modal-metric-card">
          <div class="modal-metric-val">${data.total_backlog || 0}</div>
          <div class="modal-metric-lbl">En Backlog</div>
        </div>
        <div class="modal-metric-card">
          <div class="modal-metric-val">${data.total_projects || 0}</div>
          <div class="modal-metric-lbl">Proyectos</div>
        </div>
      </div>
      <div class="modal-section-title">Registrar Nuevo Proyecto</div>
      <div class="modal-form-row">
        <input id="newProjId" class="edit-input" style="flex:0 0 150px;" type="text" placeholder="Código (ej: GRAFANA)">
        <input id="newProjName" class="edit-input" style="flex:1;" type="text" placeholder="Nombre descriptivo">
        <button id="btnCreateProj" class="btn-edit-save" type="button">➕ Crear</button>
      </div>
      <div class="modal-section-title">Desglose por Proyecto</div>
      <div class="modal-list">${projRows || '<div class="empty-state">No hay proyectos registrados.</div>'}</div>
    `;

    document.getElementById('btnCreateProj').addEventListener('click', async () => {
      const pid = document.getElementById('newProjId').value.trim();
      const pname = document.getElementById('newProjName').value.trim();
      if (!pid) return;
      const r = await fetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ vault: state.currentVault, id: pid, name: pname || pid })
      });
      if (r.ok) {
        showToast(`Proyecto ${pid.toUpperCase()} registrado`, 'success');
        openProjectsOverviewModal();
        loadHub();
      }
    });
  } catch (err) {
    el.modalBody.innerHTML = `<div class="empty-state">Error cargando métricas de proyectos.</div>`;
  }
}

async function openBacklogManagerModal() {
  openModal('🗂️ Gestionar Backlog (Tareas sin fecha)', `<div>Cargando backlog...</div>`);
  try {
    const res = await fetch(`/api/backlog?vault=${encodeURIComponent(state.currentVault || '')}`);
    const data = await res.json();
    const tasks = data.backlog_tasks || [];
    const activeDayNum = state.activeDayNumber || (state.hubData && state.hubData.active_day ? state.hubData.active_day.day_number : null);

    const listHtml = tasks.map((t) => `
      <div class="modal-list-item">
        <div style="flex:1;min-width:0;">
          <span>${t.premoji || '📋'}</span>
          <strong>${escapeHtml(t.title)}</strong>
          ${t.project_id ? `<span class="task-project-tag">${escapeHtml(t.project_id)}</span>` : ''}
        </div>
        <div style="display:flex;gap:6px;">
          <button type="button" class="btn-edit-save btn-sched-backlog-day" data-id="${t.id}" title="Agendar al Día ${activeDayNum || 'Activo'}">➔ Día ${activeDayNum || 'Hoy'}</button>
          <button type="button" class="btn-edit-cancel btn-sched-backlog-week" data-id="${t.id}" title="Mover a Tareas de la Semana">⏳ Sem</button>
        </div>
      </div>
    `).join('');

    el.modalBody.innerHTML = `
      <div class="modal-section-title">Añadir Tarea Directamente al Backlog</div>
      <div class="modal-form-row">
        <input id="backlogNewTitle" class="edit-input" style="flex:1;" type="text" placeholder="Nueva tarea de backlog... (ej: Migrar servidor #[INFRA])">
        <button id="btnAddBacklogTask" class="btn-edit-save" type="button">➕ Guardar en Backlog</button>
      </div>
      <div class="modal-section-title">Tareas Pendientes sin Agendar (${tasks.length})</div>
      <div class="modal-list">${listHtml || '<div class="empty-state">¡Backlog limpio! No hay tareas pendientes sin fecha.</div>'}</div>
    `;

    document.getElementById('btnAddBacklogTask').addEventListener('click', async () => {
      const title = document.getElementById('backlogNewTitle').value.trim();
      if (!title) return;
      const r = await fetch('/api/backlog', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ vault: state.currentVault, title })
      });
      if (r.ok) {
        showToast('Tarea añadida al Backlog', 'success');
        openBacklogManagerModal();
      }
    });

    el.modalBody.querySelectorAll('.btn-sched-backlog-day').forEach((btn) => {
      btn.addEventListener('click', async () => {
        await fetch('/api/backlog/schedule', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            vault: state.currentVault,
            task_id: btn.dataset.id,
            target: 'day',
            day_number: activeDayNum,
            year: state.activeYear,
            week: state.activeWeekNumber
          })
        });
        await loadHub();
        openBacklogManagerModal();
        showToast('Tarea agendada al día activo', 'success');
      });
    });

    el.modalBody.querySelectorAll('.btn-sched-backlog-week').forEach((btn) => {
      btn.addEventListener('click', async () => {
        await fetch('/api/backlog/schedule', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            vault: state.currentVault,
            task_id: btn.dataset.id,
            target: 'week',
            year: state.activeYear,
            week: state.activeWeekNumber
          })
        });
        await loadHub();
        openBacklogManagerModal();
        showToast('Tarea añadida a Tareas de la Semana', 'success');
      });
    });
  } catch (err) {
    el.modalBody.innerHTML = `<div class="empty-state">Error cargando el Backlog.</div>`;
  }
}

async function openIdeasManagerModal() {
  openModal('💡 Gestionar Ideas ([🧩GENERAL]🧠Ideas.md)', `<div>Cargando ideas...</div>`);
  try {
    const res = await fetch(`/api/ideas?vault=${encodeURIComponent(state.currentVault || '')}`);
    const data = await res.json();
    const ideas = data.ideas || [];

    const statusEmoji = { evaluating: '🟡', accepted: '🟢', discarded: '🔴' };
    const rowsHtml = ideas.map((idea) => `
      <div class="modal-list-item">
        <div style="flex:1;min-width:0;">
          <span>${statusEmoji[idea.status] || '💡'}</span>
          <strong>${escapeHtml(idea.title)}</strong>
          ${idea.project_id ? `<span class="task-project-tag">${escapeHtml(idea.project_id)}</span>` : ''}
        </div>
        <select class="edit-select idea-status-select" data-id="${idea.id}" style="width:135px;">
          <option value="evaluating" ${idea.status === 'evaluating' ? 'selected' : ''}>🟡 Evaluando</option>
          <option value="accepted" ${idea.status === 'accepted' ? 'selected' : ''}>🟢 Aceptada</option>
          <option value="discarded" ${idea.status === 'discarded' ? 'selected' : ''}>🔴 Descartada</option>
        </select>
      </div>
    `).join('');

    el.modalBody.innerHTML = `
      <div class="modal-section-title">Capturar Nueva Idea</div>
      <div class="modal-form-row">
        <input id="ideaNewTitle" class="edit-input" style="flex:1;" type="text" placeholder="Título de la idea... (ej: Automatizar alertas #[GRAFANA])">
        <button id="btnAddIdea" class="btn-edit-save" type="button">💡 Guardar Idea</button>
      </div>
      <div class="modal-section-title">Ideas Registradas (${ideas.length})</div>
      <div class="modal-list">${rowsHtml || '<div class="empty-state">No hay ideas registradas todavía.</div>'}</div>
    `;

    document.getElementById('btnAddIdea').addEventListener('click', async () => {
      const title = document.getElementById('ideaNewTitle').value.trim();
      if (!title) return;
      const r = await fetch('/api/ideas', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ vault: state.currentVault, title })
      });
      if (r.ok) {
        showToast('Idea guardada y sincronizada en Markdown', 'success');
        openIdeasManagerModal();
      }
    });

    el.modalBody.querySelectorAll('.idea-status-select').forEach((sel) => {
      sel.addEventListener('change', async () => {
        await fetch(`/api/ideas/${encodeURIComponent(sel.dataset.id)}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ vault: state.currentVault, status: sel.value })
        });
        showToast('Estado de idea actualizado', 'info');
        openIdeasManagerModal();
      });
    });
  } catch (err) {
    el.modalBody.innerHTML = `<div class="empty-state">Error cargando ideas.</div>`;
  }
}

function openScheduleWeekToTodayModal() {
  const weekTasks = (state.hubData && state.hubData.week_tasks) ? state.hubData.week_tasks.filter((t) => !t.is_done) : [];
  const activeDayNum = state.activeDayNumber || (state.hubData && state.hubData.active_day ? state.hubData.active_day.day_number : null);

  const rowsHtml = weekTasks.map((t) => `
    <div class="modal-list-item">
      <div>
        <span>${t.premoji || '⏳'}</span>
        <strong>${escapeHtml(t.title)}</strong>
        ${t.project_id ? `<span class="task-project-tag">${escapeHtml(t.project_id)}</span>` : ''}
      </div>
      <button type="button" class="btn-edit-save btn-move-wk-to-day" data-id="${t.id}">➔ Pasar a Día ${activeDayNum || 'Hoy'}</button>
    </div>
  `).join('');

  openModal(`➡️ Agendar Tarea Semanal a Día ${activeDayNum || 'Activo'}`, `
    <div class="modal-list">${rowsHtml || '<div class="empty-state">No hay tareas semanales pendientes para mover.</div>'}</div>
  `);

  el.modalBody.querySelectorAll('.btn-move-wk-to-day').forEach((btn) => {
    btn.addEventListener('click', async () => {
      await fetch('/api/backlog/schedule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          vault: state.currentVault,
          task_id: btn.dataset.id,
          target: 'day',
          day_number: activeDayNum,
          year: state.activeYear,
          week: state.activeWeekNumber
        })
      });
      closeModal();
      await loadHub();
      showToast(`Tarea movida al Día ${activeDayNum}`, 'success');
    });
  });
}

function openConsolidateMonthModal() {
  const now = new Date();
  const curYear = (state.hubData && state.hubData.week) ? state.hubData.week.year : now.getFullYear();
  const curMonth = (state.hubData && state.hubData.week) ? state.hubData.week.month : (now.getMonth() + 1);

  openModal('📅 Consolidar Mes Completo ([YYYY][MM].md)', `
    <p style="color:var(--text-muted);">
      Une todas las bitácoras semanales del mes en un único archivo consolidado mensual <code>[YYYY][MM].md</code>.
    </p>
    <div class="modal-form-row">
      <input id="consMonthYear" class="edit-input" style="flex:1;" type="number" value="${curYear}" placeholder="Año (YYYY)">
      <input id="consMonthNum" class="edit-input" style="flex:1;" type="number" min="1" max="12" value="${curMonth}" placeholder="Mes (1-12)">
    </div>
    <label style="display:flex;align-items:center;gap:8px;font-size:0.82rem;color:var(--text-muted);cursor:pointer;">
      <input id="consMonthDelete" type="checkbox">
      Borrar archivos semanales origen tras consolidar
    </label>
    <div style="display:flex;justify-content:flex-end;">
      <button id="btnRunConsMonth" class="btn-edit-save" type="button">📦 Consolidar Mes</button>
    </div>
  `);

  const btn = document.getElementById('btnRunConsMonth');
  if (btn) {
    btn.addEventListener('click', async () => {
      btn.disabled = true;
      try {
        const res = await fetch('/api/consolidate/month', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            vault: state.currentVault,
            year: parseInt(document.getElementById('consMonthYear').value, 10),
            month: parseInt(document.getElementById('consMonthNum').value, 10),
            delete_source: document.getElementById('consMonthDelete').checked
          })
        });
        const data = await res.json();
        if (res.ok && data.success) {
          closeModal();
          showToast(`Creado consolidado mensual: ${data.file}`, 'success');
        } else {
          showToast(data.message || data.error || 'No se pudo consolidar el mes', 'error');
        }
      } catch (err) {
        showToast('Error al consolidar mes', 'error');
      } finally {
        btn.disabled = false;
      }
    });
  }
}

function openConsolidateYearModal() {
  const now = new Date();
  const curYear = (state.hubData && state.hubData.week) ? state.hubData.week.year : now.getFullYear();

  openModal('🗓️ Consolidar Año Completo ([YYYY].md)', `
    <p style="color:var(--text-muted);">
      Une todos los archivos consolidados mensuales <code>[YYYY][MM].md</code> del año en un único archivo anual <code>[YYYY].md</code>.
    </p>
    <div class="modal-form-row">
      <input id="consYearInput" class="edit-input" style="flex:1;" type="number" value="${curYear}" placeholder="Año (YYYY)">
      <button id="btnRunConsYear" class="btn-edit-save" type="button">📦 Consolidar Año</button>
    </div>
  `);

  const btn = document.getElementById('btnRunConsYear');
  if (btn) {
    btn.addEventListener('click', async () => {
      btn.disabled = true;
      try {
        const res = await fetch('/api/consolidate/year', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            vault: state.currentVault,
            year: parseInt(document.getElementById('consYearInput').value, 10),
            delete_source: false
          })
        });
        const data = await res.json();
        if (res.ok && data.success) {
          closeModal();
          showToast(`Creado consolidado anual: ${data.file}`, 'success');
        } else {
          showToast(data.message || data.error || 'Primero consolida algún mes del año', 'error');
        }
      } catch (err) {
        showToast('Error al consolidar año', 'error');
      } finally {
        btn.disabled = false;
      }
    });
  }
}

async function openWorkCalendarModal() {
  openModal('🏖️ Calendario Laboral (Festivos y Vacaciones)', `<div>Cargando calendario...</div>`);
  try {
    const res = await fetch(`/api/calendar?vault=${encodeURIComponent(state.currentVault || '')}`);
    const data = await res.json();
    const holidays = data.holidays || [];
    const vacations = data.vacations || [];

    const holHtml = holidays.map((h, idx) => `
      <div class="modal-list-item">
        <div><strong>🎉 ${escapeHtml(h.date)}</strong> — ${escapeHtml(h.name || 'Festivo')}</div>
        <button type="button" class="btn-edit-delete btn-del-hol" data-idx="${idx}">🗑️</button>
      </div>
    `).join('');

    const vacHtml = vacations.map((v, idx) => `
      <div class="modal-list-item">
        <div><strong>🏖️ ${escapeHtml(v.start)} ➔ ${escapeHtml(v.end)}</strong> — ${escapeHtml(v.name || 'Vacaciones')}</div>
        <button type="button" class="btn-edit-delete btn-del-vac" data-idx="${idx}">🗑️</button>
      </div>
    `).join('');

    el.modalBody.innerHTML = `
      <div class="modal-section-title">Añadir Día Festivo</div>
      <div class="modal-form-row">
        <input id="calHolDate" class="edit-input" style="flex:0 0 155px;" type="date">
        <input id="calHolName" class="edit-input" style="flex:1;" type="text" placeholder="Nombre del festivo">
        <button id="btnAddHol" class="btn-edit-save" type="button">➕ Festivo</button>
      </div>
      <div class="modal-list" style="max-height:140px;">${holHtml || '<div class="empty-state" style="padding:10px;">Sin festivos registrados.</div>'}</div>

      <div class="modal-section-title" style="margin-top:6px;">Añadir Periodo de Vacaciones</div>
      <div class="modal-form-row">
        <input id="calVacStart" class="edit-input" style="flex:1;" type="date" title="Inicio">
        <input id="calVacEnd" class="edit-input" style="flex:1;" type="date" title="Fin">
        <input id="calVacName" class="edit-input" style="flex:1;" type="text" placeholder="Motivo / Nombre">
        <button id="btnAddVac" class="btn-edit-save" type="button">➕ Vacaciones</button>
      </div>
      <div class="modal-list" style="max-height:140px;">${vacHtml || '<div class="empty-state" style="padding:10px;">Sin vacaciones registradas.</div>'}</div>

      <div style="display:flex;justify-content:flex-end;margin-top:6px;">
        <button id="btnModalApplyCal" class="btn-edit-cancel" type="button">📆 Reaplicar Calendario a Semana Actual</button>
      </div>
    `;

    document.getElementById('btnAddHol').addEventListener('click', async () => {
      const d = document.getElementById('calHolDate').value;
      const n = document.getElementById('calHolName').value.trim();
      if (!d) return;
      const r = await fetch('/api/calendar/holidays', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ vault: state.currentVault, date: d, name: n || 'Festivo' })
      });
      if (r.ok) {
        openWorkCalendarModal();
        showToast('Festivo añadido al calendario', 'success');
      }
    });

    document.getElementById('btnAddVac').addEventListener('click', async () => {
      const s = document.getElementById('calVacStart').value;
      const e = document.getElementById('calVacEnd').value;
      const n = document.getElementById('calVacName').value.trim();
      if (!s || !e) return;
      const r = await fetch('/api/calendar/vacations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ vault: state.currentVault, start: s, end: e, name: n || 'Vacaciones' })
      });
      if (r.ok) {
        openWorkCalendarModal();
        showToast('Vacaciones registradas', 'success');
      }
    });

    el.modalBody.querySelectorAll('.btn-del-hol').forEach((b) => {
      b.addEventListener('click', async () => {
        await fetch(`/api/calendar/holidays/${b.dataset.idx}?vault=${encodeURIComponent(state.currentVault || '')}`, { method: 'DELETE' });
        openWorkCalendarModal();
      });
    });

    el.modalBody.querySelectorAll('.btn-del-vac').forEach((b) => {
      b.addEventListener('click', async () => {
        await fetch(`/api/calendar/vacations/${b.dataset.idx}?vault=${encodeURIComponent(state.currentVault || '')}`, { method: 'DELETE' });
        openWorkCalendarModal();
      });
    });

    document.getElementById('btnModalApplyCal').addEventListener('click', async () => {
      await runApplyCalendar();
      closeModal();
    });
  } catch (err) {
    el.modalBody.innerHTML = `<div class="empty-state">Error cargando el calendario laboral.</div>`;
  }
}

function toggleAllCollapsibleSections() {
  const sections = Array.from(document.querySelectorAll('.collapsible-section'));
  const anyExpanded = sections.some((s) => !s.classList.contains('collapsed'));
  sections.forEach((sec) => {
    const sectionId = sec.dataset.section;
    const btn = sec.querySelector('.section-header-btn');
    if (anyExpanded) {
      sec.classList.add('collapsed');
      if (btn) btn.setAttribute('aria-expanded', 'false');
      if (sectionId) localStorage.setItem(`brackets_section_collapsed_${sectionId}`, 'true');
    } else {
      sec.classList.remove('collapsed');
      if (btn) btn.setAttribute('aria-expanded', 'true');
      if (sectionId) localStorage.setItem(`brackets_section_collapsed_${sectionId}`, 'false');
    }
  });
}

// ---------------------------------------------------------------------------
// Temporizador Pomodoro Flotante con Modo Focus (Difuminado de Fondo)
// ---------------------------------------------------------------------------
const pomoState = {
  totalSeconds: 25 * 60,
  remainingSeconds: 25 * 60,
  running: false,
  intervalId: null,
  blurActive: false
};

function updatePomodoroTaskOptions(data) {
  if (!el.pomoTaskSelect || !data) return;
  const prevVal = el.pomoTaskSelect.value;
  const tasks = [...(data.today_tasks || []), ...(data.week_tasks || [])].filter((t) => !t.is_done);
  el.pomoTaskSelect.innerHTML = `<option value="">🎯 Sin tarea específica seleccionada</option>`;
  tasks.forEach((t) => {
    const opt = document.createElement('option');
    opt.value = t.id;
    opt.textContent = `${t.premoji || '📋'} ${t.title}`;
    el.pomoTaskSelect.appendChild(opt);
  });
  if (prevVal) el.pomoTaskSelect.value = prevVal;
}

function formatPomoTime(secs) {
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

function togglePomodoroWidget(forceShow = null) {
  if (!el.pomodoroWidget) return;
  const isHidden = el.pomodoroWidget.style.display === 'none';
  const nextShow = forceShow !== null ? forceShow : isHidden;
  el.pomodoroWidget.style.display = nextShow ? 'block' : 'none';
  if (!nextShow && el.pomodoroBackdrop) {
    el.pomodoroBackdrop.style.display = 'none';
    pomoState.blurActive = false;
    if (el.btnPomoBlurToggle) el.btnPomoBlurToggle.classList.remove('active');
  }
}

function setupPomodoroWidget() {
  if (!el.pomodoroWidget) return;

  const renderTime = () => {
    if (el.pomoTimeDisplay) {
      el.pomoTimeDisplay.textContent = formatPomoTime(pomoState.remainingSeconds);
    }
  };

  const stopTimer = () => {
    if (pomoState.intervalId) {
      clearInterval(pomoState.intervalId);
      pomoState.intervalId = null;
    }
    pomoState.running = false;
    if (el.btnPomoStartPause) el.btnPomoStartPause.textContent = '▶ Iniciar';
  };

  if (el.btnPomoStartPause) {
    el.btnPomoStartPause.addEventListener('click', () => {
      if (pomoState.running) {
        stopTimer();
      } else {
        pomoState.running = true;
        el.btnPomoStartPause.textContent = '⏸ Pausar';
        pomoState.intervalId = setInterval(() => {
          if (pomoState.remainingSeconds > 0) {
            pomoState.remainingSeconds -= 1;
            renderTime();
          } else {
            stopTimer();
            playAllDoneSound();
            triggerCelebrationEffect();
            showToast('🍅 ¡Sesión Pomodoro completada!', 'success');
          }
        }, 1000);
      }
    });
  }

  if (el.btnPomoReset) {
    el.btnPomoReset.addEventListener('click', () => {
      stopTimer();
      pomoState.remainingSeconds = pomoState.totalSeconds;
      renderTime();
    });
  }

  el.pomodoroWidget.querySelectorAll('.btn-pomo-mode').forEach((btn) => {
    btn.addEventListener('click', () => {
      el.pomodoroWidget.querySelectorAll('.btn-pomo-mode').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      const mins = parseInt(btn.dataset.minutes, 10) || 25;
      stopTimer();
      pomoState.totalSeconds = mins * 60;
      pomoState.remainingSeconds = pomoState.totalSeconds;
      renderTime();
    });
  });

  if (el.btnPomoBlurToggle) {
    el.btnPomoBlurToggle.addEventListener('click', () => {
      pomoState.blurActive = !pomoState.blurActive;
      el.btnPomoBlurToggle.classList.toggle('active', pomoState.blurActive);
      if (el.pomodoroBackdrop) {
        el.pomodoroBackdrop.style.display = pomoState.blurActive ? 'block' : 'none';
      }
    });
  }

  if (el.btnPomoMinimize) {
    el.btnPomoMinimize.addEventListener('click', () => {
      el.pomodoroWidget.classList.toggle('minimized');
    });
  }

  if (el.btnPomoClose) {
    el.btnPomoClose.addEventListener('click', () => {
      stopTimer();
      togglePomodoroWidget(false);
    });
  }
}



// ---------------------------------------------------------------------------
// Integración UI Multi-Vault Híbrido (Local Disk + GitHub REST API v3)
// ---------------------------------------------------------------------------
function closeAllTopMenuDropdowns() {
  if (typeof closeHamburgerMenu === 'function') {
    closeHamburgerMenu();
  }
}

function updateStorageModeBadge() {
  const btn = document.getElementById('btnGitHubConfig');
  if (!btn) return;
  const gh = window.BracketsGitHub;
  const isGh = gh && gh.ConfigStore.isGitHubVault(state.currentVault);
  const hasToken = gh && gh.ConfigStore.hasToken();

  if (isGh) {
    btn.classList.add('is-github');
    btn.textContent = hasToken ? '☁️ GitHub API' : '🔑 Configurar PAT';
    btn.title = 'Modo activo: GitHub REST API v3 (Clic para gestionar Token PAT y Repositorios)';
  } else {
    btn.classList.remove('is-github');
    btn.textContent = '💻 Local · ☁️ GitHub';
    btn.title = 'Modo activo: Servidor Local PC (Clic para configurar GitHub API y Vaults Remotos)';
  }
}

// Sobrescribir loadVaults para agrupar Vaults Locales y Vaults Remotos de GitHub
async function loadVaults() {
  try {
    const res = await fetch('/api/vaults');
    const data = await res.json();
    if (!el.vaultSelect) return;
    el.vaultSelect.innerHTML = '';

    const vaults = data.vaults || [];
    const localVaults = vaults.filter((v) => v.storage_mode !== 'github');
    const githubVaults = vaults.filter((v) => v.storage_mode === 'github');

    function formatVaultOptionLabel(vault, defaultIcon) {
      let raw = (vault.label || vault.name || '').replace(/\s*\((GitHub|Local)\)\s*/gi, '').trim();
      if (!raw.startsWith('☁️') && !raw.startsWith('💻') && !raw.startsWith('🌱') && !raw.startsWith('💼')) {
        raw = `${defaultIcon} ${raw}`;
      }
      return raw;
    }

    if (localVaults.length > 0) {
      const localGroup = document.createElement('optgroup');
      localGroup.label = '💻 Vaults Locales (PC)';
      localVaults.forEach((v) => {
        const opt = document.createElement('option');
        opt.value = v.name;
        opt.textContent = formatVaultOptionLabel(v, v.vault_type === 'personal' ? '🌱' : '💼');
        localGroup.appendChild(opt);
      });
      el.vaultSelect.appendChild(localGroup);
    }

    if (githubVaults.length > 0) {
      const ghGroup = document.createElement('optgroup');
      ghGroup.label = '☁️ Vaults en GitHub (API v3)';
      githubVaults.forEach((v) => {
        const opt = document.createElement('option');
        opt.value = v.name;
        opt.textContent = formatVaultOptionLabel(v, '☁️');
        ghGroup.appendChild(opt);
      });
      el.vaultSelect.appendChild(ghGroup);
    }

    if (vaults.length > 0) {
      const preferred =
        data.default_vault && vaults.some((v) => v.name === data.default_vault)
          ? data.default_vault
          : vaults[0].name;
      state.currentVault = preferred;
      el.vaultSelect.value = preferred;
      updateStorageModeBadge();
    }
  } catch (err) {
    console.error('Error cargando vaults:', err);
  }
}

// Extender renderHamburgerMenu para garantizar que siempre exista acceso a Configuración GitHub
const _baseRenderHamburgerMenu = renderHamburgerMenu;
renderHamburgerMenu = function (groups) {
  const enrichedGroups = Array.isArray(groups) ? JSON.parse(JSON.stringify(groups)) : [];
  const hasGhItem = enrichedGroups.some((g) =>
    (g.items || []).some((it) => it.command === 'github_settings')
  );
  if (!hasGhItem) {
    let toolsGroup = enrichedGroups.find((g) => g.id === 'tools' || (g.label && g.label.includes('Herramientas')));
    if (!toolsGroup) {
      toolsGroup = { id: 'tools', label: '🛠️ Herramientas y Nube', items: [] };
      enrichedGroups.push(toolsGroup);
    }
    toolsGroup.items = toolsGroup.items || [];
    toolsGroup.items.push({
      id: 'github_settings',
      label: '☁️ Configurar GitHub API / Vaults Remotos',
      command: 'github_settings'
    });
  }
  _baseRenderHamburgerMenu(enrichedGroups);
};

const _baseExecuteMenuCommand = executeMenuCommand;
executeMenuCommand = async function (command) {
  if (command === 'github_settings') {
    return openGitHubSettingsModal();
  }
  if (command === 'pomodoro_focus') {
    return togglePomodoroWidget(true);
  }
  return _baseExecuteMenuCommand(command);
};

function openGitHubSettingsModal() {
  const gh = window.BracketsGitHub;
  if (!gh) {
    showToast('El módulo GitHub Adapter no está cargado.', 'error');
    return;
  }

  const renderModalContent = (editingVault = null) => {
    const cfg = gh.ConfigStore.getConfig();
    const hasToken = Boolean(cfg.github_token);
    const vaults = cfg.remote_vaults || [];

    const repoCardsHtml = vaults
      .map((v) => {
        const isCurrent = state.currentVault === v.id;
        return `
          <div class="gh-repo-card ${isCurrent ? 'active-vault' : ''}" data-vault-id="${escapeHtml(v.id)}">
            <div class="gh-repo-header">
              <div>
                <div class="gh-repo-title">${escapeHtml(v.name)} ${isCurrent ? '<span class="gh-status-pill ok">Activo</span>' : ''}</div>
                <div class="gh-repo-meta">${escapeHtml(v.owner)}/${escapeHtml(v.repo)} • rama: <strong>${escapeHtml(v.branch || 'main')}</strong>${v.base_path ? ` • ruta: /${escapeHtml(v.base_path)}` : ''} • ${v.days_per_week || 7}d</div>
              </div>
              <div style="display:flex; gap:6px; flex-wrap:wrap;">
                <button type="button" class="btn-edit-save btn-gh-activate" data-id="${escapeHtml(v.id)}" style="padding:4px 8px; font-size:0.75rem;">🚀 Usar Vault</button>
                <button type="button" class="btn-week-action btn-gh-verify" data-id="${escapeHtml(v.id)}" style="padding:4px 8px; font-size:0.75rem;">🧪 Probar</button>
                <button type="button" class="btn-week-action btn-gh-edit" data-id="${escapeHtml(v.id)}" style="padding:4px 8px; font-size:0.75rem;">✏️</button>
                <button type="button" class="btn-week-action btn-gh-delete" data-id="${escapeHtml(v.id)}" style="padding:4px 8px; font-size:0.75rem; color:#f87171;">🗑️</button>
              </div>
            </div>
            <div id="ghVerifyStatus-${escapeHtml(v.id)}" style="font-size:0.76rem; color:var(--text-muted); display:none;"></div>
          </div>
        `;
      })
      .join('');

    const formTitle = editingVault ? `✏️ Editando: ${editingVault.name}` : '➕ Añadir / Actualizar Repositorio de Notas';
    const vName = editingVault ? editingVault.name : '';
    const vOwner = editingVault ? editingVault.owner : 'Brackets-Core';
    const vRepo = editingVault ? editingVault.repo : '';
    const vBranch = editingVault ? editingVault.branch : 'main';
    const vPath = editingVault ? editingVault.base_path : '';
    const vType = editingVault ? editingVault.vault_type : 'personal';

    openModal(
      '☁️ Conexión GitHub REST API v3 & Multi-Vault',
      `
      <div class="modal-section-title">1. Personal Access Token (PAT) de GitHub</div>
      <p style="font-size:0.8rem; color:var(--text-muted); margin-top:-4px;">
        El token se almacena exclusivamente en el <code>localStorage</code> de tu navegador/móvil y se utiliza para leer y escribir tus bitácoras <code>.md</code> directamente contra <code>api.github.com</code> (requiere permiso <strong>Contents: Read & Write</strong>).
      </p>
      <div class="modal-form-row">
        <input id="inputGhToken" class="edit-input" type="password" style="flex:1;" placeholder="github_pat_... o ghp_..." value="${escapeHtml(cfg.github_token)}" autocomplete="off">
        <button id="btnToggleGhTokenVis" type="button" class="btn-week-action" title="Mostrar/Ocultar Token">👁️</button>
        <button id="btnSaveGhToken" type="button" class="btn-edit-save">💾 Guardar Token</button>
      </div>
      <div style="font-size:0.76rem;">
        Estado del Token: ${hasToken ? '<span class="gh-status-pill ok">✓ Token configurado en este dispositivo</span>' : '<span class="gh-status-pill warn">⚠ Sin token configurado (solo modo local disponible)</span>'}
      </div>

      <hr style="border:none; border-top:1px solid var(--border); margin:6px 0;">

      <div class="modal-section-title">2. Repositorios Privados de Notas (Multi-Vault)</div>
      <div class="modal-list" style="max-height:220px;">
        ${repoCardsHtml || '<div class="empty-state">No hay repositorios remotos configurados.</div>'}
      </div>

      <hr style="border:none; border-top:1px solid var(--border); margin:6px 0;">

      <div class="modal-section-title">${escapeHtml(formTitle)}</div>
      <div class="modal-form-row">
        <input id="inputGhVaultName" class="edit-input" style="flex:1; min-width:140px;" type="text" placeholder="Nombre en UI (ej: ☁️ Personal)" value="${escapeHtml(vName)}">
        <select id="inputGhVaultType" class="edit-input" style="width:175px;">
          <option value="personal" ${vType === 'personal' ? 'selected' : ''}>🌱 Personal (7 días L-D)</option>
          <option value="work" ${vType === 'work' ? 'selected' : ''}>💼 Trabajo (5 días L-V)</option>
        </select>
      </div>
      <div class="modal-form-row">
        <input id="inputGhOwner" class="edit-input" style="flex:1; min-width:120px;" type="text" placeholder="Owner / Org (ej: Brackets-Core)" value="${escapeHtml(vOwner)}">
        <input id="inputGhRepo" class="edit-input" style="flex:1; min-width:130px;" type="text" placeholder="Repositorio (ej: MyPersonalNotes)" value="${escapeHtml(vRepo)}">
      </div>
      <div class="modal-form-row">
        <input id="inputGhBranch" class="edit-input" style="width:120px;" type="text" placeholder="Rama (main)" value="${escapeHtml(vBranch)}">
        <input id="inputGhBasePath" class="edit-input" style="flex:1;" type="text" placeholder="Ruta base opcional (vacío = raíz del repo)" value="${escapeHtml(vPath)}">
        <button id="btnSaveGhVault" type="button" class="btn-edit-save">Guardar Repo</button>
      </div>
    `
    );

    const inputToken = document.getElementById('inputGhToken');
    const btnVis = document.getElementById('btnToggleGhTokenVis');
    const btnSaveToken = document.getElementById('btnSaveGhToken');

    if (btnVis && inputToken) {
      btnVis.addEventListener('click', () => {
        inputToken.type = inputToken.type === 'password' ? 'text' : 'password';
      });
    }

    if (btnSaveToken && inputToken) {
      btnSaveToken.addEventListener('click', async () => {
        gh.ConfigStore.setToken(inputToken.value.trim());
        gh.RestClient.clearCache();
        updateStorageModeBadge();
        showToast('Token PAT guardado en este dispositivo', 'success');
        renderModalContent();
        if (gh.ConfigStore.isGitHubVault(state.currentVault)) {
          await loadHub();
        }
      });
    }

    // Botones de cada repositorio
    el.modalBody.querySelectorAll('.btn-gh-activate').forEach((btn) => {
      btn.addEventListener('click', async () => {
        if (inputToken && inputToken.value.trim() !== gh.ConfigStore.getToken()) {
          gh.ConfigStore.setToken(inputToken.value.trim());
        }
        const targetId = btn.dataset.id;
        state.currentVault = targetId;
        state.activeYear = null;
        state.activeWeekNumber = null;
        state.activeDayNumber = null;
        gh.ConfigStore.setPreferredVault(targetId);
        await loadVaults();
        if (el.vaultSelect) el.vaultSelect.value = targetId;
        updateStorageModeBadge();
        closeModal();
        await loadHub();
        showToast(`Conectado a ${targetId}`, 'success');
      });
    });

    el.modalBody.querySelectorAll('.btn-gh-verify').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const targetId = btn.dataset.id;
        const vaultObj = gh.ConfigStore.getVaultById(targetId);
        const statusEl = document.getElementById(`ghVerifyStatus-${targetId}`);
        if (!vaultObj || !statusEl) return;
        const tokenToTest = inputToken ? inputToken.value.trim() : gh.ConfigStore.getToken();
        statusEl.style.display = 'block';
        statusEl.textContent = '⏳ Verificando acceso en api.github.com...';
        try {
          const info = await gh.RestClient.verifyRepoAccess(vaultObj, tokenToTest);
          const weeks = await gh.VaultEngine.listAvailableWeeks(vaultObj);
          statusEl.innerHTML = `<span style="color:#4ade80;">✅ Conexión OK: <strong>${escapeHtml(info.full_name)}</strong> (${info.private ? 'Privado 🔒' : 'Público'}) • ${weeks.length} bitácora(s) encontrada(s)</span>`;
        } catch (err) {
          statusEl.innerHTML = `<span style="color:#f87171;">❌ Error: ${escapeHtml(err.message)}</span>`;
        }
      });
    });

    el.modalBody.querySelectorAll('.btn-gh-edit').forEach((btn) => {
      btn.addEventListener('click', () => {
        const vObj = gh.ConfigStore.getVaultById(btn.dataset.id);
        if (vObj) renderModalContent(vObj);
      });
    });

    el.modalBody.querySelectorAll('.btn-gh-delete').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const targetId = btn.dataset.id;
        gh.ConfigStore.removeRemoteVault(targetId);
        await loadVaults();
        renderModalContent();
        showToast('Repositorio eliminado de la lista', 'info');
      });
    });

    const btnSaveVault = document.getElementById('btnSaveGhVault');
    if (btnSaveVault) {
      btnSaveVault.addEventListener('click', async () => {
        const owner = (document.getElementById('inputGhOwner')?.value || '').trim();
        const repo = (document.getElementById('inputGhRepo')?.value || '').trim();
        const name = (document.getElementById('inputGhVaultName')?.value || '').trim() || `☁️ ${repo} (GitHub)`;
        const branch = (document.getElementById('inputGhBranch')?.value || 'main').trim();
        const basePath = (document.getElementById('inputGhBasePath')?.value || '').trim();
        const vaultType = document.getElementById('inputGhVaultType')?.value || 'personal';

        if (!owner || !repo) {
          showToast('Indica al menos el Owner y el nombre del Repositorio', 'error');
          return;
        }

        gh.ConfigStore.upsertRemoteVault({
          id: editingVault ? editingVault.id : `gh:${repo}`,
          name,
          owner,
          repo,
          branch,
          base_path: basePath,
          vault_type: vaultType,
          days_per_week: vaultType === 'personal' ? 7 : 5
        });

        await loadVaults();
        renderModalContent();
        showToast(`Repositorio ${owner}/${repo} guardado`, 'success');
      });
    }
  };

  renderModalContent();
}

window.openGitHubSettingsModal = openGitHubSettingsModal;

document.addEventListener('DOMContentLoaded', () => {
  const btnGh = document.getElementById('btnGitHubConfig');
  if (btnGh) {
    btnGh.addEventListener('click', openGitHubSettingsModal);
  }
  if (el.vaultSelect) {
    el.vaultSelect.addEventListener('change', () => {
      updateStorageModeBadge();
    });
  }
});
