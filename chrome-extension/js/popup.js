// Popup script for Gmail PDF Processor Extension

class PopupUI {
    constructor() {
        this.loginSection = document.getElementById('login-section');
        this.mainSection = document.getElementById('main-section');
        this.loginBtn = document.getElementById('login-btn');
        this.processBtn = document.getElementById('process-btn');
        this.searchKeywords = document.getElementById('search-keywords');
        this.dateRange = document.getElementById('date-range');
        this.includePassword = document.getElementById('include-password');
        this.organizeBySender = document.getElementById('organize-by-sender');
        this.resultsList = document.getElementById('results-list');
        this.progressBar = document.getElementById('progress-bar').querySelector('.progress-value');
        this.statusMessage = document.getElementById('status-message');

        this.setupEventListeners();
        this.checkAuthStatus();
    }

    setupEventListeners() {
        this.loginBtn.addEventListener('click', () => this.authenticate());
        this.processBtn.addEventListener('click', () => this.processEmails());
    }

    async checkAuthStatus() {
        const response = await this.sendMessage({ action: 'authenticate' });
        if (response.success) {
            this.showMainUI();
        }
    }

    async authenticate() {
        this.setStatus('Authenticating...', 'warning');
        const response = await this.sendMessage({ action: 'authenticate' });
        
        if (response.success) {
            this.showMainUI();
            this.setStatus('Successfully authenticated!', 'success');
        } else {
            this.setStatus('Authentication failed: ' + response.error, 'error');
        }
    }

    showMainUI() {
        this.loginSection.style.display = 'none';
        this.mainSection.style.display = 'block';
    }

    async processEmails() {
        const keywords = this.searchKeywords.value.split(',').map(k => k.trim()).filter(k => k);
        if (keywords.length === 0) {
            this.setStatus('Please enter at least one keyword', 'error');
            return;
        }

        const dateRange = this.dateRange.value.trim();
        if (!dateRange) {
            this.setStatus('Please enter a date range', 'error');
            return;
        }

        this.setStatus('Processing emails...', 'warning');
        this.progressBar.style.width = '0%';
        this.resultsList.innerHTML = '';
        this.processBtn.disabled = true;

        try {
            const response = await this.sendMessage({
                action: 'processEmails',
                params: {
                    keywords,
                    dateRange,
                    includePassword: this.includePassword.checked,
                    organizeBySender: this.organizeBySender.checked
                }
            });

            if (response.success) {
                this.displayResults(response.attachments);
                this.setStatus('Processing complete!', 'success');
            } else {
                this.setStatus('Processing failed: ' + response.error, 'error');
            }
        } catch (error) {
            this.setStatus('Error: ' + error.message, 'error');
        } finally {
            this.processBtn.disabled = false;
        }
    }

    displayResults(attachments) {
        this.resultsList.innerHTML = '';
        
        if (this.organizeBySender.checked) {
            // Display results grouped by sender
            for (const [sender, files] of Object.entries(attachments)) {
                const senderElement = document.createElement('li');
                senderElement.className = 'sender-group';
                senderElement.innerHTML = `
                    <strong>${sender}</strong>
                    <ul class="attachment-list">
                        ${files.map(file => this.createAttachmentElement(file)).join('')}
                    </ul>
                `;
                this.resultsList.appendChild(senderElement);
            }
        } else {
            // Display flat list of results
            attachments.forEach(attachment => {
                this.resultsList.appendChild(
                    this.createAttachmentListItem(attachment)
                );
            });
        }
    }

    createAttachmentElement(attachment) {
        const date = new Date(attachment.date).toLocaleDateString();
        const size = this.formatFileSize(attachment.size);
        
        return `
            <li class="attachment-item">
                <div class="attachment-info">
                    <span class="filename">${attachment.filename}</span>
                    <span class="details">${date} - ${size}</span>
                </div>
                <button class="download-btn" onclick="popupUI.downloadPDF('${attachment.messageId}', '${attachment.id}', '${attachment.filename}')">
                    Download
                </button>
            </li>
        `;
    }

    createAttachmentListItem(attachment) {
        const li = document.createElement('li');
        li.innerHTML = this.createAttachmentElement(attachment);
        return li;
    }

    async downloadPDF(messageId, attachmentId, filename) {
        this.setStatus('Downloading PDF...', 'warning');
        
        try {
            const response = await this.sendMessage({
                action: 'downloadPDF',
                params: { messageId, attachmentId, filename }
            });

            if (response.success) {
                this.setStatus('Download started!', 'success');
            } else {
                this.setStatus('Download failed: ' + response.error, 'error');
            }
        } catch (error) {
            this.setStatus('Error: ' + error.message, 'error');
        }
    }

    formatFileSize(bytes) {
        const units = ['B', 'KB', 'MB', 'GB'];
        let size = bytes;
        let unitIndex = 0;

        while (size >= 1024 && unitIndex < units.length - 1) {
            size /= 1024;
            unitIndex++;
        }

        return `${size.toFixed(1)} ${units[unitIndex]}`;
    }

    setStatus(message, type) {
        this.statusMessage.textContent = message;
        this.statusMessage.className = `status ${type}`;
    }

    sendMessage(message) {
        return new Promise((resolve, reject) => {
            chrome.runtime.sendMessage(message, response => {
                if (chrome.runtime.lastError) {
                    reject(chrome.runtime.lastError);
                } else {
                    resolve(response);
                }
            });
        });
    }
}

// Initialize the popup UI
const popupUI = new PopupUI(); 