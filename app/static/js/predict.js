
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
    setTimeout(() => {
        document.getElementById('ocrText').textContent = 'Sample extracted text from your exam paper would appear here...';
        document.getElementById('ocrSection').style.display = 'block';

        spinner.style.display = 'none';
        text.textContent = 'Extract Text';
        extractBtn.disabled = false;
        updateStep(3);
        // Scroll to OCR section
        document.getElementById('ocrSection').scrollIntoView({ behavior: 'smooth' });
    }, 2000);
});

// Predict topics functionality
document.getElementById('predictBtn').addEventListener('click', () => {
    const spinner = document.getElementById('predictSpinner');
    const text = document.getElementById('predictText');

    spinner.style.display = 'block';
    text.textContent = 'Analyzing...';

    // Simulate prediction process
    setTimeout(() => {
        const topics = ['Machine Learning', 'Data Structures', 'Algorithms', 'Database Systems', 'Software Engineering'];
        const container = document.getElementById('topicsContainer');
        container.innerHTML = '';

        topics.forEach((topic, index) => {
            setTimeout(() => {
                const tag = document.createElement('span');
                tag.className = 'topic-tag px-4 py-2 rounded-full text-white font-medium text-sm';
                tag.textContent = topic;
                container.appendChild(tag);
            }, index * 200);
        });

        document.getElementById('topicsSection').style.display = 'block';
        spinner.style.display = 'none';
        text.textContent = '🔮 Predict Topics';
        updateStep(4);

        // Scroll to topics section
        setTimeout(() => {
            document.getElementById('topicsSection').scrollIntoView({ behavior: 'smooth' });
        }, 1000);
    }, 2000);
});