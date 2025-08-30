
function updateStep(currentStep) {
    const totalSteps = 3;

    for (let i = 1; i <= totalSteps; i++) {
        const step = document.getElementById(`step${i}`);
        const circle = step.querySelector('.step-circle');
        const title = step.querySelector('.step-title');
        const desc = step.querySelector('.step-desc');

        // Reset base classes
        step.className = 'flex items-center space-x-2.5 rtl:space-x-reverse';
        circle.className = 'step-circle flex items-center justify-center w-8 h-8 border rounded-full shrink-0';
        title.className = 'step-title font-medium leading-tight';
        desc.className = 'step-desc text-sm';

        if (i < currentStep) {
            // Completed
            step.classList.add('text-blue-500');
            circle.classList.add('border-blue-500', 'bg-blue-100', 'text-blue-600');
            circle.textContent = '✓';
            title.classList.add('text-blue-400');
            desc.classList.add('text-blue-300');
        } else if (i === currentStep) {
            // Current
            step.classList.add('text-white');
            circle.classList.add('border-blue-500', 'text-white');
            circle.textContent = `${i}`;
            title.classList.add('text-white');
            desc.classList.add('text-slate-300');
        } else {
            // Upcoming
            step.classList.add('text-gray-400');
            circle.classList.add('border-gray-500', 'text-gray-400');
            circle.textContent = `${i}`;
            title.classList.add('text-gray-300');
            desc.classList.add('text-gray-400');
        }
    }
}


// File handling
const fileInput = document.getElementById('fileInput');
const dropZone = document.getElementById('dropZone');
const extractBtn = document.getElementById('extractBtn');
const uploadContent = document.getElementById('uploadContent');
const fileInfo = document.getElementById('fileInfo');
const fileName = document.getElementById('fileName');

// Drag and drop functionality
dropZone.addEventListener('click', () => fileInput.click());
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});
dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});
dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        fileInput.files = files;
        handleFileSelect();
    }
});

fileInput.addEventListener('change', handleFileSelect);

function handleFileSelect() {
    const file = fileInput.files[0];
    if (file) {
        uploadContent.classList.add('hidden');
        fileInfo.classList.remove('hidden');
        fileName.textContent = file.name;
        extractBtn.disabled = false;
        updateStep(2);
    }
}

// Extract text functionality
extractBtn.addEventListener('click', () => {
    const spinner = document.getElementById('extractSpinner');
    const text = document.getElementById('extractText');

    spinner.style.display = 'block';
    text.textContent = 'Extracting...';
    extractBtn.disabled = true;

    // Simulate extraction process
    // Real extraction process
    const file = fileInput.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    fetch('/extract_text', {
        method: 'POST',
        body: formData
    })
        .then(response => response.json())
        .then(data => {
            if (data.text) {
                document.getElementById('ocrText').textContent = data.text;
                document.getElementById('ocrSection').style.display = 'block';
                updateStep(3);
                document.getElementById('ocrSection').scrollIntoView({ behavior: 'smooth' });
            } else if (data.error) {
                document.getElementById('ocrText').textContent = 'Error: ' + data.error;
                document.getElementById('ocrSection').style.display = 'block';
            }
        })
        .catch(err => {
            document.getElementById('ocrText').textContent = 'Error: ' + err.message;
            document.getElementById('ocrSection').style.display = 'block';
        })
        .finally(() => {
            spinner.style.display = 'none';
            text.textContent = 'Extract Text';
            extractBtn.disabled = false;
        });

});

// Predict topics functionality
document.getElementById('predictBtn').addEventListener('click', () => {
    const spinner = document.getElementById('predictSpinner');
    const textEl = document.getElementById('predictText');
    const ocrText = document.getElementById('ocrText').textContent;

    spinner.style.display = 'block';
    textEl.textContent = 'Analyzing...';

    fetch('/predict_topics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: ocrText })
    })
    .then(res => res.json())
    .then(data => {
        const container = document.getElementById('topicsContainer');
        container.innerHTML = '';
        if (data.topics) {
            data.topics.forEach(topic => {
                const tag = document.createElement('span');
                tag.className = 'topic-tag px-4 py-2 rounded-full text-white font-medium text-sm';
                tag.textContent = topic;
                container.appendChild(tag);
            });
            document.getElementById('topicsSection').style.display = 'block';
            updateStep(4);
            setTimeout(() => {
                document.getElementById('topicsSection').scrollIntoView({ behavior: 'smooth' });
            }, 200);
        } else if (data.error) {
            container.textContent = 'Error: ' + data.error;
        }
    })
    .catch(err => {
        document.getElementById('topicsContainer').textContent = 'Error: ' + err.message;
    })
    .finally(() => {
        spinner.style.display = 'none';
        textEl.textContent = '🔮 Predict Topics';
    });
});
