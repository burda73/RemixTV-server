import { apiFetch } from "./api.js";

function toDatetimeLocalValue(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (n) => String(n).padStart(2, "0");
  const yyyy = d.getFullYear();
  const mm = pad(d.getMonth() + 1);
  const dd = pad(d.getDate());
  const hh = pad(d.getHours());
  const mi = pad(d.getMinutes());
  return `${yyyy}-${mm}-${dd}T${hh}:${mi}`;
}

function fromDatetimeLocalValue(val) {
  if (!val) return null;
  const d = new Date(val);
  if (Number.isNaN(d.getTime())) return null;
  return d.toISOString();
}

let dragRow = null;

function wireDragDrop(tbody) {
  tbody.querySelectorAll("tr[data-id]").forEach((row) => {
    row.setAttribute("draggable", "true");
    row.addEventListener("dragstart", () => {
      dragRow = row;
      row.classList.add("dragging");
    });
    row.addEventListener("dragend", () => {
      row.classList.remove("dragging");
      dragRow = null;
    });
    row.addEventListener("dragover", (e) => {
      e.preventDefault();
      if (!dragRow || dragRow === row) return;
      const rect = row.getBoundingClientRect();
      const before = e.clientY < rect.top + rect.height / 2;
      tbody.insertBefore(dragRow, before ? row : row.nextSibling);
    });
  });
}

export async function loadVideos() {
  return apiFetch("/api/videos");
}

export async function loadPlaylist() {
  return apiFetch("/api/playlist");
}

export function renderVideos(videos, onAdd, onToast) {
  const ul = document.getElementById("videoList");
  ul.innerHTML = "";
  if (!videos.length) {
    ul.innerHTML = '<li class="list-group-item text-muted">Нет загруженных видео</li>';
    return;
  }
  for (const v of videos) {
    const li = document.createElement("li");
    li.className = "list-group-item d-flex justify-content-between align-items-start";
    const sizeMb = (v.file_size / (1024 * 1024)).toFixed(2);
    li.innerHTML = `
      <div class="me-2 flex-grow-1">
        <div class="fw-semibold text-break">
          <span class="filename-display">${v.filename}</span>
          <button class="btn btn-sm btn-link p-0 ms-1 btn-rename" data-id="${v.id}" data-name="${v.filename}" title="Переименовать">✏️</button>
        </div>
        <div class="small text-muted">${sizeMb} МБ · v${v.version} · ${v.file_hash.slice(0, 8)}…</div>
      </div>
      <div class="btn-group shrink-0">
        <button class="btn btn-sm btn-outline-secondary btn-preview" data-id="${v.id}" title="Просмотр">▶</button>
        <button class="btn btn-sm btn-outline-primary btn-download" data-id="${v.id}" title="Скачать">⬇</button>
        <button class="btn btn-sm btn-outline-success btn-add" data-id="${v.id}">В плейлист</button>
        <button class="btn btn-sm btn-outline-danger btn-delete" data-id="${v.id}">×</button>
      </div>
    `;
    li.querySelector(".btn-add").addEventListener("click", async () => {
      try {
        await apiFetch("/api/playlist", {
          method: "POST",
          body: JSON.stringify({ video_id: v.id }),
        });
        onToast("success", "Добавлено в плейлист");
        onAdd();
      } catch (e) {
        onToast("danger", e.message || "Ошибка");
      }
    });
    li.querySelector(".btn-preview").addEventListener("click", () => {
      const modal = new bootstrap.Modal(document.getElementById("videoModal"));
      const player = document.getElementById("videoPlayer");
      const title = document.getElementById("videoModalTitle");
      player.src = `/api/videos/${v.id}/preview`;
      player.type = getVideoMime(v.filename);
      title.textContent = v.filename;
      modal.show();
      player.onerror = () => {
        onToast("danger", "Не удалось воспроизвести видео");
        modal.hide();
      };
    });
    li.querySelector(".btn-download").addEventListener("click", () => {
      window.location.href = `/api/videos/${v.id}/download`;
    });
    li.querySelector(".btn-rename").addEventListener("click", async () => {
      const newName = prompt("Новое имя файла:", v.filename);
      if (!newName || newName === v.filename) return;
      try {
        await apiFetch(`/api/videos/${v.id}`, {
          method: "PATCH",
          body: JSON.stringify({ filename: newName }),
        });
        onToast("success", "Файл переименован");
        onAdd();
      } catch (e) {
        onToast("danger", e.message || "Ошибка");
      }
    });
    li.querySelector(".btn-delete").addEventListener("click", async () => {
      if (!confirm("Удалить видео из библиотеки?")) return;
      try {
        await apiFetch(`/api/videos/${v.id}`, { method: "DELETE" });
        onToast("success", "Видео удалено");
        onAdd();
      } catch (e) {
        onToast("danger", e.message || "Ошибка");
      }
    });
    ul.appendChild(li);
  }
}

function getVideoMime(filename) {
  const ext = filename.split(".").pop().toLowerCase();
  const mimes = {
    mp4: "video/mp4",
    mkv: "video/x-matroska",
    webm: "video/webm",
    avi: "video/x-msvideo",
    mov: "video/quicktime",
  };
  return mimes[ext] || "video/mp4";
}

export function renderPlaylist(items, onChange, onToast) {
  const tbody = document.getElementById("playlistBody");
  tbody.innerHTML = "";
  const sorted = [...items].sort((a, b) => a.order - b.order);
  for (const it of sorted) {
    const tr = document.createElement("tr");
    tr.dataset.id = String(it.id);
    tr.innerHTML = `
      <td class="handle">☰</td>
      <td>
        <div class="d-flex align-items-center gap-2">
          <button class="btn btn-sm btn-outline-secondary btn-preview" data-id="${it.video.id}" title="Просмотр">▶</button>
          <span class="text-break">${it.video.filename}</span>
        </div>
      </td>
      <td><input type="datetime-local" class="form-control form-control-sm inp-start" value="${toDatetimeLocalValue(it.start_date)}"></td>
      <td><input type="datetime-local" class="form-control form-control-sm inp-end" value="${toDatetimeLocalValue(it.end_date)}"></td>
      <td class="text-center"><input type="checkbox" class="form-check-input inp-active" ${it.is_active ? "checked" : ""}></td>
      <td><button class="btn btn-sm btn-outline-danger btn-del">Удалить</button></td>
    `;
    tr.querySelector(".btn-del").addEventListener("click", async () => {
      if (!confirm("Удалить из плейлиста?")) return;
      try {
        await apiFetch(`/api/playlist/${it.id}`, { method: "DELETE" });
        onToast("success", "Удалено");
        onChange();
      } catch (e) {
        onToast("danger", e.message || "Ошибка");
      }
    });
    tr.querySelector(".btn-preview").addEventListener("click", () => {
      const modal = new bootstrap.Modal(document.getElementById("videoModal"));
      const player = document.getElementById("videoPlayer");
      const title = document.getElementById("videoModalTitle");
      player.src = `/api/videos/${it.video.id}/preview`;
      player.type = getVideoMime(it.video.filename);
      title.textContent = it.video.filename;
      modal.show();
      player.onerror = () => {
        onToast("danger", "Не удалось воспроизвести видео");
        modal.hide();
      };
    });
    const saveRow = async () => {
      const start = fromDatetimeLocalValue(tr.querySelector(".inp-start").value);
      const end = fromDatetimeLocalValue(tr.querySelector(".inp-end").value);
      if (start && end && new Date(start) > new Date(end)) {
        onToast("warning", "Дата начала позже даты окончания");
        return;
      }
      const body = {
        start_date: start,
        end_date: end,
        is_active: tr.querySelector(".inp-active").checked,
      };
      try {
        await apiFetch(`/api/playlist/${it.id}`, { method: "PUT", body: JSON.stringify(body) });
        onToast("success", "Сохранено");
        onChange();
      } catch (e) {
        onToast("danger", e.message || "Ошибка");
      }
    };
    tr.querySelectorAll(".inp-start, .inp-end, .inp-active").forEach((el) => {
      el.addEventListener("change", saveRow);
    });
    tbody.appendChild(tr);
  }

  wireDragDrop(tbody);
}

export async function savePlaylistOrder(onToast, onReload) {
  const tbody = document.getElementById("playlistBody");
  const rows = Array.from(tbody.querySelectorAll("tr[data-id]"));
  const items = rows.map((row, idx) => ({ id: Number(row.dataset.id), order: idx }));
  if (!items.length) {
    onToast("info", "Плейлист пуст");
    return;
  }
  try {
    await apiFetch("/api/playlist/reorder", {
      method: "POST",
      body: JSON.stringify({ items }),
    });
    onToast("success", "Порядок сохранён");
    await onReload();
  } catch (e) {
    onToast("danger", e.message || "Ошибка");
  }
}
