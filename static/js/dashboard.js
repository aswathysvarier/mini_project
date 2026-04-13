let currentResult = null;
let currentFileName = "uploaded_image";
let preparedUploadFile = null;

async function loadModelStatus() {
  const statusEl = document.getElementById("model-status");
  if (!statusEl) return;

  try {
    const res = await fetch("/model_status");
    const data = await res.json();

    if (data.model_ready) {
      statusEl.textContent = `Model ready: ${data.model_name}`;
      statusEl.style.color = "#1f7a4d";
    } else {
      statusEl.textContent = `Model not ready. Add trained weights at ${data.model_path} before analyzing images.`;
      statusEl.style.color = "#b54708";
    }
  } catch (err) {
    statusEl.textContent = "Could not check model status.";
    statusEl.style.color = "#b42318";
  }
}

function getCurrentUser() {
  if (window.isDemoAuth) {
    return window.demoAuth.getCurrentUser();
  }
  return auth.currentUser;
}

function guardDashboardAccess() {
  if (window.isDemoAuth) {
    const user = window.demoAuth.getCurrentUser();
    if (!user) {
      window.location.href = "/";
      return;
    }
    document.getElementById("user-email").textContent = user.email || user.displayName;
    return;
  }

  auth.onAuthStateChanged(user => {
    if (!user) {
      window.location.href = "/";
    } else {
      document.getElementById("user-email").textContent = user.email || user.displayName;
    }
  });
}

function logoutUser() {
  if (window.isDemoAuth) {
    window.demoAuth.logout();
    window.location.href = "/";
    return;
  }

  auth.signOut().then(() => window.location.href = "/");
}

function previewImage(event) {
  const file = event.target.files[0];
  if (!file) return;
  currentFileName = file.name;

  const reader = new FileReader();
  reader.onload = e => {
    const preview = document.getElementById("preview");
    const dropText = document.getElementById("drop-text");
    preview.src = e.target.result;
    preview.classList.remove("hidden");
    dropText.classList.add("hidden");
    document.getElementById("analyze-btn").disabled = false;
  };
  reader.readAsDataURL(file);
}

async function prepareUploadFile(file) {
  if (!file || !file.type.startsWith("image/")) {
    return file;
  }

  if (file.size <= 400 * 1024) {
    return file;
  }

  const imageBitmap = await createImageBitmap(file);
  const maxDimension = 960;
  const scale = Math.min(1, maxDimension / Math.max(imageBitmap.width, imageBitmap.height));
  const width = Math.max(1, Math.round(imageBitmap.width * scale));
  const height = Math.max(1, Math.round(imageBitmap.height * scale));

  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d", { alpha: false });
  context.drawImage(imageBitmap, 0, 0, width, height);

  const blob = await new Promise(resolve => canvas.toBlob(resolve, "image/jpeg", 0.76));
  imageBitmap.close();

  if (!blob || blob.size >= file.size) {
    return file;
  }

  return new File([blob], file.name.replace(/\.[^.]+$/, "") + ".jpg", {
    type: "image/jpeg",
    lastModified: Date.now()
  });
}

const dropZone = document.getElementById("drop-zone");
dropZone.addEventListener("dragover", e => { e.preventDefault(); dropZone.style.borderColor = "#0f3460"; });
dropZone.addEventListener("dragleave", () => { dropZone.style.borderColor = ""; });
dropZone.addEventListener("drop", e => {
  e.preventDefault();
  dropZone.style.borderColor = "";
  const dt = new DataTransfer();
  dt.items.add(e.dataTransfer.files[0]);
  document.getElementById("file-input").files = dt.files;
  previewImage({ target: { files: dt.files } });
});

async function analyzeImage() {
  const fileInput = document.getElementById("file-input");
  if (!fileInput.files.length) return;

  const btn = document.getElementById("analyze-btn");
  btn.textContent = "Analyzing...";
  btn.disabled = true;

  try {
    preparedUploadFile = await prepareUploadFile(fileInput.files[0]);
    const formData = new FormData();
    formData.append("image", preparedUploadFile);

    const res = await fetch("/predict", { method: "POST", body: formData });
    const data = await res.json();

    if (data.error) {
      alert("Error: " + data.error);
      if (res.status === 503) {
        const section = document.getElementById("result-section");
        section.classList.add("hidden");
        await loadModelStatus();
      }
      return;
    }

    currentResult = { ...data, filename: currentFileName };
    showResult(data);
  } catch (err) {
    alert("Server error. Make sure the Flask backend is running.");
  } finally {
    btn.textContent = "Analyze Image";
    btn.disabled = false;
  }
}

function showResult(data) {
  const section = document.getElementById("result-section");
  section.classList.remove("hidden");

  const badge = document.getElementById("verdict-badge");
  badge.textContent = data.label;
  badge.className = "verdict-badge " + data.label.toLowerCase();

  setTimeout(() => {
    document.getElementById("real-bar").style.width = data.real_prob + "%";
    document.getElementById("fake-bar").style.width = data.fake_prob + "%";
  }, 50);

  document.getElementById("real-pct").textContent = data.real_prob + "%";
  document.getElementById("fake-pct").textContent = data.fake_prob + "%";

  const warning = document.getElementById("warning-box");
  const pdfBtn = document.getElementById("pdf-btn");

  if (data.label === "FAKE") {
    warning.classList.remove("hidden");
    pdfBtn.classList.remove("hidden");
  } else {
    warning.classList.add("hidden");
    pdfBtn.classList.add("hidden");
  }

  section.scrollIntoView({ behavior: "smooth" });
}

async function downloadReport() {
  if (!currentResult) return;

  const res = await fetch("/generate_report", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(currentResult)
  });

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "deepshield_report.pdf";
  a.click();
  URL.revokeObjectURL(url);
}

guardDashboardAccess();
loadModelStatus();
