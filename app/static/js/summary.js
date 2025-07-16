// State management
        let currentInputMode = 'text';
        let uploadedFile = null;

        // DOM elements
        const textInputBtn = document.getElementById('textInputBtn');
        const fileInputBtn = document.getElementById('fileInputBtn');
        const textInputArea = document.getElementById('textInputArea');
        const fileInputArea = document.getElementById('fileInputArea');
        const noteInput = document.getElementById('noteInput');
        const fileUpload = document.getElementById('fileUpload');
        const fileInfo = document.getElementById('fileInfo');
        const fileName = document.getElementById('fileName');
        const fileSize = document.getElementById('fileSize');
        const removeFile = document.getElementById('removeFile');
        const summarizeBtn = document.getElementById('summarizeBtn');
        const clearBtn = document.getElementById('clearBtn');
        const loadingSpinner = document.getElementById('loadingSpinner');
        const summaryOutput = document.getElementById('summaryOutput');
        const charCount = document.getElementById('charCount');
        const darkModeToggle = document.getElementById('darkModeToggle');

        // Dark mode functionality
        function initDarkMode() {
            const isDark = localStorage.getItem('darkMode') === 'true' || 
                          (!localStorage.getItem('darkMode') && window.matchMedia('(prefers-color-scheme: dark)').matches);
            document.documentElement.classList.toggle('dark', isDark);
        }

        darkModeToggle.addEventListener('click', () => {
            document.documentElement.classList.toggle('dark');
            localStorage.setItem('darkMode', document.documentElement.classList.contains('dark'));
        });

        // Input mode toggle
        function switchInputMode(mode) {
            currentInputMode = mode;
            
            if (mode === 'text') {
                textInputBtn.className = 'px-6 py-3 rounded-lg font-medium transition-all duration-200 bg-indigo-600 text-white shadow-md';
                fileInputBtn.className = 'px-6 py-3 rounded-lg font-medium transition-all duration-200 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600';
                textInputArea.classList.remove('hidden');
                fileInputArea.classList.add('hidden');
            } else {
                fileInputBtn.className = 'px-6 py-3 rounded-lg font-medium transition-all duration-200 bg-indigo-600 text-white shadow-md';
                textInputBtn.className = 'px-6 py-3 rounded-lg font-medium transition-all duration-200 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600';
                fileInputArea.classList.remove('hidden');
                textInputArea.classList.add('hidden');
            }
        }

        // Character count
        function updateCharCount() {
            charCount.textContent = noteInput.value.length;
        }

        // File upload handling
        function handleFileUpload(file) {
            uploadedFile = file;
            fileName.textContent = file.name;
            fileSize.textContent = formatFileSize(file.size);
            fileInfo.classList.remove('hidden');
        }

        function formatFileSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        // Clear functionality
        function clearAll() {
            noteInput.value = '';
            uploadedFile = null;
            fileInfo.classList.add('hidden');
            fileUpload.value = '';
            updateCharCount();
            summaryOutput.innerHTML = `
                <div class="text-center text-slate-500 dark:text-slate-400">
                    <svg class="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
                    </svg>
                    <p class="text-sm">Your AI-generated summary will appear here</p>
                </div>
            `;
        }

        // Summarize functionality
        function summarize() {
            if (currentInputMode === 'text' && !noteInput.value.trim()) {
                alert('Please enter some text to summarize.');
                return;
            }
            
            if (currentInputMode === 'file' && !uploadedFile) {
                alert('Please upload a file to summarize.');
                return;
            }

            // Show loading state
            loadingSpinner.classList.remove('hidden');
            summarizeBtn.disabled = true;

            // Simulate AI processing
            setTimeout(() => {
                let content = currentInputMode === 'text' ? noteInput.value : `Content from ${uploadedFile.name}`;
                
                // Mock summary generation
                const summary = generateMockSummary(content);
                
                summaryOutput.innerHTML = `
                    <div class="prose dark:prose-invert max-w-none">
                        <div class="space-y-4">
                            <div class="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700">
                                <h4 class="font-semibold text-indigo-600 dark:text-indigo-400 mb-2">📋 Key Points</h4>
                                <ul class="space-y-1 text-sm">
                                    ${summary.keyPoints.map(point => `<li class="flex items-start"><span class="text-indigo-500 mr-2">•</span>${point}</li>`).join('')}
                                </ul>
                            </div>
                            <div class="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700">
                                <h4 class="font-semibold text-green-600 dark:text-green-400 mb-2">💡 Summary</h4>
                                <p class="text-sm leading-relaxed">${summary.summary}</p>
                            </div>
                        </div>
                    </div>
                `;
                
                loadingSpinner.classList.add('hidden');
                summarizeBtn.disabled = false;
            }, 2000);
        }

        // Mock summary generator
        function generateMockSummary(content) {
            return {
                keyPoints: [
                    "Main topic identified and analyzed",
                    "Key arguments and supporting evidence extracted",
                    "Important conclusions highlighted",
                    "Actionable insights provided"
                ],
                summary: "This content covers several important points related to the main topic. The analysis reveals key themes and provides valuable insights that can be used for further reference. The summary maintains the essential information while presenting it in a more digestible format."
            };
        }

        // Event listeners
        textInputBtn.addEventListener('click', () => switchInputMode('text'));
        fileInputBtn.addEventListener('click', () => switchInputMode('file'));
        noteInput.addEventListener('input', updateCharCount);
        fileUpload.addEventListener('change', (e) => {
            if (e.target.files[0]) {
                handleFileUpload(e.target.files[0]);
            }
        });
        removeFile.addEventListener('click', () => {
            uploadedFile = null;
            fileInfo.classList.add('hidden');
            fileUpload.value = '';
        });
        summarizeBtn.addEventListener('click', summarize);
        clearBtn.addEventListener('click', clearAll);

        // Initialize
        initDarkMode();
        updateCharCount();