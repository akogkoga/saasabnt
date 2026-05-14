const fileInput = document.querySelector("#fileInput");
const fileLabel = document.querySelector("#fileLabel");
const fileHint = document.querySelector("#fileHint");
const textInput = document.querySelector("#textInput");
const formatButton = document.querySelector("#formatButton");
const clearButton = document.querySelector("#clearButton");
const downloadLink = document.querySelector("#downloadLink");
const resultBox = document.querySelector("#resultBox");
const resultTitle = document.querySelector("#resultTitle");
const resultMessage = document.querySelector("#resultMessage");
const stateValue = document.querySelector("#stateValue");
const sizeValue = document.querySelector("#sizeValue");
const dropZone = document.querySelector("#dropZone");
const apiStatus = document.querySelector("#apiStatus");
const downloadModal = document.querySelector("#downloadModal");
const continueDownloadButton = document.querySelector("#continueDownloadButton");

let downloadUrl = "";
const apiBaseUrl = (window.SAAS_ABNT_CONFIG?.apiBaseUrl || "").replace(/\/$/, "");

const apiUrl = (path) => `${apiBaseUrl}${path}`;

const formatBytes = (bytes) => {
  if (!bytes) return "-";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
};

const setResult = ({ title, message, state, size, error = false }) => {
  resultTitle.textContent = title;
  resultMessage.textContent = message;
  stateValue.textContent = state;
  sizeValue.textContent = size || "-";
  resultBox.classList.toggle("is-error", error);
};

const resetDownload = () => {
  if (downloadUrl) URL.revokeObjectURL(downloadUrl);
  downloadUrl = "";
  downloadLink.removeAttribute("href");
  downloadLink.classList.add("disabled");
  downloadLink.setAttribute("aria-disabled", "true");
};

const setBusy = (busy) => {
  formatButton.disabled = busy;
  formatButton.innerHTML = busy
    ? '<span aria-hidden="true">...</span> Formatando'
    : '<span aria-hidden="true">↧</span> Formatar documento';
};

const selectedFile = () => fileInput.files && fileInput.files[0];

const openDownloadModal = () => {
  downloadModal.hidden = false;
  continueDownloadButton.focus();
};

const closeDownloadModal = () => {
  downloadModal.hidden = true;
};

const triggerDownload = () => {
  if (!downloadUrl) return;

  const anchor = document.createElement("a");
  anchor.href = downloadUrl;
  anchor.download = downloadLink.download || "documento_abnt_v6.docx";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
};

const updateFileLabel = () => {
  const file = selectedFile();
  if (!file) {
    fileLabel.textContent = "Selecionar DOCX";
    fileHint.textContent = "Arraste um arquivo ou clique para escolher.";
    return;
  }

  fileLabel.textContent = file.name;
  fileHint.textContent = `${formatBytes(file.size)} selecionado`;
};

const buildFormData = () => {
  const formData = new FormData();
  const file = selectedFile();
  const text = textInput.value.trim();

  if (file) {
    formData.append("file", file);
  } else if (text) {
    formData.append("text", text);
  } else {
    throw new Error("Envie um DOCX ou cole um texto antes de formatar.");
  }

  return formData;
};

const downloadFilename = (contentDisposition) => {
  const fallback = "documento_abnt_v6.docx";
  if (!contentDisposition) return fallback;

  const match = contentDisposition.match(/filename="?([^"]+)"?/i);
  return match ? match[1] : fallback;
};

const formatDocument = async () => {
  resetDownload();
  setBusy(true);
  setResult({
    title: "Formatando documento",
    message: "Compilando estrutura, validando IR e gerando o DOCX final.",
    state: "Processando",
  });

  try {
    const response = await fetch(apiUrl("/format"), {
      method: "POST",
      body: buildFormData(),
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(payload?.detail || "Não foi possível formatar o documento.");
    }

    const blob = await response.blob();
    downloadUrl = URL.createObjectURL(blob);
    downloadLink.href = downloadUrl;
    downloadLink.download = downloadFilename(response.headers.get("Content-Disposition"));
    downloadLink.classList.remove("disabled");
    downloadLink.setAttribute("aria-disabled", "false");

    const state = response.headers.get("X-Compilation-State") || "finalized";
    setResult({
      title: "Documento finalizado",
      message: "O DOCX formatado está pronto para download.",
      state,
      size: formatBytes(blob.size),
    });
  } catch (error) {
    setResult({
      title: "Não foi possível concluir",
      message: error.message,
      state: "Erro",
      error: true,
    });
  } finally {
    setBusy(false);
  }
};

fileInput.addEventListener("change", updateFileLabel);
formatButton.addEventListener("click", formatDocument);

downloadLink.addEventListener("click", (event) => {
  if (!downloadUrl || downloadLink.classList.contains("disabled")) {
    event.preventDefault();
    return;
  }

  event.preventDefault();
  openDownloadModal();
});

continueDownloadButton.addEventListener("click", () => {
  closeDownloadModal();
  triggerDownload();
});

clearButton.addEventListener("click", () => {
  fileInput.value = "";
  textInput.value = "";
  updateFileLabel();
  resetDownload();
  setResult({
    title: "Pronto para formatar",
    message: "Escolha uma entrada e gere seu documento ABNT.",
    state: "Aguardando",
  });
});

["dragenter", "dragover"].forEach((eventName) => {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.add("is-dragging");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  dropZone.addEventListener(eventName, () => {
    dropZone.classList.remove("is-dragging");
  });
});

dropZone.addEventListener("drop", (event) => {
  event.preventDefault();
  const file = event.dataTransfer.files && event.dataTransfer.files[0];
  if (!file) return;

  const transfer = new DataTransfer();
  transfer.items.add(file);
  fileInput.files = transfer.files;
  updateFileLabel();
});

fetch(apiUrl("/openapi.json"))
  .then((response) => {
    apiStatus.textContent = response.ok ? "API online" : "API indisponível";
  })
  .catch(() => {
    apiStatus.textContent = "API offline";
  });
