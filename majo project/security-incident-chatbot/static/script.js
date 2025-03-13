document.addEventListener('DOMContentLoaded', () => {
    const chatMessages = document.querySelector('.chat-messages');
    const inputField = document.querySelector('.input-field');
    const sendButton = document.querySelector('.send-button');
    const severityFilter = document.querySelector('#severity-filter');
    const startDate = document.querySelector('#start-date');
    const endDate = document.querySelector('#end-date');
    const loadHistoryButton = document.querySelector('#load-history');

    let isProcessing = false;

    function formatTimestamp(date) {
        return new Intl.DateTimeFormat('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            hour12: true
        }).format(new Date(date));
    }

    function createMessageElement(message, isAlert = false, severity = null, alertId = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isAlert ? 'alert' : 'response'}`;
        
        if (severity && (severity === 'High' || severity === 'Critical')) {
            messageDiv.classList.add(`severity-${severity.toLowerCase()}`);
        }

        const alertInfo = document.createElement('div');
        alertInfo.className = 'alert-info';

        if (severity) {
            const severityBadge = document.createElement('span');
            severityBadge.className = 'severity-badge';
            severityBadge.textContent = severity;
            alertInfo.appendChild(severityBadge);
        }

        const timestamp = document.createElement('span');
        timestamp.className = 'message-time';
        timestamp.textContent = formatTimestamp(new Date());
        alertInfo.appendChild(timestamp);

        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        messageContent.textContent = message;

        messageDiv.appendChild(alertInfo);
        messageDiv.appendChild(messageContent);

        // Add action buttons for alerts that are not user messages
        if (!isAlert && alertId) {
            const actionsDiv = document.createElement('div');
            actionsDiv.className = 'message-actions';

            // JIRA ticket button
            const jiraButton = document.createElement('button');
            jiraButton.className = 'action-button jira';
            jiraButton.textContent = 'Create JIRA Ticket';
            jiraButton.onclick = () => createJiraTicket(alertId);

            // Slack notification button
            const slackButton = document.createElement('button');
            slackButton.className = 'action-button slack';
            slackButton.textContent = 'Send to Slack';
            slackButton.onclick = () => sendSlackNotification(alertId);

            actionsDiv.appendChild(jiraButton);
            actionsDiv.appendChild(slackButton);
            messageDiv.appendChild(actionsDiv);
        }

        return messageDiv;
    }

    async function createJiraTicket(alertId) {
        try {
            const response = await fetch(`/create_ticket/${alertId}`, {
                method: 'POST'
            });
            const data = await response.json();
            chatMessages.appendChild(createMessageElement(data.message, false));
        } catch (error) {
            console.error('Error creating JIRA ticket:', error);
            chatMessages.appendChild(createMessageElement('Error creating JIRA ticket. Please try again.', false));
        }
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    async function sendSlackNotification(alertId) {
        try {
            const response = await fetch(`/slack_alert/${alertId}`, {
                method: 'POST'
            });
            const data = await response.json();
            chatMessages.appendChild(createMessageElement(data.message, false));
        } catch (error) {
            console.error('Error sending Slack notification:', error);
            chatMessages.appendChild(createMessageElement('Error sending Slack notification. Please try again.', false));
        }
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function addLoadingIndicator() {
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'loading response';
        loadingDiv.innerHTML = `
            Processing
            <div class="loading-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;
        chatMessages.appendChild(loadingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return loadingDiv;
    }

    async function loadAlertHistory() {
        const loadingIndicator = addLoadingIndicator();
        
        try {
            let url = '/alerts/?';
            const params = new URLSearchParams();
            
            if (severityFilter.value) {
                params.append('severity', severityFilter.value);
            }
            if (startDate.value) {
                params.append('start_date', new Date(startDate.value).toISOString());
            }
            if (endDate.value) {
                params.append('end_date', new Date(endDate.value).toISOString());
            }

            const response = await fetch(url + params.toString());
            const alerts = await response.json();

            // Clear existing messages
            chatMessages.innerHTML = '';

            // Display alerts
            alerts.forEach(alert => {
                const messageElement = createMessageElement(
                    alert.message,
                    false,
                    alert.severity,
                    alert.id
                );
                chatMessages.appendChild(messageElement);

                if (alert.jira_ticket_id) {
                    chatMessages.appendChild(
                        createMessageElement(`JIRA ticket: ${alert.jira_ticket_id}`, false)
                    );
                }
            });

        } catch (error) {
            console.error('Error loading history:', error);
            chatMessages.appendChild(createMessageElement('Error loading alert history. Please try again.', false));
        } finally {
            loadingIndicator.remove();
        }
    }

    async function processAlert(message) {
        if (isProcessing) return;
        isProcessing = true;

        // Add user message to chat
        chatMessages.appendChild(createMessageElement(message, true));
        
        // Add loading indicator
        const loadingIndicator = addLoadingIndicator();

        try {
            // Send alert to backend
            const response = await fetch('/process_alert/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    source: 'web_interface'
                })
            });

            if (!response.ok) {
                throw new Error('Failed to process alert');
            }

            const data = await response.json();
            
            // Remove loading indicator
            loadingIndicator.remove();

            // Add response to chat
            const responseMessage = `Alert processed with severity: ${data.severity}${data.jira_ticket_id ? '\nJIRA ticket created: ' + data.jira_ticket_id : ''}`;
            chatMessages.appendChild(createMessageElement(responseMessage, false, data.severity, data.id));

            // If high or critical severity, get automated response
            if (['High', 'Critical'].includes(data.severity)) {
                const automatedResponse = await fetch(`/automated_response/${data.id}`);
                const responseData = await automatedResponse.json();
                chatMessages.appendChild(createMessageElement(responseData.response, false));
            }

        } catch (error) {
            console.error('Error:', error);
            loadingIndicator.remove();
            chatMessages.appendChild(createMessageElement('Error processing alert. Please try again.', false));
        }

        chatMessages.scrollTop = chatMessages.scrollHeight;
        isProcessing = false;
    }

    // Event listeners
    sendButton.addEventListener('click', () => {
        const message = inputField.value.trim();
        if (message) {
            processAlert(message);
            inputField.value = '';
        }
    });

    inputField.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendButton.click();
        }
    });

    loadHistoryButton.addEventListener('click', loadAlertHistory);
}); 