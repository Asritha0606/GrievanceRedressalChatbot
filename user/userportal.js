document.addEventListener('DOMContentLoaded', function () {
    // Tab Functionality
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.getAttribute('data-tab');

            // Remove active class from all buttons and contents
            tabBtns.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));

            // Add active class to current button and content
            btn.classList.add('active');
            document.getElementById(`${tabId}-section`).classList.add('active');
        });
    });

    // Chat Functionality
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const complaintForm = document.getElementById('complaint-form');

    // Enhanced addMessage function with bot logo support
    function addMessage(message, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', isUser ? 'user' : 'bot');
        
        if (!isUser) {
            // Add bot logo for bot messages
            const logoDiv = document.createElement('div');
            logoDiv.classList.add('bot-logo');
            const icon = document.createElement('i');
            icon.classList.add('fas', 'fa-robot');
            logoDiv.appendChild(icon);
            messageDiv.appendChild(logoDiv);
        }
        
        const textDiv = document.createElement('div');
        textDiv.textContent = message;
        messageDiv.appendChild(textDiv);
        
        // Add typing animation for bot messages
        if (!isUser) {
            messageDiv.style.opacity = '0';
            setTimeout(() => {
                messageDiv.style.opacity = '1';
            }, 100);
        }
        
        const chatMessages = document.getElementById('chat-messages');
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return messageDiv;
    }

    async function handleUserInput() {
        const message = userInput.value.trim();
        if (!message) return;

        // Hide complaint form if visible
        const complaintForm = document.getElementById('complaint-form');
        if (complaintForm.style.display === 'block') {
            complaintForm.style.display = 'none';
            complaintForm.classList.remove('show');
        }

        // Add user message to chat
        addMessage(message, true);
        
        // Disable input and button while processing
        userInput.disabled = true;
        sendBtn.disabled = true;
        
        // Add loading indicator
        const loadingMessage = addMessage("Typing...", false);
        loadingMessage.classList.add('bot-typing');
        
        try {
            // Clear input field
            userInput.value = '';
            
            const response = await fetch('http://127.0.0.1:5000/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message })
            });

            const result = await response.json();

            // Remove loading message
            loadingMessage.remove();

            if (result.success) {
                // Always show the bot's reply first
                addMessage(result.reply);

                if (result.type === 'complaint') {
                    // Add a small delay before showing follow-up messages
                    setTimeout(() => {
                        addMessage(`To ensure we capture all the necessary details and get this resolved efficiently, could you please fill out the form below?`);
                        
                        // Show form with smooth animation
                        complaintForm.style.display = 'block';
                        requestAnimationFrame(() => {
                            complaintForm.classList.add('show');
                        });
                        
                        // Pre-fill complaint field
                        document.getElementById('complaint').value = message;
                        
                        // Smooth scroll to form
                        complaintForm.scrollIntoView({ 
                            behavior: 'smooth',
                            block: 'start' 
                        });
                    }, 800);
                }
            } else {
                addMessage("I apologize, but I couldn't process your request. Could you please rephrase that?");
            }
        } catch (error) {
            console.error('Error:', error);
            loadingMessage.remove();
            addMessage("I apologize for the inconvenience. There seems to be a connection issue. Please try again.");
        } finally {
            // Re-enable input and button
            userInput.disabled = false;
            sendBtn.disabled = false;
            userInput.focus();
        }
    }

    sendBtn.addEventListener('click', handleUserInput);
    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleUserInput();
        }
    });

    // Image Upload Preview
    const imageUpload = document.getElementById('image-upload');
    const imagePreview = document.getElementById('image-preview');

    imageUpload.addEventListener('change', () => {
        const file = imageUpload.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function (e) {
                const img = document.createElement('img');
                img.src = e.target.result;
                imagePreview.innerHTML = '';
                imagePreview.appendChild(img);
            };
            reader.readAsDataURL(file);
        }
    });

    // Submit Complaint
    const submitBtn = document.getElementById('submit-complaint');
    const submissionResult = document.getElementById('submission-result');
    const ticketNumberElem = document.getElementById('ticket-number');
    const assignedDeptElem = document.getElementById('assigned-department');

    async function submitComplaint() {
        const name = document.getElementById('name').value.trim();
        const email = document.getElementById('email').value.trim();
        const phone = document.getElementById('phone').value.trim();
        const complaint = document.getElementById('complaint').value.trim();
        const address = document.getElementById('address').value.trim();

        // Remove image from required fields check
        if (!name || !email || !complaint || !address) {
            alert('Please fill all required fields');
            return;
        }

        let imageData = null;
        if (imageUpload.files[0]) {
            const reader = new FileReader();
            imageData = await new Promise(resolve => {
                reader.onload = e => resolve(e.target.result);
                reader.readAsDataURL(imageUpload.files[0]);
            });
        }
        // Image is now optional, so we continue with or without it
        const data = { name, email, phone, complaint, address, image: imageData };

        try {
            const response = await fetch("http://127.0.0.1:5000/api/submit_complaint", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data)
            });

            const result = await response.json();
            console.log(result) 

            if (result.success) {
                // Update the ticket number and department in the UI
                document.getElementById('ticket-number').textContent = result.ticket_number;
                document.getElementById('assigned-department').textContent = result.department;
                
                // Hide the complaint form and show the success message
                document.getElementById('complaint-form').style.display = 'none';
                document.getElementById('submission-result').style.display = 'block';
                
                // Clear the form but keep the submission result visible
                document.getElementById('name').value = '';
                document.getElementById('email').value = '';
                document.getElementById('phone').value = '';
                document.getElementById('complaint').value = '';
                document.getElementById('address').value = '';
                imageUpload.value = '';
                imagePreview.innerHTML = '';
            } else {
                alert(result.message || 'Failed to submit complaint');
            }
        } catch (error) {
            console.error('Error submitting complaint:', error);
            alert('An error occurred while submitting the complaint.');
        }
    }

    submitBtn.addEventListener('click', submitComplaint);

    document.getElementById('new-complaint').addEventListener('click', () => {
        // Hide the submission result
        document.getElementById('submission-result').style.display = 'none';
        
        // Clear the form
        document.getElementById('name').value = '';
        document.getElementById('email').value = '';
        document.getElementById('phone').value = '';
        document.getElementById('complaint').value = '';
        document.getElementById('address').value = '';
        imageUpload.value = '';
        imagePreview.innerHTML = '';
        
        // Show the chat interface
        document.getElementById('complaint-form').style.display = 'none';
        
        // Reset the chat with an informative message
        const chatMessages = document.getElementById('chat-messages');
        const previousTicket = document.getElementById('ticket-number').textContent;
        const previousDepartment = document.getElementById('assigned-department').textContent;
        
        chatMessages.innerHTML = `
            <div class="message bot">
                Great! Your previous grievance (Ticket: ${previousTicket}) has been successfully submitted and classified under ${previousDepartment} department. We'll keep you updated on its progress.
                <br><br>
                How else can I assist you today? Feel free to share any other grievance you have, and I'll help direct it to the appropriate department.
            </div>
        `;
        
        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    // Track Complaint
    const trackBtn = document.getElementById('track-btn');
    const complaintDetails = document.getElementById('complaint-details');
    const trackError = document.getElementById('track-error');

    trackBtn.addEventListener('click', async () => {
        const ticketNumber = document.getElementById('track-ticket').value.trim();

        if (!ticketNumber) {
            alert('Please enter a ticket number');
            return;
        }

        trackBtn.disabled = true;
        trackBtn.textContent = 'Tracking...';

        try {
            const response = await fetch("http://127.0.0.1:5000/api/track_complaint", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                mode: "cors",
                body: JSON.stringify({ ticket_number: ticketNumber })
            });

            const result = await response.json();

            if (result.success && result.complaint) {
                trackError.style.display = 'none';

                const complaint = result.complaint;
                const elements = {
                    'detail-ticket': complaint.ticket_number,
                    'detail-department': complaint.department,
                    'detail-description': complaint.description,
                    'detail-address': complaint.address,
                    'detail-status': complaint.status
                };

                // Update all elements safely
                Object.entries(elements).forEach(([id, value]) => {
                    const element = document.getElementById(id);
                    if (element) {
                        element.textContent = value || 'N/A';
                    }
                });

                // Update status element with class
                const statusElem = document.getElementById('detail-status');
                if (statusElem) {
                    statusElem.className = `detail-value status ${(complaint.status || '').replace(' ', '')}`;
                }

                // Update dates
                const createdDate = new Date(complaint.created_at);
                const updatedDate = new Date(complaint.updated_at);
                const dateElements = {
                    'detail-date': createdDate,
                    'detail-updated': updatedDate
                };

                Object.entries(dateElements).forEach(([id, date]) => {
                    const element = document.getElementById(id);
                    if (element) {
                        element.textContent = formatDate(date);
                    }
                });

                if (complaintDetails) {
                    complaintDetails.style.display = 'block';
                }
            } else {
                const errorMessage = document.getElementById('error-message');
                if (errorMessage) {
                    errorMessage.textContent = result.message || 'Ticket not found';
                }
                if (trackError) {
                    trackError.style.display = 'block';
                }
                if (complaintDetails) {
                    complaintDetails.style.display = 'none';
                }
            }
        } catch (error) {
            console.error('Error tracking complaint:', error);
            const errorMessage = document.getElementById('error-message');
            if (errorMessage) {
                errorMessage.textContent = 'An error occurred while tracking your complaint';
            }
            if (trackError) {
                trackError.style.display = 'block';
            }
            if (complaintDetails) {
                complaintDetails.style.display = 'none';
            }
        } finally {
            if (trackBtn) {
                trackBtn.disabled = false;
                trackBtn.textContent = 'Track';
            }
        }
    });

    function isValidEmail(email) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    }

    function formatDate(date) {
        return date.toLocaleString('en-US', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    }

    // Intersection Observer for animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Observe elements with animation classes
    document.querySelectorAll('.message, .form-group, .detail-row').forEach(el => {
        observer.observe(el);
    });

    // Add smooth scroll behavior
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            document.querySelector(this.getAttribute('href')).scrollIntoView({
                behavior: 'smooth'
            });
        });
    });

    // Add loading state to buttons
    document.querySelectorAll('.btn').forEach(button => {
        button.addEventListener('click', function() {
            if (!this.disabled) {
                this.classList.add('loading');
                setTimeout(() => {
                    this.classList.remove('loading');
                }, 2000);
            }
        });
    });
});
