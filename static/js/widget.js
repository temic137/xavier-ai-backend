(function() {
    // Get configuration from script tag
    const script = document.currentScript;
    const config = {
        chatbotId: script.getAttribute('data-chatbot-id'),
        name: script.getAttribute('data-name') || 'Support Agent',
        askUrl: script.getAttribute('data-ask-url'),
        feedbackUrl: script.getAttribute('data-feedback-url'),
        ticketUrl: script.getAttribute('data-ticket-url'),
        avatar: script.getAttribute('data-avatar') || './assets/agent.png',
        themeColor: script.getAttribute('data-theme-color') || '#0066CC'
    };

    // Styles
    const styles = `
        .chatbot-container {
            position: fixed;
            bottom: 20px;
            right: 20px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            z-index: 999999;
            width: 360px;
            line-height: normal;
        }

        .chatbot-toggle {
            background: ${config.themeColor};
            color: white;
            border: none;
            padding: 16px;
            border-radius: 50%;
            cursor: pointer;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            transition: all 0.3s ease;
            width: 60px;
            height: 60px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-left: auto;
        }

        .chatbot-toggle:hover {
            background: ${adjustColor(config.themeColor, -20)};
            transform: scale(1.05);
        }

        .chatbot-toggle svg {
            width: 30px;
            height: 30px;
            fill: currentColor;
        }

        .chatbot-avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            border: 2px solid white;
            object-fit: cover;
        }

        .chatbot-content {
            display: none;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            margin-bottom: 16px;
            overflow: hidden;
            height: 480px;
            flex-direction: column;
            position: relative;
        }

        .chatbot-content.chatbot-visible {
            display: flex;
        }

        .chatbot-header {
            padding: 20px;
            background: ${config.themeColor};
            border-bottom: 1px solid #eee;
            color: #FFFFFF;
            display: flex;
            align-items: flex-start;
            gap: 12px;
            position: relative;
        }

        .chatbot-header-info {
            display: flex;
            align-items: center;
            gap: 12px;
            flex: 1;
        }

        .chatbot-header-text {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .chatbot-header-dropdown {
            position: relative;
            display: inline-block;
        }

        .chatbot-header-actions {
            display: flex;
            flex-direction: column;
            gap: 8px;
            margin-top: 4px;
        }

        .chatbot-header-actions-button {
            background: none;
            border: none;
            color: #FFFFFF;
            cursor: pointer;
            padding: 8px;
            font-size: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 4px;
        }

        .chatbot-header-actions-button:hover {
            background: rgba(255, 255, 255, 0.1);
        }

        .chatbot-dropdown-menu {
            display: none;
            position: absolute;
            right: 0;
            top: 100%;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            min-width: 160px;
            z-index: 1000;
            margin-top: 4px;
        }

        .chatbot-dropdown-menu.show {
            display: block;
        }

        .chatbot-dropdown-item {
            padding: 12px 16px;
            color: #333;
            text-decoration: none;
            display: flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
            transition: background 0.2s ease;
            font-size: 14px;
        }

        .chatbot-dropdown-item:hover {
            background: #f5f5f5;
        }

        .chatbot-dropdown-item:first-child {
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
        }

        .chatbot-dropdown-item:last-child {
            border-bottom-left-radius: 8px;
            border-bottom-right-radius: 8px;
        }

        .chatbot-feedback-trigger {
            background: rgba(255, 255, 255, 0.1);
            border: none;
            color: #FFFFFF;
            cursor: pointer;
            padding: 8px 12px;
            font-size: 14px;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            width: 140px;
            transition: background-color 0.2s ease;
        }

        .chatbot-feedback-trigger:hover {
            background: rgba(255, 255, 255, 0.2);
        }

        .chatbot-feedback-trigger span:last-child {
            margin-left: 4px;
        }

        .chatbot-close-chat {
            position: absolute;
            top: 8px;
            right: 8px;
            background: none;
            border: none;
            color: #FFFFFF;
            font-size: 24px;
            cursor: pointer;
            padding: 4px;
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            transition: background-color 0.2s ease;
        }

        .chatbot-close-chat:hover {
            background: rgba(255, 255, 255, 0.1);
        }

        .chatbot-status-dot {
            width: 8px;
            height: 8px;
            background: #22C55E;
            border-radius: 50%;
            margin-right: 4px;
            display: inline-block;
        }

        .chatbot-messages {
            flex-grow: 1;
            overflow-y: auto;
            padding: 20px;
            background: #f8f9fa;
        }

        .chatbot-messages::-webkit-scrollbar {
            width: 6px;
        }

        .chatbot-messages::-webkit-scrollbar-track {
            background: #f1f1f1;
        }

        .chatbot-messages::-webkit-scrollbar-thumb {
            background: #888;
            border-radius: 3px;
        }

        .chatbot-message {
            margin-bottom: 12px;
            padding: 12px 16px;
            border-radius: 12px;
            max-width: 85%;
            font-size: 14px;
            line-height: 1.5;
            word-wrap: break-word;
        }

        .chatbot-message.user {
            background: ${config.themeColor};
            color: white;
            margin-left: auto;
            border-bottom-right-radius: 4px;
        }

        .chatbot-message.bot {
            background: white;
            color: #1a1a1a;
            border-bottom-left-radius: 4px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }

        .chatbot-message.error {
            background: #fee2e2;
            color: #991b1b;
            margin-left: auto;
            border-bottom-right-radius: 4px;
        }

        .chatbot-input-container {
            padding: 16px;
            background: white;
            border-top: 1px solid #eee;
        }

        .chatbot-input-wrapper {
            display: flex;
            align-items: center;
            background: #f8f9fa;
            border-radius: 8px;
            padding: 8px 16px;
            gap: 8px;
        }

        .chatbot-input {
            flex-grow: 1;
            border: none;
            background: transparent;
            padding: 8px 0;
            font-size: 14px;
            min-width: 0;
            color: #1a1a1a;
        }

        .chatbot-input:focus {
            outline: none;
        }

        .chatbot-input::placeholder {
            color: #6b7280;
        }

        .chatbot-send {
            background: none;
            border: none;
            color: ${config.themeColor};
            padding: 8px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .chatbot-send:disabled {
            color: #ccc;
            cursor: not-allowed;
        }

        .chatbot-send svg {
            width: 20px;
            height: 20px;
        }

        .powered-by {
            text-align: center;
            font-size: 12px;
            color: #666;
            padding: 8px;
            background: white;
            border-top: 1px solid #eee;
        }

        .chatbot-typing {
            padding: 12px 16px;
            background: #F5F5F5;
            border-radius: 12px;
            border-bottom-left-radius: 4px;
            display: inline-block;
            margin-bottom: 12px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }

        .chatbot-typing-dots {
            display: flex;
            gap: 4px;
            padding: 0 4px;
        }

        .chatbot-typing-dot {
            width: 8px;
            height: 8px;
            background: ${config.themeColor};
            border-radius: 50%;
            animation: typing 1.4s infinite;
            opacity: 0.2;
        }

        .chatbot-typing-dot:nth-child(2) {
            animation-delay: 0.2s;
        }

        .chatbot-typing-dot:nth-child(3) {
            animation-delay: 0.4s;
        }

        .chatbot-ticket-form {
            display: none;
            padding: 20px;
            background: white;
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            z-index: 2;
            overflow-y: auto;
        }

        .chatbot-ticket-form.chatbot-visible {
            display: block;
        }

        .chatbot-ticket-form h3 {
            margin: 0 0 16px 0;
            color: ${config.themeColor};
            font-size: 18px;
        }

        .chatbot-form-group {
            margin-top:2px;
            margin-bottom: 16px;
        }

        .chatbot-form-group label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-size: 14px;
        }

        .chatbot-form-group input,
        .chatbot-form-group textarea,
        .chatbot-form-group select {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }

        .chatbot-form-group textarea {
            height: 100px;
            resize: vertical;
        }

        .chatbot-ticket-actions {
            display: flex;
            gap: 8px;
        }

        .chatbot-ticket-submit,
        .chatbot-ticket-cancel {
            flex: 1;
            padding: 10px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.2s ease;
        }

        .chatbot-ticket-submit {
            background: ${config.themeColor};
            color: white;
        }

        .chatbot-ticket-cancel {
            background: #e1e1e1;
            color: #333;
        }

        .chatbot-feedback-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            justify-content: center;
            align-items: center;
            z-index: 1000000;
        }

        .chatbot-feedback-modal.chatbot-visible {
            display: flex;
        }

        .chatbot-feedback-content {
            background: white;
            padding: 24px;
            border-radius: 12px;
            width: 90%;
            max-width: 400px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }

        .chatbot-feedback-content h3 {
            margin: 0 0 16px 0;
            color: #1a1a1a;
            font-size: 18px;
        }

        .chatbot-feedback-content textarea {
            width: 100%;
            height: 120px;
            padding: 12px;
            margin-bottom: 16px;
            border: 1px solid ${config.themeColor};
            border-radius: 8px;
            font-size: 14px;
            resize: vertical;
        }

         .chatbot-feedback-content textarea:focus {
            
            border-color: ${config.themeColor};
        }

        .chatbot-feedback-submit {
            width: 100%;
            background: #e1e1e1 ;
            color: ${config.themeColor};
            border: none;
            padding: 12px;
            border-radius: 8px;
            cursor: pointer;
            margin-bottom: 8px;
            font-size: 14px;
            transition: background 0.2s ease;
        }

         .chatbot-feedback-submit:hover {
           
        }

        .chatbot-feedback-cancel {
            width: 100%;
            background:#e1e1e1 ;
            color: ${config.themeColor};
            border: none;
            padding: 12px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.2s ease;
        }

        .chatbot-feedback-cancel:hover {
            background: #e1e1e1;
        }

        @keyframes typing {
            0%, 100% { opacity: 0.2; transform: translateY(0); }
            50% { opacity: 1; transform: translateY(-2px); }
        }

        @media (max-width: 480px) {
            .chatbot-container {
                right: 10px;
                left: 10px;
                bottom: 10px;
                width: auto;
            }
            
            .chatbot-content {
                height: calc(100vh - 100px);
            }
        }
    `;

    // Helper function to adjust color brightness
    function adjustColor(color, amount) {
        const hex = color.replace('#', '');
        const r = Math.max(0, Math.min(255, parseInt(hex.substr(0, 2), 16) + amount));
        const g = Math.max(0, Math.min(255, parseInt(hex.substr(2, 2), 16) + amount));
        const b = Math.max(0, Math.min(255, parseInt(hex.substr(4, 2), 16) + amount));
        return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
    }

    // Inject styles
    const styleSheet = document.createElement('style');
    styleSheet.textContent = styles;
    document.head.appendChild(styleSheet);

    // Create widget HTML
    const widget = document.createElement('div');
    widget.innerHTML = `
        <div id="chatbot-widget" class="chatbot-container">
            <button id="chatbot-toggle" class="chatbot-toggle">
                <svg viewBox="0 0 60 60" xmlns="http://www.w3.org/2000/svg">
                    <path d="M59.949,58.684L55.104,44.15C57.654,39.702,59,34.647,59,29.5C59,13.233,45.767,0,29.5,0S0,13.233,0,29.5S13.233,59,29.5,59c4.64,0,9.257-1.108,13.378-3.208l15.867,4.176C58.83,59.989,58.915,60,59,60c0.272,0,0.538-0.112,0.729-0.316C59.98,59.416,60.065,59.032,59.949,58.684z M16,21.015h14c0.552,0,1,0.448,1,1s-0.448,1-1,1H16c-0.552,0-1-0.448-1-1S15.448,21.015,16,21.015z M43,39.015H16c-0.552,0-1-0.448-1-1s0.448-1,1-1h27c0.552,0,1,0.448,1,1S43.552,39.015,43,39.015z M43,31.015H16c-0.552,0-1-0.448-1-1s0.448-1,1-1h27c0.552,0,1,0.448,1,1S43.552,31.015,43,31.015z"/>
                </svg>
            </button>
            
            <div id="chatbot-content" class="chatbot-content">
                <div class="chatbot-header">
                    <div class="chatbot-header-info">
                        <img src="${config.avatar}" class="chatbot-avatar" alt="${config.name}">
                        <div class="chatbot-header-text">
                            <div style="font-weight: 600">${config.name}</div>
                            <div style="font-size: 14px;">
                                <span class="chatbot-status-dot"></span>Online
                            </div>
                        </div>
                    </div>
                
                        <div class="chatbot-header-actions">
                <div class="chatbot-header-dropdown">
                    <button class="chatbot-header-actions-button" onclick="window.chatbotWidget.toggleDropdown()">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="3" y1="12" x2="21" y2="12"></line>
                            <line x1="3" y1="6" x2="21" y2="6"></line>
                            <line x1="3" y1="18" x2="21" y2="18"></line>
                        </svg>
                    </button>
                    <div id="chatbot-dropdown-menu" class="chatbot-dropdown-menu">
                        <button class="chatbot-dropdown-item" onclick="window.chatbotWidget.openTicketForm()">
                            <span>Create Ticket</span>
                            <span>🎫</span>
                        </button>
                        <button class="chatbot-dropdown-item" onclick="window.chatbotWidget.openFeedback()">
                            <span>Feedback</span>
                            <span>💬</span>
                        </button>
                    </div>
                </div>

            </div>
                    
                    <button class="chatbot-close-chat" onclick="window.chatbotWidget.toggle()">×</button>
                </div>
                        
                <div id="chatbot-messages" class="chatbot-messages">
                    <div class="chatbot-message bot">
                        Hi there! 👋 How can I help you today?
                    </div>
                </div>
                
                <div class="chatbot-input-container">
                    <div class="chatbot-input-wrapper">
                        <input type="text" 
                               id="chatbot-input" 
                               class="chatbot-input"
                               placeholder="Type your message..."
                               autocomplete="off"
                               onkeypress="if(event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); window.chatbotWidget.send(); }">
                        <button id="chatbot-send" onclick="window.chatbotWidget.send()" class="chatbot-send" disabled>
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M22 2L11 13M22 2L15 22L11 13M11 13L2 9L22 2"/>
                            </svg>
                        </button>
                    </div>
                </div>
                
                <div class="powered-by">Powered by Xavier AI</div>

                <!-- Ticket Form -->
                <div id="chatbot-ticket-form" class="chatbot-ticket-form">
                    <h3>Create Support Ticket</h3>
                    <h5>(It might take sometime to get a response)</h5>
                    <div class="chatbot-form-group">
                        <label for="ticket-subject">Subject</label>
                        <input type="text" id="ticket-subject" required>
                    </div>
                    <div class="chatbot-form-group">
                        <label for="ticket-description">Description</label>
                        <textarea id="ticket-description" required></textarea>
                    </div>
                    <div class="chatbot-form-group">
                        <label for="ticket-priority">Priority</label>
                        <select id="ticket-priority">
                            <option value="low">Low</option>
                            <option value="medium">Medium</option>
                            <option value="high">High</option>
                        </select>
                    </div>
                    <div class="chatbot-form-group">
                        <label for="ticket-account">Account Details</label>
                        <input type="text" id="ticket-account" required>
                    </div>
                    <div class="chatbot-ticket-actions">
                        <button onclick="window.chatbotWidget.submitTicket()" 
                                class="chatbot-ticket-submit">Submit Ticket</button>
                        <button onclick="window.chatbotWidget.closeTicketForm()" 
                                class="chatbot-ticket-cancel">Cancel</button>
                    </div>
                </div>
            </div>

            <!-- Feedback Modal -->
            <div id="chatbot-feedback" class="chatbot-feedback-modal">
                <div class="chatbot-feedback-content">
                    <h3>Provide Feedback</h3>
                    <textarea id="chatbot-feedback-text" 
                             placeholder="Your feedback helps us improve..."></textarea>
                    <button onclick="window.chatbotWidget.submitFeedback()" 
                            class="chatbot-feedback-submit">Submit</button>
                    <button onclick="window.chatbotWidget.closeFeedback()" 
                            class="chatbot-feedback-cancel">Cancel</button>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(widget);

    // Initialize widget functionality
    window.chatbotWidget = {
        userId: 'user_' + Math.random().toString(36).substr(2, 9),
        isTyping: false,
        
        toggle() {
            const content = document.getElementById('chatbot-content');
            const toggle = document.getElementById('chatbot-toggle');
            content.classList.toggle('chatbot-visible');
            toggle.style.display = content.classList.contains('chatbot-visible') ? 'none' : 'flex';
            
            if (content.classList.contains('chatbot-visible')) {
                document.getElementById('chatbot-input').focus();
            }
        },
        toggleDropdown() {
            const dropdown = document.getElementById('chatbot-dropdown-menu');
            dropdown.classList.toggle('show');

            // Close dropdown when clicking outside
            const closeDropdown = (event) => {
                if (!event.target.matches('.chatbot-header-actions-button')) {
                    dropdown.classList.remove('show');
                    document.removeEventListener('click', closeDropdown);
                }
            };

            if (dropdown.classList.contains('show')) {
                setTimeout(() => {
                    document.addEventListener('click', closeDropdown);
                }, 0);
            }
        },

        showTyping() {
            if (this.isTyping) return;
            
            this.isTyping = true;
            const messages = document.getElementById('chatbot-messages');
            messages.insertAdjacentHTML('beforeend', `
                <div id="typing-indicator" class="chatbot-typing">
                    <div class="chatbot-typing-dots">
                        <div class="chatbot-typing-dot"></div>
                        <div class="chatbot-typing-dot"></div>
                        <div class="chatbot-typing-dot"></div>
                    </div>
                </div>
            `);
            messages.scrollTop = messages.scrollHeight;
        },

        hideTyping() {
            if (!this.isTyping) return;
            
            this.isTyping = false;
            const typingIndicator = document.getElementById('typing-indicator');
            if (typingIndicator) {
                typingIndicator.remove();
            }
        },

        async send() {
            const input = document.getElementById('chatbot-input');
            const messages = document.getElementById('chatbot-messages');
            const sendButton = document.getElementById('chatbot-send');
            const question = input.value.trim();
            
            if (!question) return;
            
            try {
                // Disable input and button while sending
                input.disabled = true;
                sendButton.disabled = true;
                
                // Add user message
                messages.innerHTML += `<div class="chatbot-message user">${this.escapeHtml(question)}</div>`;
                input.value = '';
                messages.scrollTop = messages.scrollHeight;
                
                // Show typing indicator
                this.showTyping();
                
                // Send request to backend
                const response = await fetch(config.askUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'User-ID': this.userId
                    },
                    body: JSON.stringify({ question })
                });
                
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                
                const data = await response.json();
                
                // Hide typing indicator and show response
                this.hideTyping();
                messages.innerHTML += `<div class="chatbot-message bot">${this.escapeHtml(data.answer)}</div>`;
                
            } catch (error) {
                console.error('Chatbot error:', error);
                this.hideTyping();
                messages.innerHTML += `
                    <div class="chatbot-message error">
                        Sorry, something went wrong. Please try again.
                    </div>
                `;
            } finally {
                // Re-enable input and button
                input.disabled = false;
                sendButton.disabled = false;
                input.focus();
                messages.scrollTop = messages.scrollHeight;
            }
        },

        openFeedback() {
            document.getElementById('chatbot-feedback').classList.add('chatbot-visible');
        },

        closeFeedback() {
            document.getElementById('chatbot-feedback').classList.remove('chatbot-visible');
            document.getElementById('chatbot-feedback-text').value = '';
        },

        async submitFeedback() {
            const textarea = document.getElementById('chatbot-feedback-text');
            const feedback = textarea.value.trim();
            
            if (!feedback) {
                alert('Please enter your feedback before submitting.');
                return;
            }
            
            try {
                await fetch(config.feedbackUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'User-ID': this.userId
                    },
                    body: JSON.stringify({ feedback })
                });
                
                alert('Thank you for your feedback!');
                this.closeFeedback();
            } catch (error) {
                console.error('Feedback error:', error);
                alert('Sorry, we couldn\'t submit your feedback. Please try again.');
            }
        },

        openTicketForm() {
            document.getElementById('chatbot-ticket-form').classList.add('chatbot-visible');
        },

        
        closeTicketForm() {
            document.getElementById('chatbot-ticket-form').classList.remove('chatbot-visible');
            // Reset form
            document.getElementById('ticket-subject').value = '';
            document.getElementById('ticket-description').value = '';
            document.getElementById('ticket-priority').value = 'medium';
            document.getElementById('ticket-account').value = '';
        },

        async submitTicket() {
            const subject = document.getElementById('ticket-subject').value.trim();
            const description = document.getElementById('ticket-description').value.trim();
            const priority = document.getElementById('ticket-priority').value;
            const accountDetails = document.getElementById('ticket-account').value.trim();

            if (!subject || !description || !accountDetails) {
                alert('Please fill in all required fields');
                return;
            }

            try {
                const response = await fetch(config.ticketUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'User-ID': this.userId
                    },
                    body: JSON.stringify({
                        subject,
                        description,
                        priority,
                        account_details: accountDetails
                    })
                });

                if (!response.ok) {
                    throw new Error('Failed to create ticket');
                }

                const data = await response.json();
                
                // Add success message to chat
                const messages = document.getElementById('chatbot-messages');
                messages.innerHTML += `
                    <div class="chatbot-message bot">
                        Ticket created successfully! Your ticket ID is: ${data.ticket_id}
                    </div>
                `;
                messages.scrollTop = messages.scrollHeight;

                this.closeTicketForm();
            } catch (error) {
                console.error('Ticket creation error:', error);
                alert('Sorry, we couldn\'t create your ticket. Please try again.');
            }
        },

        escapeHtml(unsafe) {
            return unsafe
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        }
    };

    // Add event listeners
    document.getElementById('chatbot-toggle').onclick = () => window.chatbotWidget.toggle();
    
    // Add event listeners
    const input = document.getElementById('chatbot-input');
    const sendButton = document.getElementById('chatbot-send');
    
    input.addEventListener('input', () => {
        sendButton.disabled = !input.value.trim();
    });
})();
