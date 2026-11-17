const fileInput = document.querySelector("#fileInput");
const fileLabel = document.querySelector("#fileLabel");
const fileHint = document.querySelector("#fileHint");
const removeFileButton = document.querySelector("#removeFileButton");
const textInput = document.querySelector("#textInput");
const textStats = document.querySelector("#textStats");
const sampleButton = document.querySelector("#sampleButton");
const formatButton = document.querySelector("#formatButton");
const clearButton = document.querySelector("#clearButton");
const downloadLink = document.querySelector("#downloadLink");
const resultBox = document.querySelector("#resultBox");
const resultTitle = document.querySelector("#resultTitle");
const resultMessage = document.querySelector("#resultMessage");
const stateValue = document.querySelector("#stateValue");
const sizeValue = document.querySelector("#sizeValue");
const modeValue = document.querySelector("#modeValue");
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

const FORMAT_BUTTON_IDLE = `
  <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
    <polyline points="14 2 14 8 20 8" />
    <path d="m9 15 2 2 4-4" />
  </svg>
  <span>Formatar documento</span>
`;

const FORMAT_BUTTON_BUSY = `
  <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <path d="M21 12a9 9 0 1 1-6.219-8.56" />
  </svg>
  <span>Formatando...</span>
`;

const SAMPLE_DOCUMENT = [
  "PADRONIZAÇÃO DIGITAL DE DOCUMENTOS ACADÊMICOS",
  "MARIANA FERREIRA COSTA",
  "RESUMO",
  "Este trabalho analisa a automação da formatação acadêmica conforme as diretrizes da ABNT, avaliando a preservação de conteúdo estrutural, tabelas e citações em documentos digitais.",
  "INTRODUÇÃO",
  "A padronização documental facilita a leitura técnica e garante uniformidade visual em pesquisas científicas.",
  "FUNDAMENTAÇÃO TEÓRICA",
  "Segundo Silva (2022), a organização hierárquica de seções reduz falhas na revisão editorial de trabalhos de conclusão.",
  "CONCLUSÃO",
  "Os resultados indicam ganhos de produtividade mantendo a revisão humana como etapa essencial de validação.",
  "REFERÊNCIAS",
  "SILVA, João. Metodologia e normalização científica. São Paulo: Atlas, 2022.",
].join("\n");

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

const setResult = ({ title, message, state, size, tone = "idle" }) => {
  resultTitle.textContent = title;
  resultMessage.textContent = message;
  stateValue.textContent = state;
  sizeValue.textContent = size || "-";
  resultBox.classList.toggle("is-busy", tone === "busy");
  resultBox.classList.toggle("is-success", tone === "success");
  resultBox.classList.toggle("is-error", tone === "error");
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
  formatButton.innerHTML = busy ? FORMAT_BUTTON_BUSY : FORMAT_BUTTON_IDLE;
};

const selectedFile = () => fileInput.files && fileInput.files[0];

const updateFileLabel = () => {
  const file = selectedFile();
  dropZone.classList.toggle("has-file", Boolean(file));
  if (removeFileButton) removeFileButton.hidden = !file;

  if (!file) {
    fileLabel.textContent = "Selecionar DOCX";
    fileHint.textContent = "Arraste um arquivo .docx (até 5 MB) ou clique para escolher.";
    return;
  }

  fileLabel.textContent = file.name;
  fileHint.textContent = `${formatBytes(file.size)} selecionado`;
};

const updateTextStats = () => {
  if (!textStats) return;
  const raw = textInput.value;
  const trimmed = raw.trim();
  const lines = trimmed ? raw.split(/\r?\n/).filter((line) => line.trim()).length : 0;
  const words = trimmed ? trimmed.split(/\s+/).length : 0;
  textStats.textContent = `${lines} ${lines === 1 ? "linha" : "linhas"} · ${words} ${words === 1 ? "palavra" : "palavras"}`;
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
    tone: "busy",
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
      tone: "success",
    });
  } catch (error) {
    setResult({
      title: "Não foi possível concluir",
      message: error.message,
      state: "Erro",
      tone: "error",
    });
  } finally {
    setBusy(false);
  }
};

const syncModeUI = () => {
  if (metadataFields) {
    metadataFields.hidden = !completeMissingInput.checked;
  }
  if (modeValue) {
    modeValue.textContent = completeMissingInput.checked ? "Completo ABNT" : "Adaptativo";
  }
};

syncModeUI();
updateTextStats();
completeMissingInput.addEventListener("change", syncModeUI);
textInput.addEventListener("input", updateTextStats);

if (sampleButton) {
  sampleButton.addEventListener("click", () => {
    fileInput.value = "";
    updateFileLabel();
    textInput.value = SAMPLE_DOCUMENT;
    updateTextStats();
    textInput.focus();
  });
}

if (removeFileButton) {
  removeFileButton.addEventListener("click", () => {
    fileInput.value = "";
    updateFileLabel();
  });
}

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
  updateTextStats();
  resetDownload();
  setResult({
    title: "Pronto para formatar",
    message: "Escolha uma entrada e gere seu documento ABNT.",
    state: "Aguardando",
    tone: "idle",
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
    const ok = response.ok;
    apiStatus.textContent = ok ? "API online" : "API indisponível";
    apiStatus.classList.toggle("is-online", ok);
    apiStatus.classList.toggle("is-offline", !ok);
  })
  .catch(() => {
    apiStatus.textContent = "API offline";
    apiStatus.classList.remove("is-online");
    apiStatus.classList.add("is-offline");
  });
