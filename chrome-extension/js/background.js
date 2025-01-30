// Background script for Gmail PDF Processor Extension

class GmailPDFProcessor {
    constructor() {
        this.AUTH_TOKEN = null;
        this.setupListeners();
        this.setupErrorHandling();
    }

    setupListeners() {
        // Listen for messages from popup and content scripts
        chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
            switch (request.action) {
                case 'authenticate':
                    this.authenticate().then(sendResponse);
                    return true;
                case 'processEmails':
                    this.processEmails(request.params).then(sendResponse);
                    return true;
                case 'downloadPDF':
                    this.downloadPDF(request.params).then(sendResponse);
                    return true;
            }
        });
    }

    setupErrorHandling() {
        // Global error handler
        window.onerror = (message, source, lineno, colno, error) => {
            console.error('Global error:', { message, source, lineno, colno, error });
            return false;
        };

        // Unhandled promise rejection handler
        window.onunhandledrejection = (event) => {
            console.error('Unhandled promise rejection:', event.reason);
        };
    }

    async authenticate() {
        try {
            const token = await this.getAuthToken();
            this.AUTH_TOKEN = token;
            return { success: true, token };
        } catch (error) {
            console.error('Authentication error:', error);
            return { success: false, error: error.message };
        }
    }

    async getAuthToken() {
        return new Promise((resolve, reject) => {
            chrome.identity.getAuthToken({ interactive: true }, (token) => {
                if (chrome.runtime.lastError) {
                    reject(chrome.runtime.lastError);
                } else {
                    resolve(token);
                }
            });
        });
    }

    async processEmails({ keywords, dateRange, includePassword, organizeBySender }) {
        try {
            if (!this.AUTH_TOKEN) {
                throw new Error('Not authenticated');
            }

            // Convert date range to Gmail query format
            const dateQuery = this.convertDateRange(dateRange);
            const query = `has:attachment filename:pdf ${keywords.join(' OR ')} ${dateQuery}`;

            // Fetch emails from Gmail API
            const emails = await this.searchGmail(query);
            const attachments = await this.extractAttachments(emails, includePassword);

            if (organizeBySender) {
                return this.organizeAttachmentsBySender(attachments);
            }

            return { success: true, attachments };
        } catch (error) {
            console.error('Process emails error:', error);
            return { success: false, error: error.message };
        }
    }

    async searchGmail(query) {
        try {
            if (!query) {
                throw new Error('Search query cannot be empty');
            }

            const response = await fetch(
                `https://www.googleapis.com/gmail/v1/users/me/messages?q=${encodeURIComponent(query)}`,
                {
                    headers: {
                        Authorization: `Bearer ${this.AUTH_TOKEN}`,
                    },
                }
            );

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(`Gmail API error: ${errorData.error?.message || response.statusText}`);
            }

            const data = await response.json();
            
            if (!data.messages || data.messages.length === 0) {
                return [];
            }

            return Promise.all(
                data.messages.map(msg => this.getEmailDetails(msg.id))
            );
        } catch (error) {
            console.error('Search Gmail error:', error);
            throw error;
        }
    }

    async getEmailDetails(messageId) {
        const response = await fetch(
            `https://www.googleapis.com/gmail/v1/users/me/messages/${messageId}`,
            {
                headers: {
                    Authorization: `Bearer ${this.AUTH_TOKEN}`,
                },
            }
        );

        if (!response.ok) {
            throw new Error('Failed to fetch email details');
        }

        return response.json();
    }

    async extractAttachments(emails, includePassword) {
        const attachments = [];

        for (const email of emails) {
            const parts = email.payload.parts || [];
            const sender = this.getEmailSender(email);
            const subject = this.getEmailSubject(email);
            const date = new Date(parseInt(email.internalDate));

            for (const part of parts) {
                if (part.mimeType === 'application/pdf') {
                    attachments.push({
                        id: part.body.attachmentId,
                        filename: part.filename,
                        messageId: email.id,
                        sender,
                        subject,
                        date,
                        size: part.body.size,
                    });
                }
            }
        }

        return attachments;
    }

    getEmailSender(email) {
        const headers = email.payload.headers;
        const fromHeader = headers.find(h => h.name.toLowerCase() === 'from');
        return fromHeader ? fromHeader.value : '';
    }

    getEmailSubject(email) {
        const headers = email.payload.headers;
        const subjectHeader = headers.find(h => h.name.toLowerCase() === 'subject');
        return subjectHeader ? subjectHeader.value : '';
    }

    organizeAttachmentsBySender(attachments) {
        return attachments.reduce((acc, attachment) => {
            const sender = attachment.sender;
            if (!acc[sender]) {
                acc[sender] = [];
            }
            acc[sender].push(attachment);
            return acc;
        }, {});
    }

    convertDateRange(dateRange) {
        // Convert user-friendly date range to Gmail query format
        const now = new Date();
        let daysAgo;

        if (dateRange.includes('day')) {
            daysAgo = parseInt(dateRange);
        } else if (dateRange.includes('week')) {
            daysAgo = parseInt(dateRange) * 7;
        } else if (dateRange.includes('month')) {
            daysAgo = parseInt(dateRange) * 30;
        }

        const pastDate = new Date(now.getTime() - (daysAgo * 24 * 60 * 60 * 1000));
        return `after:${pastDate.getFullYear()}/${pastDate.getMonth() + 1}/${pastDate.getDate()}`;
    }

    async downloadPDF(params) {
        try {
            if (!params.messageId || !params.attachmentId || !params.filename) {
                throw new Error('Missing required download parameters');
            }

            const response = await fetch(
                `https://www.googleapis.com/gmail/v1/users/me/messages/${params.messageId}/attachments/${params.attachmentId}`,
                {
                    headers: {
                        Authorization: `Bearer ${this.AUTH_TOKEN}`,
                    },
                }
            );

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(`Download error: ${errorData.error?.message || response.statusText}`);
            }

            const data = await response.json();
            
            if (!data.data) {
                throw new Error('No attachment data received');
            }

            const pdfBlob = this.base64ToBlob(data.data, 'application/pdf');
            
            return new Promise((resolve, reject) => {
                const downloadUrl = URL.createObjectURL(pdfBlob);
                
                chrome.downloads.download({
                    url: downloadUrl,
                    filename: this.sanitizeFilename(params.filename),
                    saveAs: true
                }, (downloadId) => {
                    URL.revokeObjectURL(downloadUrl);
                    
                    if (chrome.runtime.lastError) {
                        reject(chrome.runtime.lastError);
                    } else {
                        resolve({ success: true, downloadId });
                    }
                });
            });
        } catch (error) {
            console.error('Download PDF error:', error);
            return { success: false, error: error.message };
        }
    }

    base64ToBlob(base64, mimeType) {
        const byteCharacters = atob(base64.replace(/-/g, '+').replace(/_/g, '/'));
        const byteArrays = [];

        for (let offset = 0; offset < byteCharacters.length; offset += 512) {
            const slice = byteCharacters.slice(offset, offset + 512);
            const byteNumbers = new Array(slice.length);
            
            for (let i = 0; i < slice.length; i++) {
                byteNumbers[i] = slice.charCodeAt(i);
            }
            
            byteArrays.push(new Uint8Array(byteNumbers));
        }

        return new Blob(byteArrays, { type: mimeType });
    }

    sanitizeFilename(filename) {
        // Remove invalid characters from filename
        return filename.replace(/[<>:"/\\|?*]/g, '_');
    }
}

// Initialize the processor
const processor = new GmailPDFProcessor(); 