/**
 * app.js - Main application logic for VisionID
 */

document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const authenticateBtn = document.getElementById('authenticate-button');
    const loadingIndicator = document.getElementById('loading-indicator');
    const resultContainer = document.getElementById('result-container');
    const successCard = document.getElementById('success-card');
    const failureCard = document.getElementById('failure-card');
    const failureMessage = document.getElementById('failure-message');
    const resetSuccessBtn = document.getElementById('reset-success');
    const resetFailureBtn = document.getElementById('reset-failure');
    
    // Username field (required)
    const usernameField = document.getElementById('username-field');
    const usernameError = document.getElementById('username-error');
    const usernameErrorMessage = document.getElementById('username-error-message');
    
    // Event Listeners
    authenticateBtn.addEventListener('click', authenticateUser);
    resetSuccessBtn.addEventListener('click', resetApplication);
    resetFailureBtn.addEventListener('click', resetApplication);
    
    // Check username availability when starting the camera
    document.getElementById('start-camera').addEventListener('click', validateUsername);
    
    // Webcam event listeners
    document.addEventListener('webcam:captured', function(event) {
        // Image captured, show authenticate button
        authenticateBtn.classList.remove('d-none');
    });
    
    document.addEventListener('webcam:retake', function() {
        // Image retaking, hide authenticate button
        authenticateBtn.classList.add('d-none');
    });
    
    /**
     * Authenticates user by sending the captured image to the backend
     */
    async function authenticateUser() {
        try {
            // Get captured image
            const imageBase64 = window.webcamHandler.getImageBase64();
            
            if (!imageBase64) {
                showError('No image captured. Please capture your face image first.');
                return;
            }
            
            // Show loading indicator
            authenticateBtn.classList.add('d-none');
            loadingIndicator.classList.remove('d-none');
            
            // Validate username (required)
            if (!usernameField || usernameField.value.trim() === '') {
                showError('Username is required for authentication. Please enter your username and try again.');
                return;
            }
            
            // Prepare authentication data
            const authData = { 
                image: imageBase64,
                username: usernameField.value.trim()
            };
            
            // Send to backend for authentication
            const response = await fetch('/api/authenticate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(authData),
            });
            
            const data = await response.json();
            
            // Hide loading indicator
            loadingIndicator.classList.add('d-none');
            
            // Display result
            resultContainer.classList.remove('d-none');
            
            if (data.status === 'success') {
                // Show success message
                successCard.classList.remove('d-none');
                failureCard.classList.add('d-none');
                
                // If user_id is returned, redirect to profile after delay
                if (data.user_id) {
                    setTimeout(() => {
                        window.location.href = '/profile';
                    }, 2000);
                }
            } else {
                // Show failure message
                successCard.classList.add('d-none');
                failureCard.classList.remove('d-none');
                failureMessage.textContent = data.message || 'Authentication failed.';
            }
            
        } catch (error) {
            console.error('Authentication error:', error);
            loadingIndicator.classList.add('d-none');
            
            // Show error message
            resultContainer.classList.remove('d-none');
            successCard.classList.add('d-none');
            failureCard.classList.remove('d-none');
            failureMessage.textContent = 'Network or server error. Please try again.';
        }
    }
    
    /**
     * Resets the application to the initial state
     */
    function resetApplication() {
        // Reset webcam
        window.webcamHandler.reset();
        
        // Reset UI
        authenticateBtn.classList.add('d-none');
        loadingIndicator.classList.add('d-none');
        resultContainer.classList.add('d-none');
        successCard.classList.add('d-none');
        failureCard.classList.add('d-none');
        
        // Clear username if field exists
        if (usernameField) {
            usernameField.value = '';
        }
    }
    
    /**
     * Validates the username before starting camera
     */
    function validateUsername(event) {
        if (!usernameField || usernameField.value.trim() === '') {
            // Prevent camera from starting
            event.preventDefault();
            event.stopPropagation();
            
            // Show error
            usernameError.classList.remove('d-none');
            usernameErrorMessage.textContent = 'Please enter your username before proceeding';
            usernameField.focus();
            return false;
        }
        
        // Username provided, hide error if shown
        usernameError.classList.add('d-none');
        return true;
    }

    /**
     * Shows an error message to the user
     */
    function showError(message) {
        resultContainer.classList.remove('d-none');
        successCard.classList.add('d-none');
        failureCard.classList.remove('d-none');
        failureMessage.textContent = message;
    }
});
