const messagesContainer = document.getElementById('messages');
const userInput = document.getElementById('user-input');
const sendButton = document.getElementById('send-button');
const microphoneButton = document.getElementById('microphone');

let isListening = false; // Flag to prevent multiple simultaneous recognition starts
let activeSessionId = null; // To track the current active session
let currentUtterance = null; // Store the current speech instance

// Function to stop ongoing speech
function stopCurrentSpeech() {
    if ('speechSynthesis' in window && currentUtterance) {
        speechSynthesis.cancel(); // Stop any previous speech
        currentUtterance = null;
    }
}

// Function to add a message to the chat
function addMessage(text, sender, autoSpeak = false) {
    const messageElement = document.createElement('div');
    messageElement.classList.add('message', sender);
    messageElement.textContent = text;

    if (sender === 'bot') {
        // Create Speak/Mute button
        const speakBtn = document.createElement('button');
        speakBtn.innerHTML = '🔊'; // Initial state: Speak
        speakBtn.classList.add('speak-btn');

        let isSpeaking = false;
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'en-US';
        utterance.rate = 1.0;

        speakBtn.onclick = () => {
            if (!isSpeaking) {
                stopCurrentSpeech(); // Stop any ongoing speech
                currentUtterance = utterance;
                speechSynthesis.speak(utterance);
                speakBtn.innerHTML = '🔇'; // Change to Mute
                isSpeaking = true;
            } else {
                stopCurrentSpeech(); // Stop current speech
                speakBtn.innerHTML = '🔊'; // Change back to Speak
                isSpeaking = false;
            }
        };

        // Auto-speak only for new messages if specified
        if (autoSpeak) {
            stopCurrentSpeech(); // Stop any ongoing speech
            currentUtterance = utterance;
            speechSynthesis.speak(utterance);
            speakBtn.innerHTML = '🔇'; // Change to Mute
            isSpeaking = true;
        }

        messageElement.appendChild(speakBtn);
    }

    messagesContainer.appendChild(messageElement);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Function to display "Listening..." in the input field
function showListeningPlaceholder() {
    userInput.placeholder = 'Listening...';
    userInput.disabled = true; // Disable input while listening
}

// Function to restore the input field's original placeholder
function restoreInputPlaceholder() {
    userInput.placeholder = 'Type your message...';
    userInput.disabled = false; // Re-enable input after listening
}

// Function to handle sending user input
async function handleSend() {
    const text = userInput.value.trim();
    if (text && activeSessionId) {
        stopCurrentSpeech(); // Stop any ongoing speech before adding new message
        addMessage(text, 'user');
        userInput.value = '';
        try {
            const response = await fetch('/api/typed-input', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ text, sessionId: activeSessionId })
            });
            const data = await response.json();
            addMessage(data.response, 'bot', true); // Auto-speak for new bot response

            // Update title if it's the first message
            if (data.updated_title) {
                updateChatTitle(data.updated_title);
                await fetchChatHistory();
            }
        } catch (error) {
            console.error('Error:', error);
        }
    }
}

// Function to update the chat title dynamically in UI
function updateChatTitle(firstMessage) {
    const historyItems = document.querySelectorAll('#history-list li');
    if (historyItems.length > 0 && historyItems[0].textContent === 'New Chat') {
        historyItems[0].textContent = firstMessage.length > 20 ? firstMessage.substring(0, 20) + '...' : firstMessage;
    }
}

// Event listener for the "Send" button
sendButton.addEventListener('click', handleSend);

// Event listener for the "Enter" key
userInput.addEventListener('keypress', (event) => {
    if (event.key === 'Enter') {
        handleSend();
    }
});

// Voice recognition setup
const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
recognition.lang = 'en-US';
recognition.interimResults = false;

// Update to handle microphone button click with "Listening..." message
microphoneButton.addEventListener('click', () => {
    if (isListening) {
        console.log('Already listening...');
        return; // Ignore additional clicks if already listening
    }
    isListening = true; // Set flag to true
    showListeningPlaceholder(); // Show "Listening..." in the input field
    recognition.start();
});

recognition.addEventListener('result', (event) => {
    const text = event.results[0][0].transcript;
    stopCurrentSpeech(); // Stop any ongoing speech
    addMessage(text, 'user'); // Display the user's voice input
    fetch('/api/typed-input', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, sessionId: activeSessionId })
    })
    .then(response => response.json())
    .then(data => {
        addMessage(data.response, 'bot', true); // Auto-speak for new bot response
        // Update title if it's the first message
        if (data.updated_title) {
            updateChatTitle(data.updated_title);
            fetchChatHistory();
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
});

recognition.addEventListener('end', () => {
    console.log('Voice recognition ended');
    restoreInputPlaceholder(); // Restore the input field's placeholder
    isListening = false; // Reset the flag to allow new recognition
});

// Function to clear stored session when a user logs in
function clearStoredSession() {
    localStorage.removeItem('lastChatSessionId'); // Remove old session ID
    localStorage.removeItem('chatHistory'); // Remove old messages
}

// Call clearStoredSession when login page loads
if (window.location.pathname === "/login") {
    clearStoredSession();
}

// Function to save messages to local storage
function saveChatToLocal() {
    const messages = document.getElementById('messages').innerHTML;
    localStorage.setItem('chatHistory', messages);
}

// Function to load messages from local storage
function loadChatFromLocal() {
    const savedMessages = localStorage.getItem('chatHistory');
    if (savedMessages) {
        document.getElementById('messages').innerHTML = savedMessages;
    }
}

// Function to save the last viewed chat session ID in localStorage
function saveLastSession(sessionId) {
    localStorage.setItem('lastChatSessionId', sessionId);
}

// Function to get the last viewed chat session ID from localStorage
function getLastSession() {
    return localStorage.getItem('lastChatSessionId');
}

// Function to load chat session from server
async function loadChatSession(sessionId) {
    try {
        const response = await fetch(`/api/get-chat/${sessionId}`);
        const data = await response.json();
        if (data.error) {
            console.error(data.error);
            return;
        }
        activeSessionId = sessionId;
        messagesContainer.innerHTML = "";
        data.messages.forEach(entry => {
            addMessage(entry.user.text, 'user');
            addMessage(entry.bot.text, 'bot'); // No auto-speak for loaded messages
        });
        highlightActiveSession();
    } catch (error) {
        console.error('Error loading chat session:', error);
    }
}

// Highlight the active session in the UI
function highlightActiveSession() {
    document.querySelectorAll('#history-list li').forEach(li => {
        li.classList.remove('active');
        if (li.dataset.sessionId === activeSessionId) {
            li.classList.add('active');
        }
    });
}

// Restore the last viewed chat session when the page reloads
window.addEventListener('load', async () => {
    try {
        const response = await fetch('/api/get-current-session');
        const data = await response.json();
        let sessionId = getLastSession() || data.chat_session_id; // Retrieve last session

        if (sessionId) {
            await loadChatSession(sessionId);
        }
    } catch (error) {
        console.error('Error fetching current session:', error);
    }
});

async function createNewChat() {
    try {
        const response = await fetch('/api/new-session', { method: 'POST' });
        const data = await response.json();
        if (data.chat_session_id) {
            // 1) Re-fetch chat history to update the sidebar
            await fetchChatHistory();
            // 2) Auto-load the new session
            loadChatSession(data.chat_session_id);
        }
    } catch (error) {
        console.error('Error creating new session:', error);
    }
}

// After fetching chat history:
fetch('/api/get-current-session')
    .then(response => response.json())
    .then(data => {
        const currentSessionId = data.chat_session_id;
        if (currentSessionId) {
            loadChatSession(currentSessionId);
        }
    })
    .catch(error => console.error('Error fetching current session:', error));

// Function to fetch and render chat history
async function fetchChatHistory() {
    try {
        const response = await fetch('/api/chat-history');
        const data = await response.json();
        const historyList = document.getElementById('history-list');
        historyList.innerHTML = "";

        data.chat_history.forEach(chat => {
            const listItem = document.createElement('li');
            listItem.textContent = chat.title;
            listItem.dataset.sessionId = chat.chat_session_id;
            listItem.classList.add('chat-item');

            // Highlight active session
            if (chat.chat_session_id === activeSessionId) {
                listItem.classList.add('active');
            }

            // Load chat session on click
            listItem.addEventListener('click', () => {
                activeSessionId = chat.chat_session_id;
                loadChatSession(activeSessionId);
                highlightActiveSession();
            });

            // Create and bind delete button
            const deleteButton = document.createElement('button');
            deleteButton.textContent = '❌';
            deleteButton.classList.add('delete-chat');
            deleteButton.addEventListener('click', async (event) => {
                event.stopPropagation(); // Prevent triggering chat load
                await deleteChatSession(chat.chat_session_id);
            });

            listItem.appendChild(deleteButton);
            historyList.appendChild(listItem);
        });
    } catch (error) {
        console.error("Error fetching chat history:", error);
    }
}

// Function to delete chat session
async function deleteChatSession(sessionId) {
    try {
        const response = await fetch(`/api/delete-chat/${sessionId}`, {
            method: 'DELETE'
        });
        const data = await response.json();
        if (data.success) {
            await fetchChatHistory(); // Refresh chat history after deletion
        } else {
            console.error("Error deleting chat:", data.error);
        }
    } catch (error) {
        console.error("Error deleting chat session:", error);
    }
}

document.addEventListener('DOMContentLoaded', function () {
    fetchChatHistory();
});