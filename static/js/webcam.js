/**
 * webcam.js - Handles webcam functionality for VisionID
 */

class WebcamHandler {
    constructor() {
        // DOM elements
        this.video = document.getElementById('webcam');
        this.canvas = document.getElementById('canvas');
        this.cameraPlaceholder = document.getElementById('camera-placeholder');
        this.faceGuidelines = document.getElementById('face-guidelines');
        this.startCameraBtn = document.getElementById('start-camera');
        this.captureBtn = document.getElementById('capture-button');
        this.retakeBtn = document.getElementById('retake-button');
        
        // Initialize state
        this.stream = null;
        this.isCaptured = false;
        this.capturedImage = null;
        
        // Bind methods
        this.startCamera = this.startCamera.bind(this);
        this.stopCamera = this.stopCamera.bind(this);
        this.captureImage = this.captureImage.bind(this);
        this.retakeImage = this.retakeImage.bind(this);
        this.getImageBase64 = this.getImageBase64.bind(this);
        
        // Initialize
        this.init();
    }
    
    init() {
        // Set up event listeners
        this.startCameraBtn.addEventListener('click', this.startCamera);
        this.captureBtn.addEventListener('click', this.captureImage);
        this.retakeBtn.addEventListener('click', this.retakeImage);
        
        // Handle page unload
        window.addEventListener('beforeunload', this.stopCamera);
    }
    
    async startCamera() {
        try {
            // Request camera access
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    facingMode: 'user'
                },
                audio: false
            });
            
            // Connect stream to video element
            this.video.srcObject = this.stream;
            
            // Update UI
            this.video.classList.remove('d-none');
            this.cameraPlaceholder.classList.add('d-none');
            this.faceGuidelines.classList.remove('d-none');
            this.startCameraBtn.classList.add('d-none');
            this.captureBtn.classList.remove('d-none');
            
            // Set up canvas
            this.canvas.width = this.video.videoWidth || 640;
            this.canvas.height = this.video.videoHeight || 480;
            
            // Custom event
            document.dispatchEvent(new CustomEvent('webcam:started'));
            
        } catch (error) {
            console.error('Error accessing camera:', error);
            alert(`Camera access error: ${error.message}. Please ensure your camera is connected and that you've granted permission.`);
        }
    }
    
    stopCamera() {
        // Stop all tracks in the stream
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        
        // Custom event
        document.dispatchEvent(new CustomEvent('webcam:stopped'));
    }
    
    captureImage() {
        if (!this.stream) return;
        
        const context = this.canvas.getContext('2d');
        
        // Set canvas dimensions to match video
        this.canvas.width = this.video.videoWidth;
        this.canvas.height = this.video.videoHeight;
        
        // Draw current video frame to canvas
        context.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
        
        // Update state and UI
        this.isCaptured = true;
        this.capturedImage = this.canvas.toDataURL('image/jpeg', 0.9);
        
        // Show canvas with captured image
        this.video.classList.add('d-none');
        this.canvas.classList.remove('d-none');
        this.faceGuidelines.classList.add('d-none');
        
        // Toggle buttons
        this.captureBtn.classList.add('d-none');
        this.retakeBtn.classList.remove('d-none');
        
        // Stop the camera after capturing the image
        this.stopCamera();
        console.log('Camera automatically closed after capturing image');
        
        // Custom event
        document.dispatchEvent(new CustomEvent('webcam:captured', {
            detail: { image: this.capturedImage }
        }));
    }
    
    retakeImage() {
        // Start the camera again since we stopped it after capturing
        this.startCamera();
        
        // Reset state
        this.isCaptured = false;
        this.capturedImage = null;
        
        // Update UI
        this.canvas.classList.add('d-none');
        this.video.classList.remove('d-none');
        this.faceGuidelines.classList.remove('d-none');
        
        // Toggle buttons
        this.retakeBtn.classList.add('d-none');
        this.captureBtn.classList.remove('d-none');
        
        // Custom event
        document.dispatchEvent(new CustomEvent('webcam:retake'));
    }
    
    getImageBase64() {
        return this.capturedImage;
    }
    
    reset() {
        // Reset to initial state
        this.stopCamera();
        
        // Reset UI elements
        this.video.classList.add('d-none');
        this.canvas.classList.add('d-none');
        this.cameraPlaceholder.classList.remove('d-none');
        this.faceGuidelines.classList.add('d-none');
        
        // Reset buttons
        this.startCameraBtn.classList.remove('d-none');
        this.captureBtn.classList.add('d-none');
        this.retakeBtn.classList.add('d-none');
        
        // Reset state
        this.isCaptured = false;
        this.capturedImage = null;
    }
}

// Create global instance
window.webcamHandler = new WebcamHandler();
