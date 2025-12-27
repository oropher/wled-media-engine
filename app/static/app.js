const healthBadge = document.getElementById("health");
const btn = document.getElementById("btnTest");
const menuToggle = document.getElementById("menuToggle");
const sidebar = document.getElementById("sidebar");
const sidebarOverlay = document.getElementById("sidebarOverlay");

// Upload elements
const uploadArea = document.getElementById("uploadArea");
const fileInput = document.getElementById("fileInput");
const uploadMessage = document.getElementById("uploadMessage");

// Steps
const uploadStep1 = document.getElementById("uploadStep1");
const uploadStep2 = document.getElementById("uploadStep2");

// Preview elements
const originalImage = document.getElementById("originalImage");
const matrixPreview = document.getElementById("matrixPreview");
const imageName = document.getElementById("imageName");
const cancelBtn = document.getElementById("cancelBtn");
const saveBtn = document.getElementById("saveBtn");
const saveMessage = document.getElementById("saveMessage");

// State
let currentImageFile = null;
let matrixWidth = 20;
let matrixHeight = 20;

function checkHealth() {
  fetch("/api/health")
    .then(r => r.json())
    .then(() => {
      healthBadge.textContent = "OK";
      healthBadge.className = "badge bg-success";
    })
    .catch(() => {
      healthBadge.textContent = "ERROR";
      healthBadge.className = "badge bg-danger";
    });
}

// Toggle sidebar visibility
function toggleSidebar() {
  sidebar.classList.toggle("show");
  sidebarOverlay.classList.toggle("show");
}

// Close sidebar when clicking overlay
sidebarOverlay.addEventListener("click", () => {
  sidebar.classList.remove("show");
  sidebarOverlay.classList.remove("show");
});

// Menu navigation event listeners
document.querySelectorAll(".sidebar .nav-link").forEach(link => {
  link.addEventListener("click", (e) => {
    e.preventDefault();
    
    // Hide all sections
    document.querySelectorAll(".content-section").forEach(section => {
      section.classList.add("d-none");
    });
    
    // Remove active class from all links
    document.querySelectorAll(".sidebar .nav-link").forEach(l => {
      l.classList.remove("active");
    });
    
    // Show selected section
    const sectionId = link.getAttribute("data-section");
    const selectedSection = document.getElementById(sectionId);
    selectedSection.classList.remove("d-none");
    link.classList.add("active");
    
    // Load config if settings section is clicked
    if (sectionId === "settings") {
      loadConfig();
    }
    
    // Close sidebar on mobile
    if (window.innerWidth <= 768) {
      sidebar.classList.remove("show");
      sidebarOverlay.classList.remove("show");
    }
  });
});

// ====== UPLOAD FUNCTIONALITY ======

uploadArea.addEventListener("click", () => fileInput.click());

uploadArea.addEventListener("dragover", (e) => {
  e.preventDefault();
  uploadArea.classList.add("dragover");
});

uploadArea.addEventListener("dragleave", () => {
  uploadArea.classList.remove("dragover");
});

uploadArea.addEventListener("drop", (e) => {
  e.preventDefault();
  uploadArea.classList.remove("dragover");
  const file = e.dataTransfer.files[0];
  if (file && file.type.startsWith("image/")) {
    handleImageUpload(file);
  }
});

fileInput.addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (file && file.type.startsWith("image/")) {
    handleImageUpload(file);
  }
});

function handleImageUpload(file) {
  currentImageFile = file;
  imageName.value = file.name.replace(/\.[^/.]+$/, "");
  
  const reader = new FileReader();
  reader.onload = (e) => {
    const img = new Image();
    img.onload = () => {
      originalImage.src = e.target.result;
      loadMatrixDimensions().then(() => {
        generateMatrixPreview(img);
        uploadStep1.style.display = "none";
        uploadStep2.style.display = "block";
      });
    };
    img.src = e.target.result;
  };
  reader.readAsDataURL(file);
}

function loadMatrixDimensions() {
  return fetch("/api/config/")
    .then(r => r.json())
    .then(data => {
      if (data.data.matrix) {
        matrixWidth = data.data.matrix.width;
        matrixHeight = data.data.matrix.height;
        document.getElementById("matrixDims").textContent = `${matrixWidth}x${matrixHeight}`;
      }
    })
    .catch(e => console.error("Error loading config:", e));
}

function generateMatrixPreview(img) {
  const canvas = matrixPreview;
  const ctx = canvas.getContext("2d");
  
  // Configurar tamaño del canvas para preview ampliado
  const pixelSize = 20;
  canvas.width = matrixWidth * pixelSize;
  canvas.height = matrixHeight * pixelSize;
  
  // Crear canvas temporal para redimensionar la imagen
  const tempCanvas = document.createElement("canvas");
  tempCanvas.width = matrixWidth;
  tempCanvas.height = matrixHeight;
  const tempCtx = tempCanvas.getContext("2d");
  
  // Redimensionar imagen manteniendo aspecto
  const imgAspect = img.width / img.height;
  const matrixAspect = matrixWidth / matrixHeight;
  
  let drawWidth, drawHeight, drawX = 0, drawY = 0;
  
  if (imgAspect > matrixAspect) {
    drawHeight = matrixHeight;
    drawWidth = drawHeight * imgAspect;
    drawX = (matrixWidth - drawWidth) / 2;
  } else {
    drawWidth = matrixWidth;
    drawHeight = drawWidth / imgAspect;
    drawY = (matrixHeight - drawHeight) / 2;
  }
  
  tempCtx.drawImage(img, drawX, drawY, drawWidth, drawHeight);
  
  // Dibujar en canvas con ampliación
  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(tempCanvas, 0, 0, matrixWidth, matrixHeight, 0, 0, canvas.width, canvas.height);
}

cancelBtn.addEventListener("click", () => {
  uploadStep1.style.display = "block";
  uploadStep2.style.display = "none";
  currentImageFile = null;
  imageName.value = "";
  fileInput.value = "";
});

saveBtn.addEventListener("click", () => {
  if (!imageName.value) {
    showSaveMessage("Por favor ingresa un nombre", "warning");
    return;
  }
  
  if (!currentImageFile) {
    showSaveMessage("No hay imagen cargada", "warning");
    return;
  }
  
  const isGif = currentImageFile.type === "image/gif";
  
  console.log("File type:", currentImageFile.type, "Is GIF:", isGif);
  
  if (isGif) {
    // Para GIF, enviar el archivo original al backend
    const formData = new FormData();
    formData.append("image", currentImageFile);
    formData.append("name", imageName.value);
    formData.append("is_gif", "true");
    
    console.log("Uploading as GIF");
    
    fetch("/api/upload", {
      method: "POST",
      body: formData
    })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          showSaveMessage("GIF guardado exitosamente", "success");
          setTimeout(() => {
            uploadStep1.style.display = "block";
            uploadStep2.style.display = "none";
            currentImageFile = null;
            imageName.value = "";
            fileInput.value = "";
          }, 1500);
        } else {
          showSaveMessage(data.message || "Error al guardar", "danger");
        }
      })
      .catch(error => {
        showSaveMessage("Error: " + error.message, "danger");
      });
  } else {
    // Para PNG/JPG, usar el redimensionamiento con canvas
    console.log("Uploading as PNG");
    const img = new Image();
    img.onload = () => {
      const tempCanvas = document.createElement("canvas");
      tempCanvas.width = matrixWidth;
      tempCanvas.height = matrixHeight;
      const tempCtx = tempCanvas.getContext("2d");
      
      // Redimensionar imagen
      const imgAspect = img.width / img.height;
      const matrixAspect = matrixWidth / matrixHeight;
      
      let drawWidth, drawHeight, drawX = 0, drawY = 0;
      
      if (imgAspect > matrixAspect) {
        drawHeight = matrixHeight;
        drawWidth = drawHeight * imgAspect;
        drawX = (matrixWidth - drawWidth) / 2;
      } else {
        drawWidth = matrixWidth;
        drawHeight = drawWidth / imgAspect;
        drawY = (matrixHeight - drawHeight) / 2;
      }
      
      tempCtx.drawImage(img, drawX, drawY, drawWidth, drawHeight);
      
      // Convertir a blob y enviar
      tempCanvas.toBlob((blob) => {
        const formData = new FormData();
        formData.append("image", blob, imageName.value + ".png");
        formData.append("name", imageName.value);
        formData.append("is_gif", "false");
        
        fetch("/api/upload", {
          method: "POST",
          body: formData
        })
          .then(r => r.json())
          .then(data => {
            if (data.success) {
              showSaveMessage("Imagen guardada exitosamente", "success");
              setTimeout(() => {
                uploadStep1.style.display = "block";
                uploadStep2.style.display = "none";
                currentImageFile = null;
                imageName.value = "";
                fileInput.value = "";
              }, 1500);
            } else {
              showSaveMessage(data.message || "Error al guardar", "danger");
            }
          })
          .catch(error => {
            showSaveMessage("Error: " + error.message, "danger");
          });
      });
    };
    img.src = originalImage.src;
  }
});

function showSaveMessage(message, type) {
  saveMessage.innerHTML = `
    <div class="alert alert-${type} alert-dismissible fade show" role="alert">
      ${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    </div>
  `;
}

// Menu toggle button
menuToggle.addEventListener("click", toggleSidebar);

// Health check on load
btn.addEventListener("click", checkHealth);
checkHealth();

// ====== CONFIG MANAGEMENT ======

const configForm = document.getElementById("configForm");
const resetBtn = document.getElementById("resetBtn");
const configMessage = document.getElementById("configMessage");

// Load configuration from server
function loadConfig() {
  fetch("/api/config/")
    .then(r => r.json())
    .then(data => {
      if (data.success && data.data) {
        const config = data.data;
        
        // Verificar estructura y asignar valores
        if (config.matrix) {
          document.getElementById("matrixWidth").value = config.matrix.width || 20;
          document.getElementById("matrixHeight").value = config.matrix.height || 20;
        }
        
        if (config.wled) {
          document.getElementById("wledProtocol").value = config.wled.protocol || "http";
          document.getElementById("wledIp").value = config.wled.ip || "192.168.1.100";
          document.getElementById("wledPort").value = config.wled.port || 80;
          document.getElementById("wledRotation").value = config.wled.rotation || "0";
          document.getElementById("wledMirrorV").checked = config.wled.mirror_v || false;
          document.getElementById("wledMirrorH").checked = config.wled.mirror_h || false;
        }
        
        if (config.animation) {
          const delayValue = config.animation.frame_delay || 100;
          document.getElementById("animationDelay").value = delayValue;
          document.getElementById("delayValue").textContent = delayValue + "ms";
          document.getElementById("animationLoop").checked = config.animation.loop || false;
        }
      } else {
        showConfigMessage("Estructura de configuración inválida", "warning");
      }
    })
    .catch(error => {
      showConfigMessage("Error al cargar configuración: " + error.message, "danger");
    });
}

// Actualizar display del delay cuando se mueve el slider
document.getElementById("animationDelay").addEventListener("input", (e) => {
  document.getElementById("delayValue").textContent = e.target.value + "ms";
});

// Save configuration
configForm.addEventListener("submit", (e) => {
  e.preventDefault();
  
  const formData = {
    matrix_width: parseInt(document.getElementById("matrixWidth").value),
    matrix_height: parseInt(document.getElementById("matrixHeight").value),
    wled_protocol: document.getElementById("wledProtocol").value,
    wled_ip: document.getElementById("wledIp").value,
    wled_port: parseInt(document.getElementById("wledPort").value),
    wled_rotation: parseInt(document.getElementById("wledRotation").value),
    wled_mirror_v: document.getElementById("wledMirrorV").checked,
    wled_mirror_h: document.getElementById("wledMirrorH").checked,
    animation_loop: document.getElementById("animationLoop").checked,
    animation_frame_delay: parseInt(document.getElementById("animationDelay").value)
  };
  
  fetch("/api/config/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(formData)
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        showConfigMessage("Configuración guardada exitosamente", "success");
      } else {
        showConfigMessage(data.message || "Error al guardar", "danger");
      }
    })
    .catch(error => {
      showConfigMessage("Error: " + error.message, "danger");
    });
});

// Reset form (reload config)
resetBtn.addEventListener("click", loadConfig);

function showConfigMessage(message, type) {
  configMessage.innerHTML = `
    <div class="alert alert-${type} alert-dismissible fade show" role="alert">
      ${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    </div>
  `;
}

// Cargar imágenes cuando se abre la sección
document.querySelectorAll('a[data-section="playlists"]').forEach(link => {
  link.addEventListener("click", loadImages);
});

function loadImages() {
  fetch("/api/upload/images")
    .then(r => r.json())
    .then(data => {
      const imagesList = document.getElementById("imagesList");
      
      if (!data.success || data.data.length === 0) {
        imagesList.innerHTML = `
          <div class="col-12 text-center text-muted">
            <p>No hay imágenes cargadas</p>
          </div>
        `;
        return;
      }
      
      // Para cada imagen, obtener info de frames
      Promise.all(data.data.map(img => 
        fetch(`/api/upload/${img.id}/frames`)
          .then(r => r.json())
          .then(frames => ({...img, frames_info: frames}))
          .catch(() => ({...img, frames_info: {is_animated: false}}))
      )).then(imagesWithFrames => {
        imagesList.innerHTML = imagesWithFrames.map(img => {
          const isAnimated = img.frames_info?.is_animated || false;
          const frames = img.frames_info?.frames || [];
          
          let animationControls = '';
          if (isAnimated && frames.length > 1) {
            animationControls = `
              <div class="mt-2 pt-2 border-top">
                <small class="text-muted d-block mb-2">
                  <i class="bi bi-film me-1"></i>Animación: ${frames.length} frames
                </small>
                <div class="btn-group btn-group-sm w-100" role="group">
                  <button class="btn btn-outline-primary btn-sm flex-grow-1" onclick="animateImage('${img.id}', 'play')">
                    <i class="bi bi-play-fill me-1"></i>Play
                  </button>
                  <button class="btn btn-outline-warning btn-sm flex-grow-1" onclick="animateImage('${img.id}', 'pause')">
                    <i class="bi bi-pause-fill me-1"></i>Pausa
                  </button>
                  <button class="btn btn-outline-danger btn-sm flex-grow-1" onclick="animateImage('${img.id}', 'stop')">
                    <i class="bi bi-stop-fill me-1"></i>Stop
                  </button>
                </div>
              </div>
            `;
          }
          
          return `
            <div class="col-md-6 col-lg-4 mb-4">
              <div class="card h-100 shadow-sm">
                <div class="card-body p-0">
                  <img src="/api/upload/preview/${img.id}" alt="${img.name}" class="card-img-top" style="max-height: 200px; object-fit: contain; background-color: #f0f0f0;">
                </div>
                <div class="card-footer bg-light">
                  <h6 class="mb-2">${img.name}</h6>
                  <small class="text-muted d-block mb-2">${new Date(img.uploaded_at).toLocaleString()}</small>
                  <div class="btn-group btn-group-sm w-100" role="group">
                    <button class="btn btn-outline-success btn-sm flex-grow-1" onclick="sendToWled('${img.id}', '${img.name}')">
                      <i class="bi bi-lightning-charge me-1"></i>WLED
                    </button>
                    <button class="btn btn-outline-info btn-sm flex-grow-1" onclick="downloadImage('${img.filename}', '${img.name}')">
                      <i class="bi bi-download me-1"></i>Descargar
                    </button>
                    <button class="btn btn-outline-danger btn-sm flex-grow-1" onclick="deleteImage('${img.id}')">
                      <i class="bi bi-trash me-1"></i>Eliminar
                    </button>
                  </div>
                  ${animationControls}
                </div>
              </div>
            </div>
          `;
        }).join("");
      });
    })
    .catch(error => console.error("Error loading images:", error));
}

function downloadImage(filename, name) {
  const link = document.createElement("a");
  link.href = `/api/upload/download/${filename}`;
  link.download = name;
  link.click();
}

function deleteImage(imageId) {
  if (confirm("¿Estás seguro de que deseas eliminar esta imagen?")) {
    fetch(`/api/upload/${imageId}`, {
      method: "DELETE"
    })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          loadImages();
        } else {
          alert("Error al eliminar la imagen");
        }
      })
      .catch(error => console.error("Error deleting image:", error));
  }
}

function sendToWled(imageId, imageName) {
  const button = event.target.closest('button');
  const originalText = button.innerHTML;
  button.disabled = true;
  button.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Enviando...';
  
  fetch(`/api/upload/send-to-wled/${imageId}`, {
    method: "POST"
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        button.innerHTML = '<i class="bi bi-check-circle me-1"></i>¡Enviado!';
        button.classList.remove('btn-outline-success');
        button.classList.add('btn-success');
        setTimeout(() => {
          button.disabled = false;
          button.innerHTML = originalText;
          button.classList.remove('btn-success');
          button.classList.add('btn-outline-success');
        }, 3000);
      } else {
        alert("Error: " + (data.message || "No se pudo enviar a WLED"));
        button.disabled = false;
        button.innerHTML = originalText;
      }
    })
    .catch(error => {
      alert("Error: " + error.message);
      button.disabled = false;
      button.innerHTML = originalText;
    });
}
function animateImage(imageId, action) {
  const button = event.target.closest('button');
  const originalText = button.innerHTML;
  button.disabled = true;
  
  let statusText = action === 'play' ? 'Reproduciendo...' : (action === 'pause' ? 'Pausando...' : 'Deteniendo...');
  button.innerHTML = `<i class="bi bi-hourglass-split me-1"></i>${statusText}`;
  
  fetch(`/api/upload/${imageId}/animate`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({action: action})
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        button.innerHTML = originalText;
        button.classList.add('active');
        setTimeout(() => {
          button.disabled = false;
          button.classList.remove('active');
        }, 500);
      } else {
        alert("Error: " + (data.message || "No se pudo " + action + " animación"));
        button.disabled = false;
        button.innerHTML = originalText;
      }
    })
    .catch(error => {
      alert("Error: " + error.message);
      button.disabled = false;
      button.innerHTML = originalText;
    });
}