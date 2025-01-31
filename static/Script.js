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
        
        // Start with initial progress
        updateProgress(10, 'Initializing...', progressFill, progressText, progressStatus);

        const response = await fetchWithTimeout('/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({ url: videoUrl })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to download video');
        }

        // Create download button immediately when we have the URL
        createDownloadButton(data.download_url, data.title);
        addToHistory(data.title);
        
        // Complete the progress immediately after download link is created
        updateProgress(100, 'Download ready!', progressFill, progressText, progressStatus);
        
        // Show success message
        showSuccess('Video processed successfully!');

        // Add to history
        addToHistory(data.title);

    } catch (error) {
        showError(error.message);
        // Reset progress on error
        updateProgress(0, 'Error occurred', progressFill, progressText, progressStatus);
    }
}

function resetUI() {
    const statusDiv = document.getElementById('status');
    const downloadLinkDiv = document.getElementById('downloadLink');
    const progressContainer = document.querySelector('.progress-container');
    
    statusDiv.innerHTML = '';
    statusDiv.className = 'status';
    downloadLinkDiv.innerHTML = '';
    updateProgress(0, 'Initializing...', 
        document.getElementById('progressFill'),
        document.getElementById('progressText'),
        document.getElementById('progressStatus')
    );
}

function updateProgress(percent, status, progressFill, progressText, progressStatus) {
    progressFill.style.width = `${percent}%`;
    progressText.textContent = `${percent}%`;
    progressStatus.textContent = status;
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

document.addEventListener('DOMContentLoaded', () => {
    // Add click handlers for navigation
    document.querySelectorAll('.nav-links a').forEach(link => {
        link.addEventListener('click', (e) => {
            const tabId = e.target.getAttribute('data-tab');
            if (!tabId) return; // Skip if no tab ID (like for logout)
            
            e.preventDefault();
            
            // Remove active class from all links
            document.querySelectorAll('.nav-links a').forEach(l => {
                l.classList.remove('active');
            });
            
            // Add active class to clicked link
            e.target.classList.add('active');
            
            // Hide all tab contents
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Show selected tab content
            document.getElementById(tabId).classList.add('active');
        });
    });

    // Initialize history display
    updateHistoryDisplay();
});

function updateHistoryDisplay() {
    const historyList = document.getElementById('historyList');
    const history = getDownloadHistory();
    
    if (!historyList) return;
    
    if (history.length === 0) {
        historyList.innerHTML = '<p class="no-history">No download history yet</p>';
        return;
    }
    
    historyList.innerHTML = history.map(item => `
        <div class="history-item">
            <div class="history-title">${escapeHtml(item.title)}</div>
            <div class="history-date">${new Date(item.date).toLocaleString()}</div>
        </div>
    `).join('');
}

function getDownloadHistory() {
    try {
        return JSON.parse(localStorage.getItem('downloadHistory') || '[]');
    } catch (e) {
        console.error('Error reading history:', e);
        return [];
    }
}

function addToHistory(title) {
    try {
        const history = getDownloadHistory();
        history.unshift({
            title: title,
            date: new Date().toISOString()
        });
        // Keep only last 10 items
        const trimmedHistory = history.slice(0, 10);
        localStorage.setItem('downloadHistory', JSON.stringify(trimmedHistory));
        updateHistoryDisplay();
    } catch (e) {
        console.error('Error saving to history:', e);
    }
}

function clearHistory() {
    try {
        localStorage.removeItem('downloadHistory');
        updateHistoryDisplay();
    } catch (e) {
        console.error('Error clearing history:', e);
    }
}