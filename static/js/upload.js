function showProgress(wrap, bar, pct) {
  wrap.classList.remove("d-none");
  bar.style.width = `${pct}%`;
  bar.setAttribute("aria-valuenow", String(pct));
}

function hideProgress(wrap, bar) {
  wrap.classList.add("d-none");
  bar.style.width = "0%";
}

/**
 * Загрузка через XHR для отображения прогресса (крупные файлы).
 */
export function uploadFile(file, onToast) {
  return new Promise((resolve, reject) => {
    const wrap = document.getElementById("uploadProgressWrap");
    const bar = document.getElementById("uploadProgress");
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/upload");
    xhr.responseType = "json";

    xhr.upload.onprogress = (e) => {
      if (!e.lengthComputable) return;
      const pct = Math.round((e.loaded / e.total) * 100);
      showProgress(wrap, bar, pct);
    };

    xhr.onload = () => {
      hideProgress(wrap, bar);
      if (xhr.status >= 200 && xhr.status < 300) {
        onToast("success", "Файл загружен");
        resolve(xhr.response);
      } else {
        const msg = xhr.response && xhr.response.detail ? xhr.response.detail : xhr.statusText;
        onToast("danger", `Ошибка загрузки: ${msg}`);
        reject(new Error(msg));
      }
    };
    xhr.onerror = () => {
      hideProgress(wrap, bar);
      onToast("danger", "Сетевая ошибка при загрузке");
      reject(new Error("network"));
    };

    const data = new FormData();
    data.append("file", file);
    xhr.send(data);
  });
}

export function initUpload(onUploaded, onToast) {
  const input = document.getElementById("fileInput");
  const zone = document.getElementById("dropZone");

  const handleFiles = async (files) => {
    for (const file of files) {
      try {
        await uploadFile(file, onToast);
        onUploaded();
      } catch {
        /* toast уже показан */
      }
    }
    input.value = "";
  };

  input.addEventListener("change", () => handleFiles(Array.from(input.files || [])));

  ["dragenter", "dragover"].forEach((ev) => {
    zone.addEventListener(ev, (e) => {
      e.preventDefault();
      e.stopPropagation();
      zone.classList.add("dragover");
    });
  });
  ["dragleave", "drop"].forEach((ev) => {
    zone.addEventListener(ev, (e) => {
      e.preventDefault();
      e.stopPropagation();
      zone.classList.remove("dragover");
    });
  });
  zone.addEventListener("drop", (e) => {
    const dt = e.dataTransfer;
    if (!dt) return;
    handleFiles(Array.from(dt.files || []));
  });
}
