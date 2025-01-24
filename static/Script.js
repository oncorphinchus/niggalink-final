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
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), FETCH_TIMEOUT);
    try {
        const response = await fetch(resource, {
            ...options,
            signal: controller.signal
        });
        clearTimeout(id);
        return response;
    } catch (error) {
        clearTimeout(id);
        throw error;
    }
}

async function downloadVideo() {
    const videoUrl = document.getElementById('videoUrl').value.trim();
    const statusDiv = document.getElementById('status');
    const downloadLinkDiv = document.getElementById('downloadLink');
    const loadingSpinner = document.getElementById('loadingSpinner');

    if (!videoUrl) {
        statusDiv.innerHTML = 'Please enter a valid URL';
        statusDiv.className = 'status error';
        return;
    }

    try {
        // Clear previous status and show loading spinner
        statusDiv.innerHTML = 'Initializing download...';
        downloadLinkDiv.innerHTML = '';
        loadingSpinner.style.display = 'flex';

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

        // Hide loading spinner
        loadingSpinner.style.display = 'none';
        statusDiv.innerHTML = 'Video processed successfully!';
        statusDiv.className = 'status success';

        // Create download link
        const downloadLink = document.createElement('a');
        downloadLink.href = data.download_url;
        downloadLink.className = 'download-button';
        downloadLink.target = '_blank';
        downloadLink.textContent = `Download ${data.title}`;
        
        downloadLinkDiv.innerHTML = '';
        downloadLinkDiv.appendChild(downloadLink);

        // Add expiration warning
        const expirationWarning = document.createElement('p');
        expirationWarning.className = 'expiration-warning';
        expirationWarning.textContent = 'Note: This download link will expire in 1 hour';
        downloadLinkDiv.appendChild(expirationWarning);

    } catch (error) {
        loadingSpinner.style.display = 'none';
        statusDiv.innerHTML = error.message || 'An error occurred while processing the video';
        statusDiv.className = 'status error';
        console.error('Download error:', error);
    }
}

// Add enter key support
document.getElementById('videoUrl').addEventListener('keypress', function(event) {
    if (event.key === 'Enter') {
        downloadVideo();
    }
});