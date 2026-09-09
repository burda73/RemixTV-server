import { initUpload } from "./upload.js";
import { loadClients, renderClients } from "./clients.js";
import { apiFetch } from "./api.js";
import {
  loadPlaylist,
  loadVideos,
  renderPlaylist,
  renderVideos,
  savePlaylistOrder,
} from "./playlist.js";

function toast(type, message) {
  const container = document.getElementById("toastContainer");
  const el = document.createElement("div");
  el.className = `toast align-items-center text-bg-${type === "success" ? "success" : type === "warning" ? "warning" : type === "info" ? "info" : "danger"} border-0`;
  el.setAttribute("role", "alert");
  el.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">${message}</div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
    </div>`;
  container.appendChild(el);
  const T = window.bootstrap.Toast;
  const t = new T(el, { delay: 3500 });
  t.show();
  el.addEventListener("hidden.bs.toast", () => el.remove());
}

async function refreshAll() {
  try {
    const [videos, playlist, clients] = await Promise.all([loadVideos(), loadPlaylist(), loadClients()]);
    renderVideos(videos, refreshAll, toast);
    renderPlaylist(playlist, refreshAll, toast);
    renderClients(clients, refreshClients, toast);
  } catch (e) {
    toast("danger", e.message || "Не удалось загрузить данные");
  }
}

async function refreshClients() {
  try {
    const clients = await loadClients();
    renderClients(clients, refreshClients, toast);
  } catch (e) {
    toast("danger", e.message || "Не удалось загрузить клиентов");
  }
}

document.getElementById("btnRefreshVideos").addEventListener("click", refreshAll);
document.getElementById("btnClearVideos").addEventListener("click", async () => {
  if (!confirm("Удалить все видео из библиотеки?")) return;
  try {
    await apiFetch("/api/videos", { method: "DELETE" });
    toast("success", "Библиотека очищена");
    refreshAll();
  } catch (e) {
    toast("danger", e.message || "Ошибка");
  }
});
document.getElementById("btnRefreshPlaylist").addEventListener("click", refreshAll);
document.getElementById("btnSaveOrder").addEventListener("click", () => savePlaylistOrder(toast, refreshAll));
document.getElementById("btnRefreshClients").addEventListener("click", refreshClients);

initUpload(refreshAll, toast);

refreshAll();
setInterval(refreshAll, 30000);
