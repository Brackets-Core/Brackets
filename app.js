/**
 * Brackets Web Hub — Frontend Vanilla JavaScript
 * Cero frameworks, cero dependencias, carga ultra rápida.
 */

// Estado de la aplicación
const state = {
  currentVault: null,
  activeDayNumber: null,
  hubData: null,
  createStatus: 'pending', // 'pending' | 'done'
  deferredPrompt: null
};

// Elementos del DOM
const el = {
  vaultSelect: document.getElementById('vaultSelect'),
  weekBadge: document.getElementById('weekBadge'),
  weightBadge: document.getElementById('weightBadge'),
  daysStrip: document.getElementById('daysStrip'),
  activeDayTitle: document.getElementById('activeDayTitle'),
  locGroup: document.getElementById('locGroup'),
  todayTasksList: document.getElementById('todayTasksList'),
  weekTasksList: document.getElementById('weekTasksList'),
  notesContainer: document.getElementById('notesContainer'),
  taskInput: document.getElementById('taskInput'),
  descTextarea: document.getElementById('descTextarea'),
  btnAddTask: document.getElementById('btnAddTask'),
  btnTogglePending: document.getElementById('btnTogglePending'),
  btnToggleDone: document.getElementById('btnToggleDone'),
  btnSync: document.getElementById('btnSync'),
  btnPwaInstall: document.getElementById('btnPwaInstall')
};

// ---------------------------------------------------------------------------
// Inicialización y Registro de PWA
// ---------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', async () => {
  setupPwaInstall();
  setupEventListeners();
  await loadVaults();
  await loadHub();
});

function setupPwaInstall() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('./sw.js').catch((err) => {
      console.warn('Service Worker registration failed:', err);
    });
  }

  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    state.deferredPrompt = e;
    if (el.btnPwaInstall) {
      el.btnPwaInstall.style.display = 'inline-flex';
    }
  });

  if (el.btnPwaInstall) {
    el.btnPwaInstall.addEventListener('click', async () => {
      if (!state.deferredPrompt) return;
      state.deferredPrompt.prompt();
      const { outcome } = await state.deferredPrompt.userChoice;
      if (outcome === 'accepted') {
        el.btnPwaInstall.style.display = 'none';
      }
      state.deferredPrompt = null;
    });
  }
}

// ---------------------------------------------------------------------------
// Event Listeners
// ---------------------------------------------------------------------------
function setupEventListeners() {
  // Cambio de Vault
  el.vaultSelect.addEventListener('change', async (e) => {
    state.currentVault = e.target.value;
    state.activeDayNumber = null;
    await loadHub();
  });

  // Botón Sincronizar
  el.btnSync.addEventListener('click', async () => {
    el.btnSync.style.opacity = '0.5';
    try {
      const res = await fetch('/api/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ vault: state.currentVault })
      });
      const data = await res.json();
      if (data.status === 'ok') {
        await loadHub();
      }
    } catch (err) {
      console.error('Error al sincronizar:', err);
    } finally {
      el.btnSync.style.opacity = '1';
    }
  });

  // Selector de Estado en Captura (Pendiente vs Resuelta [x])
  el.btnTogglePending.addEventListener('click', () => setCreateMode('pending'));
  el.btnToggleDone.addEventListener('click', () => setCreateMode('done'));

  // Añadir Tarea
  el.btnAddTask.addEventListener('click', handleCreateTask);

  // Atajos de Teclado
  el.taskInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleCreateTask();
    }
  });

  el.descTextarea.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      handleCreateTask();
    }
  });
}

function setCreateMode(mode) {
  state.createStatus = mode;
  if (mode === 'done') {
    el.btnToggleDone.classList.add('active', 'done-mode');
    el.btnTogglePending.classList.remove('active');
    el.btnAddTask.classList.add('done-mode');
    el.btnAddTask.textContent = 'Registrar Hecha [x]';
    el.taskInput.placeholder = '¿Qué tarea has completado hoy?...';
  } else {
    el.btnTogglePending.classList.add('active');
    el.btnToggleDone.classList.remove('active', 'done-mode');
    el.btnAddTask.classList.remove('done-mode');
    el.btnAddTask.textContent = 'Añadir Pendiente [ ]';
    el.taskInput.placeholder = 'Nueva tarea para hoy... (ej: Reunión: Sync #[PROYECTO])';
  }
}

// ---------------------------------------------------------------------------
// Carga de Datos desde la API
// ---------------------------------------------------------------------------
async function loadVaults() {
  try {
    const res = await fetch('/api/vaults');
    const data = await res.json();
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

    const res = await fetch(url);
    const data = await res.json();
    state.hubData = data;

    renderHub(data);
  } catch (err) {
    console.error('Error cargando Daily Hub:', err);
  }
}

// ---------------------------------------------------------------------------
// Renderizado de Componentes
// ---------------------------------------------------------------------------
function renderHub(data) {
  if (!data.week) {
    el.todayTasksList.innerHTML = `<div class="empty-state">${data.message || 'No hay semana activa.'}</div>`;
    return;
  }

  // 1. Banner de Semana
  el.weekBadge.textContent = `🗓️ Semana ${data.week.week_number} (${data.week.year})`;
  if (data.week.weight) {
    el.weightBadge.textContent = `⚖️ ${data.week.weight} kg`;
    el.weightBadge.style.display = 'inline-block';
  } else {
    el.weightBadge.style.display = 'none';
  }

  // 2. Tira de Días
  el.daysStrip.innerHTML = '';
  data.days.forEach((day) => {
    const chip = document.createElement('div');
    chip.className = `day-chip ${day.is_active ? 'active' : ''} ${day.is_today ? 'today' : ''}`;
    chip.innerHTML = `
      <span class="day-loc-emoji">${day.location_emoji || '📅'}</span>
      <span class="day-number">Día ${day.day_number}</span>
      <span class="day-badge-count">${day.task_count} tareas</span>
    `;
    chip.addEventListener('click', () => {
      state.activeDayNumber = day.day_number;
      loadHub();
    });
    el.daysStrip.appendChild(chip);
  });

  // 3. Encabezado del Día Activo
  if (data.active_day) {
    const noteText = data.active_day.location_note ? ` (${data.active_day.location_note})` : '';
    el.activeDayTitle.textContent = `${data.active_day.location_emoji} Día ${data.active_day.day_number}${noteText}`;
    renderLocationButtons(data.active_day.day_number, data.active_day.location_emoji);
  }

  // 4. Lista de Tareas de Hoy
  renderTaskList(el.todayTasksList, data.today_tasks, 'No hay tareas asignadas para hoy.');

  // 5. Lista de Tareas de la Semana
  renderTaskList(el.weekTasksList, data.week_tasks, 'No hay tareas semanales pendientes.');

  // 6. Lista de Notas
  renderNotesList(data.notes);
}

function renderLocationButtons(dayNumber, currentEmoji) {
  const locations = [
    { emoji: '🏠', label: 'Casa' },
    { emoji: '🚗', label: 'Oficina' },
    { emoji: '💻', label: 'Remoto' },
    { emoji: '🏖️', label: 'Libre' }
  ];

  el.locGroup.innerHTML = '';
  locations.forEach((loc) => {
    const btn = document.createElement('button');
    btn.className = `btn-loc ${currentEmoji === loc.emoji ? 'selected' : ''}`;
    btn.textContent = `${loc.emoji} ${loc.label}`;
    btn.title = `Cambiar ubicación a ${loc.label}`;
    btn.addEventListener('click', async () => {
      try {
        await fetch(`/api/days/${dayNumber}/location`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            vault: state.currentVault,
            emoji: loc.emoji
          })
        });
        await loadHub();
      } catch (err) {
        console.error('Error al cambiar ubicación:', err);
      }
    });
    el.locGroup.appendChild(btn);
  });
}

function renderTaskList(container, tasks, emptyMsg) {
  container.innerHTML = '';
  if (!tasks || tasks.length === 0) {
    container.innerHTML = `<div class="empty-state">${emptyMsg}</div>`;
    return;
  }

  tasks.forEach((task) => {
    const card = document.createElement('div');
    card.className = `task-card ${task.is_done ? 'done' : ''} ${task.is_cancelled ? 'cancelled' : ''}`;

    const premojiSpan = task.premoji ? `<span class="task-premoji">${task.premoji}</span>` : '';
    const projSpan = task.project_id ? `<span class="task-project-tag">${task.project_id}</span>` : '';

    let descHtml = '';
    if (task.description) {
      const lines = task.description.split('\n').filter((l) => l.trim().length > 0);
      descHtml = `<div class="task-desc-box">${lines.map((l) => `<div class="task-desc-line">💬 ${escapeHtml(l)}</div>`).join('')}</div>`;
    }

    card.innerHTML = `
      <div class="task-main-row">
        <input type="checkbox" class="task-checkbox" ${task.is_done ? 'checked' : ''}>
        <div class="task-content">
          ${premojiSpan}
          <span class="task-title">${escapeHtml(task.title)}</span>
          ${projSpan}
        </div>
      </div>
      ${descHtml}
    `;

    const chk = card.querySelector('.task-checkbox');
    chk.addEventListener('change', async () => {
      try {
        await fetch(`/api/tasks/${task.id}/toggle`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ vault: state.currentVault })
        });
        await loadHub();
      } catch (err) {
        console.error('Error al cambiar estado de tarea:', err);
      }
    });

    container.appendChild(card);
  });
}

function renderNotesList(notes) {
  el.notesContainer.innerHTML = '';
  if (!notes || notes.length === 0) {
    el.notesContainer.innerHTML = `<div class="empty-state">No hay notas registradas en esta semana.</div>`;
    return;
  }

  notes.forEach((note) => {
    const card = document.createElement('div');
    card.className = 'note-card';

    const bulletsHtml = (note.content || [])
      .map((b) => `<li class="note-bullet">${escapeHtml(b)}</li>`)
      .join('');

    card.innerHTML = `
      <div class="note-header">
        <span>📌 ${escapeHtml(note.title)}</span>
        ${note.project_id ? `<span class="task-project-tag">${escapeHtml(note.project_id)}</span>` : ''}
      </div>
      <ul>${bulletsHtml}</ul>
    `;
    el.notesContainer.appendChild(card);
  });
}

// ---------------------------------------------------------------------------
// Acciones de Creación de Tareas
// ---------------------------------------------------------------------------
async function handleCreateTask() {
  const title = el.taskInput.value.trim();
  if (!title) return;

  const desc = el.descTextarea.value.trim();
  const target = state.activeDayNumber ? `day:${state.activeDayNumber}` : 'today';

  el.btnAddTask.disabled = true;
  try {
    const res = await fetch('/api/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        vault: state.currentVault,
        title: title,
        target: target,
        status: state.createStatus,
        description: desc || null
      })
    });

    if (res.ok) {
      el.taskInput.value = '';
      el.descTextarea.value = '';
      await loadHub();
    }
  } catch (err) {
    console.error('Error creando tarea:', err);
  } finally {
    el.btnAddTask.disabled = false;
    el.taskInput.focus();
  }
}

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
