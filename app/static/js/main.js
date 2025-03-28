// Global JavaScript functionality
document.addEventListener('DOMContentLoaded', function() {
    // Auto-hide flash messages after 5 seconds
    const flashMessages = document.querySelectorAll('.message');
    if (flashMessages.length > 0) {
        setTimeout(() => {
            flashMessages.forEach(message => {
                message.style.opacity = '0';
                setTimeout(() => {
                    message.style.display = 'none';
                }, 300);
            });
        }, 5000);
    }
    
    // Initialize upload CSV button
    const uploadCsvBtn = document.getElementById('upload-csv');
    if (uploadCsvBtn) {
        uploadCsvBtn.addEventListener('click', function() {
            alert('Upload CSV functionality will be implemented here');
        });
    }
}); 