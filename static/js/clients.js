import { apiFetch } from "./api.js";

export async function loadClients() {
  return apiFetch("/api/clients");
}

export function renderClients(clients, onReload, onToast) {
  const tbody = document.getElementById("clientsBody");
  tbody.innerHTML = "";
  if (!clients.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="text-muted text-center">Нет клиентов</td></tr>';
    return;
  }
  for (const c of clients) {
    const tr = document.createElement("tr");
    const isActive = c.is_active;
    const lastSync = c.last_sync ? new Date(c.last_sync).toLocaleString("ru-RU") : "—";
    tr.innerHTML = `
      <td>${c.id}</td>
      <td class="text-break"><code class="small">${c.client_id}</code></td>
      <td>
        <input type="text" class="form-control form-control-sm inp-name" value="${c.name || ""}" placeholder="Имя клиента" data-id="${c.id}">
      </td>
      <td>
        <span class="badge ${c.is_online ? "bg-success" : "bg-secondary"}">${c.is_online ? "Онлайн" : "Офлайн"}</span>
        <span class="badge ${isActive ? "bg-primary" : "bg-warning"} ms-1">${isActive ? "Вкл" : "Выкл"}</span>
      </td>
      <td class="small text-muted">${lastSync}</td>
      <td class="small">
        ${c.synced_playlist_version === c.current_playlist_version 
          ? `<span class="badge bg-success">v${c.synced_playlist_version}</span>` 
          : `<span class="badge bg-warning text-dark">v${c.synced_playlist_version}</span> / v${c.current_playlist_version}`}
      </td>
      <td>
        <div class="btn-group btn-group-sm">
          <button class="btn btn-outline-${isActive ? "warning" : "success"} btn-toggle" data-id="${c.id}" data-active="${!isActive}">
            ${isActive ? "Деакт." : "Акт."}
          </button>
          <button class="btn btn-outline-danger btn-delete" data-id="${c.id}">×</button>
        </div>
      </td>
    `;

    const inpName = tr.querySelector(".inp-name");
    let nameTimeout = null;
    inpName.addEventListener("input", () => {
      clearTimeout(nameTimeout);
      nameTimeout = setTimeout(async () => {
        try {
          await apiFetch(`/api/clients/${c.id}`, {
            method: "PATCH",
            body: JSON.stringify({ name: inpName.value || null }),
          });
        } catch (e) {
          onToast("danger", e.message || "Ошибка сохранения имени");
        }
      }, 500);
    });

    tr.querySelector(".btn-toggle").addEventListener("click", async () => {
      const newActive = tr.querySelector(".btn-toggle").dataset.active === "true";
      try {
        await apiFetch(`/api/clients/${c.id}/toggle`, {
          method: "PUT",
          body: JSON.stringify({ is_active: newActive }),
        });
        onToast("success", newActive ? "Клиент активирован" : "Клиент деактивирован");
        onReload();
      } catch (e) {
        onToast("danger", e.message || "Ошибка");
      }
    });
    tr.querySelector(".btn-delete").addEventListener("click", async () => {
      if (!confirm("Удалить клиента?")) return;
      try {
        await apiFetch(`/api/clients/${c.id}`, { method: "DELETE" });
        onToast("success", "Клиент удалён");
        onReload();
      } catch (e) {
        onToast("danger", e.message || "Ошибка");
      }
    });
    tbody.appendChild(tr);
  }
}
