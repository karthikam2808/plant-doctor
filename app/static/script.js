// Global logout button handler for all pages
document.addEventListener('DOMContentLoaded', function() {
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.onclick = function() {
            document.cookie = 'logged_in=; Max-Age=0; path=/;';
            window.location.href = '/login';
        };
    }
});
const uploadInput = document.getElementById('upload');
const preview = document.getElementById('preview');
const resultBox = document.getElementById('result');
const predictBtn = document.getElementById('predict-btn');
const downloadBtn = document.getElementById('download-btn');
const dropZone = document.getElementById('drop-zone');
const dropZoneText = document.getElementById('drop-zone-text');

let selectedFile = null;
let lastPrediction = "";

if (dropZone && uploadInput) {
    // Click drop zone opens file dialog
    dropZone.addEventListener('click', () => {
        uploadInput.click();
    });

    // Drag over styling
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = '#388e3c';
    });
    dropZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = '#43cea2';
    });
    // Drop file
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = '#43cea2';
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            uploadInput.files = e.dataTransfer.files;
            const event = new Event('change');
            uploadInput.dispatchEvent(event);
        }
    });
}

uploadInput.addEventListener('change', (e) => {
    selectedFile = e.target.files[0];

    if (selectedFile) {
        const reader = new FileReader();
        reader.onload = () => {
            preview.src = reader.result;
            preview.style.display = 'block';
        };
        reader.readAsDataURL(selectedFile);

        resultBox.innerHTML = '';
        predictBtn.disabled = false;
        downloadBtn.disabled = true;
        if (dropZoneText) dropZoneText.textContent = 'Image selected!';
    }
});

predictBtn.addEventListener('click', async () => {
    if (!selectedFile) return;

    const formData = new FormData();
    formData.append('file', selectedFile);

    predictBtn.disabled = true;
    resultBox.innerHTML = "🔍 Predicting...";

    try {
        const res = await fetch("/predict", {
            method: "POST",
            body: formData
        });

        if (!res.ok) {
            const errorData = await res.json();
            resultBox.innerHTML = "❌ Prediction failed: " + errorData.error;
            predictBtn.disabled = false;
            return;
        }

        const data = await res.json();
        // Add delay before showing result
        resultBox.innerHTML = "⏳ Processing...";
        setTimeout(() => {
            resultBox.innerHTML = `✅ <b>Predicted:</b> ${data.prediction} (${data.confidence}%)`;
            resultBox.style.color = '#111';
            lastPrediction = data.prediction;
            downloadBtn.disabled = false;
        }, 2500); // 2.5 seconds delay

    } catch (err) {
        console.error("❌ Error:", err);
        resultBox.innerHTML = "⚠️ Could not connect to server.";
    }

    predictBtn.disabled = false;
});

downloadBtn.addEventListener('click', async () => {
    if (!selectedFile || !lastPrediction) return;

    const formData = new FormData();
    formData.append('image', selectedFile);
    formData.append('prediction', lastPrediction);

    const res = await fetch("/generate_report", {
        method: "POST",
        body: formData
    });

    if (!res.ok) {
        alert("❌ Report generation failed.");
        return;
    }

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = "plant_report.pdf";
    a.click();
    window.URL.revokeObjectURL(url);
});
