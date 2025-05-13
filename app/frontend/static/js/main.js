// Main JavaScript for Document Manager Frontend

document.addEventListener('DOMContentLoaded', function() {
    // Check if the user has an auth token
    const authToken = localStorage.getItem('auth_token');
    const currentPath = window.location.pathname;
    
    // Show the current user's username in the navbar if logged in
    updateNavbar();
    
    // Handle URL parameters (for triggering analysis modal)
    const urlParams = new URLSearchParams(window.location.search);
    const analyzeDocId = urlParams.get('analyze');
    
    if (analyzeDocId && document.getElementById('documents-table-body')) {
        // We're on the documents page and should show the analysis modal
        setTimeout(() => {
            analyzeDocument(analyzeDocId);
        }, 500);
    }
    
    // Handle logout link
    const logoutLink = document.querySelector('a[href*="logout"]');
    if (logoutLink) {
        logoutLink.addEventListener('click', function(e) {
            e.preventDefault();
            logout();
        });
    }
    
    // Initialize Bootstrap components
    initializeBootstrapComponents();
});

/**
 * Update navbar based on authentication status
 */
function updateNavbar() {
    const authToken = localStorage.getItem('auth_token');
    const authenticated = !!authToken;
    
    // Update navbar items visibility based on authentication
    document.querySelectorAll('.nav-item').forEach(item => {
        const requiresAuth = !item.querySelector('a[href*="login"]') && 
                             !item.querySelector('a[href*="register"]') &&
                             !item.querySelector('a[href="/"]');
        
        if (requiresAuth && !authenticated) {
            item.style.display = 'none';
        } else if (item.querySelector('a[href*="login"]') || item.querySelector('a[href*="register"]')) {
            item.style.display = authenticated ? 'none' : 'block';
        }
    });
    
    // Try to get username and admin status from token
    if (authenticated) {
        try {
            const tokenParts = authToken.split('.');
            if (tokenParts.length === 3) {
                const payload = JSON.parse(atob(tokenParts[1]));
                
                // Update username if available
                if (payload.username) {
                    // Find the username display element and update it
                    const usernameElement = document.querySelector('.navbar .nav-link:not([href])');
                    if (usernameElement) {
                        usernameElement.textContent = payload.username;
                    }
                }
                
                // Show/hide admin link based on admin status
                const adminItem = document.querySelector('.nav-item a[href="/admin"]')?.parentElement;
                if (adminItem) {
                    adminItem.style.display = payload.is_admin ? 'block' : 'none';
                }
            }
        } catch (e) {
            console.error('Error parsing token:', e);
        }
    }
}

/**
 * Logout the user
 */
function logout() {
    localStorage.removeItem('auth_token');
    window.location.href = '/';
}

/**
 * Initialize Bootstrap components
 */
function initializeBootstrapComponents() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}

/**
 * Format file size in a human-readable format
 * @param {number} bytes - The file size in bytes
 * @returns {string} - Formatted file size
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Format a date in a readable format
 * @param {string} dateString - ISO date string
 * @returns {string} - Formatted date
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
}

/**
 * Download a string as a file
 * @param {string} content - The content to download
 * @param {string} fileName - The name of the file
 * @param {string} contentType - The content type (default: text/plain)
 */
function downloadStringAsFile(content, fileName, contentType = 'text/plain') {
    const blob = new Blob([content], { type: contentType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    a.click();
    URL.revokeObjectURL(url);
}

/**
 * Copy text to clipboard
 * @param {string} encodedText - URL-encoded text to copy to clipboard
 */
function copyToClipboard(encodedText) {
    const text = decodeURIComponent(encodedText);
    navigator.clipboard.writeText(text)
        .then(() => {
            // Show a temporary success message
            const button = document.querySelector('[onclick*="copyToClipboard"]');
            const originalText = button.innerHTML;
            button.innerHTML = '<i class="bi bi-check"></i> Copied!';
            button.classList.add('btn-success');
            button.classList.remove('btn-outline-primary');
            
            setTimeout(() => {
                button.innerHTML = originalText;
                button.classList.remove('btn-success');
                button.classList.add('btn-outline-primary');
            }, 2000);
        })
        .catch(err => {
            console.error('Failed to copy text: ', err);
            alert('Failed to copy to clipboard. Please try again.');
        });
}

/**
 * Check if the auth token is valid and not expired
 * @returns {boolean} - Whether the token is valid
 */
function isValidToken() {
    const token = localStorage.getItem('auth_token');
    if (!token) return false;
    
    try {
        const tokenParts = token.split('.');
        if (tokenParts.length !== 3) return false;
        
        const payload = JSON.parse(atob(tokenParts[1]));
        const expirationTime = payload.exp * 1000; // Convert to milliseconds
        
        return Date.now() < expirationTime;
    } catch (e) {
        console.error('Error validating token:', e);
        return false;
    }
}

/**
 * Check if current user is an admin
 * @returns {boolean} - Whether the current user is an admin
 */
function isAdmin() {
    const token = localStorage.getItem('auth_token');
    if (!token) return false;
    
    try {
        const tokenParts = token.split('.');
        if (tokenParts.length !== 3) return false;
        
        const payload = JSON.parse(atob(tokenParts[1]));
        return !!payload.is_admin;
    } catch (e) {
        console.error('Error checking admin status:', e);
        return false;
    }
}

/**
 * Handle API responses and check for authentication errors
 * @param {Response} response - Fetch API response
 * @returns {Promise} - Promise resolving to response JSON or throwing an error
 */
async function handleApiResponse(response) {
    if (response.status === 401) {
        // Token expired or invalid
        localStorage.removeItem('auth_token');
        window.location.href = '/login';
        throw new Error('Authentication required');
    }
    
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `API error: ${response.status}`);
    }
    
    return response.json();
}