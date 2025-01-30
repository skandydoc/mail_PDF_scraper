// Content script for Gmail PDF Processor Extension
// This script runs in the context of Gmail pages

// Listen for messages from the background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    // Handle any page-specific operations here if needed
    return true;
});

// Add any Gmail-specific functionality here if needed in the future
console.log('Gmail PDF Processor Extension: Content script loaded'); 