// paper upload and analysis js code
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const fileInfo = document.getElementById('fileInfo');
const fileName = document.getElementById('fileName');
const fileSize = document.getElementById('fileSize');
const removeFile = document.getElementById('removeFile');
const analyzeBtn = document.getElementById('analyzeBtn');
const analyzeText = document.getElementById('analyzeText');
const analyzeIcon = document.getElementById('analyzeIcon');
const progressSection = document.getElementById('progressSection');
const progressText = document.getElementById('progressText');
const uploadForm = document.getElementById('uploadForm');

let selectedFiles = [];

// Drag events
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('ring-2', 'ring-indigo-400');
});

dropZone.addEventListener('dragleave', (e) => {
    e.preventDefault();
    dropZone.classList.remove('ring-2', 'ring-indigo-400');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('ring-2', 'ring-indigo-400');
    const files = e.dataTransfer.files;
    if (files.length > 0) handleFileSelect(files);
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) handleFileSelect(e.target.files);
});

function handleFileSelect(files) {
    const allowedTypes = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png'];
    selectedFiles = [];

    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        if (!allowedTypes.includes(file.type)) {
            alert('Only PDF, JPG, JPEG, PNG files are allowed.');
            return;
        }
        if (file.size > 10 * 1024 * 1024) {
            alert('File size must be below 10MB.');
            return;
        }
        selectedFiles.push(file);
    }

    // Update UI with file names and sizes (show count if multiple)
    if (selectedFiles.length === 1) {
        fileName.textContent = selectedFiles[0].name;
        fileSize.textContent = `${(selectedFiles[0].size / 1024 / 1024).toFixed(2)} MB`;
    } else {
        fileName.textContent = `${selectedFiles.length} files selected`;
        fileSize.textContent = '';
    }

    fileInfo.classList.remove('hidden');
    analyzeBtn.disabled = false;
    analyzeBtn.classList.remove('opacity-50', 'cursor-not-allowed');
}

removeFile.addEventListener('click', () => {
    selectedFiles = [];
    fileInput.value = '';
    fileInfo.classList.add('hidden');
    analyzeBtn.disabled = true;
    analyzeBtn.classList.add('opacity-50', 'cursor-not-allowed');
});

uploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (selectedFiles.length === 0) {
        alert('Please select at least one file.');
        return;
    }

    // Start analysis visual
    progressSection.classList.remove('hidden');
    analyzeBtn.disabled = true;
    analyzeText.textContent = 'Analyzing...';
    analyzeIcon.innerHTML = '<div class="animate-spin rounded-full h-5 w-5 border-b-2 border-white" role="status" aria-label="Loading"></div>';
    progressText.textContent = 'Processing OCR and extracting text...';

    const formData = new FormData();

    // Append all selected files
    selectedFiles.forEach(file => {
        formData.append('paper_files', file);
    });

    // Append selected checkboxes
    ['extract_questions', 'difficulty_analysis', 'topic_classification', 'answer_suggestions'].forEach(id => {
        const checkbox = uploadForm.querySelector(`input[name="${id}"]`);
        if (checkbox && checkbox.checked) formData.append(id, 'on');
    });

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        // Simulate progress steps (you can replace this with polling later)
        const steps = [
            'Analyzing question patterns...',
            'Classifying topics and difficulty...',
            'Generating insights and suggestions...'
        ];

        for (let i = 0; i < steps.length; i++) {
            await new Promise(res => setTimeout(res, 1500));
            progressText.textContent = steps[i];
        }

        progressText.textContent = data.message || 'Analysis complete!';
        setTimeout(() => {
            window.location.href = data.redirect_url || '/results';
        }, 1000);

    } catch (err) {
        progressText.textContent = 'Something went wrong. Please try again.';
        console.error('Upload error:', err);
    }
});

document.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && e.target === dropZone) {
        fileInput.click();
    }
});
