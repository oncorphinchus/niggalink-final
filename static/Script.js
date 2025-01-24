// Utility function to sanitize HTML and prevent XSS attacks
function escapeHtml(str) {
    if (!str) return ''; // Return empty string if input is null or undefined
    return str.replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// Create a loader element
const loader = document.createElement('div');
loader.className = 'loader';
document.body.appendChild(loader);

const FETCH_TIMEOUT = 30000; // 30 seconds

async function fetchWithTimeout(resource, options = {}) {
    const timeout = options.timeout || 30000;
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeout);

    return fetch(resource, {
        ...options,
        signal: controller.signal
    }).finally(() => clearTimeout(id));
}

async function downloadVideo() {
    const videoUrl = document.getElementById('videoUrl').value.trim();
    const statusDiv = document.getElementById('status');
    const downloadLinkDiv = document.getElementById('downloadLink');
    const progressContainer = document.querySelector('.progress-container');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    const progressStatus = document.getElementById('progressStatus');

    if (!videoUrl) {
        showError('Please enter a valid URL');
        return;
    }

    try {
        // Reset and show progress elements
        resetUI();
        progressContainer.style.display = 'block';
        
        // Start progress simulation
        startProgressSimulation(progressFill, progressText, progressStatus);

        const response = await fetchWithTimeout('/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url: videoUrl })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to download video');
        }

        // Complete the progress bar
        completeProgress(progressFill, progressText);
        
        // Show success message
        showSuccess('Video processed successfully!');

        // Create download button
        createDownloadButton(data.download_url, data.title);

    } catch (error) {
        showError(error.message);
    }
}

function resetUI() {
    const statusDiv = document.getElementById('status');
    const downloadLinkDiv = document.getElementById('downloadLink');
    const progressContainer = document.querySelector('.progress-container');
    
    statusDiv.innerHTML = '';
    statusDiv.className = 'status';
    downloadLinkDiv.innerHTML = '';
    document.getElementById('progressFill').style.width = '0%';
    document.getElementById('progressText').textContent = '0%';
    document.getElementById('progressStatus').textContent = 'Initializing download...';
}

function startProgressSimulation(progressFill, progressText, progressStatus) {
    let progress = 0;
    const statuses = [
        { percent: 0, text: 'Initializing download...' },
        { percent: 20, text: 'Fetching video information...' },
        { percent: 40, text: 'Processing video...' },
        { percent: 60, text: 'Optimizing format...' },
        { percent: 80, text: 'Preparing download...' }
    ];

    const interval = setInterval(() => {
        if (progress >= 90) {
            clearInterval(interval);
            return;
        }

        progress += 1;
        progressFill.style.width = `${progress}%`;
        progressText.textContent = `${progress}%`;

        // Update status text based on progress
        for (let status of statuses) {
            if (progress === status.percent) {
                progressStatus.textContent = status.text;
            }
        }
    }, 100);

    return interval;
}

function completeProgress(progressFill, progressText) {
    progressFill.style.width = '100%';
    progressText.textContent = '100%';
}

function showError(message) {
    const statusDiv = document.getElementById('status');
    statusDiv.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${message}`;
    statusDiv.className = 'status error';
}

function showSuccess(message) {
    const statusDiv = document.getElementById('status');
    statusDiv.innerHTML = `<i class="fas fa-check-circle"></i> ${message}`;
    statusDiv.className = 'status success';
}

function createDownloadButton(url, title) {
    const downloadLinkDiv = document.getElementById('downloadLink');
    downloadLinkDiv.innerHTML = `
        <a href="${url}" class="download-button" target="_blank">
            <i class="fas fa-download"></i> Download ${title}
        </a>
        <p class="expiration-warning">
            <i class="fas fa-clock"></i> This download link will expire in 1 hour
        </p>
    `;
}

// Add enter key support
document.getElementById('videoUrl').addEventListener('keypress', function(event) {
    if (event.key === 'Enter') {
        downloadVideo();
    }
});