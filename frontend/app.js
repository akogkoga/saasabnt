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
const completeMissingInput = document.querySelector("#completeMissingInput");
const metadataFields = document.querySelector("#metadataFields");
const metaInputs = {
  institution: document.querySelector("#metaInstitution"),
  author: document.querySelector("#metaAuthor"),
  title: document.querySelector("#metaTitle"),
  advisor: document.querySelector("#metaAdvisor"),
  city: document.querySelector("#metaCity"),
  year: document.querySelector("#metaYear"),
};

let downloadUrl = "";
const MAX_UPLOAD_BYTES = 5 * 1024 * 1024;
const apiBaseUrl = (window.SAAS_ABNT_CONFIG?.apiBaseUrl || "").replace(/\/$/, "");

const apiUrl = (path) => `${apiBaseUrl}${path}`;

const ERROR_MESSAGES = {
  "No input.": "Envie um DOCX ou cole um texto antes de formatar.",
  "Unable to parse DOCX input.": "Não foi possível ler o arquivo DOCX enviado. Verifique se o arquivo é um DOCX válido.",
};

const humanizeErrorMessage = (detail) => {
  if (!detail) return "Não foi possível formatar o documento.";
  return ERROR_MESSAGES[detail] || detail;
};

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

  if (file && text) {
    throw new Error("Escolha apenas um arquivo ou texto para formatar.");
  }
  if (file) {
    if (file.size > MAX_UPLOAD_BYTES) {
      throw new Error("O arquivo DOCX excede o limite de 5 MB.");
    }
    if (file.name && !file.name.toLowerCase().endsWith(".docx")) {
      throw new Error("Envie um arquivo no formato .docx.");
    }
    formData.append("file", file);
  } else if (text) {
    formData.append("text", text);
  } else {
    throw new Error("Envie um DOCX ou cole um texto antes de formatar.");
  }

  formData.append("complete_missing", completeMissingInput.checked ? "true" : "false");
  if (completeMissingInput.checked) {
    Object.entries(metaInputs).forEach(([key, input]) => {
      const val = input?.value?.trim();
      if (val) formData.append(key, val);
    });
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
    message: completeMissingInput.checked
      ? "Completando a estrutura e gerando o DOCX."
      : "Formatando somente as partes enviadas, sem criar campos ausentes.",
    state: "Processando",
  });

  try {
    const response = await fetch(apiUrl("/format"), {
      method: "POST",
      body: buildFormData(),
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(humanizeErrorMessage(payload?.detail));
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
      message: "O DOCX está pronto para download. Revise o conteúdo e a formatação antes de usar.",
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

const syncMetadataVisibility = () => {
  if (!metadataFields) return;
  metadataFields.hidden = !completeMissingInput.checked;
};

syncMetadataVisibility();
completeMissingInput.addEventListener("change", syncMetadataVisibility);

fileInput.addEventListener("change", updateFileLabel);
formatButton.addEventListener("click", formatDocument);

downloadLink.addEventListener("click", (event) => {
  if (!downloadUrl || downloadLink.classList.contains("disabled")) {
    event.preventDefault();
  }
});

clearButton.addEventListener("click", () => {
  fileInput.value = "";
  textInput.value = "";
  Object.values(metaInputs).forEach((input) => {
    if (input) input.value = "";
  });
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

fetch(apiUrl("/health"))
  .then((response) => {
    apiStatus.textContent = response.ok ? "API online" : "API indisponível";
  })
  .catch(() => {
    apiStatus.textContent = "API offline";
  });
