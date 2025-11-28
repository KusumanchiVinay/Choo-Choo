const messagesContainer = document.getElementById('messages');
const userInput = document.getElementById('user-input');
const sendButton = document.getElementById('send-button');
const microphoneButton = document.getElementById('microphone');
const toggleHistoryBtn = document.getElementById('toggle-history-btn');
const chatHistory = document.querySelector('.chat-history');

let isListening = false;
let activeSessionId = null;
let currentUtterance = null;

function stopCurrentSpeech() {
    if ('speechSynthesis' in window && currentUtterance) {
        speechSynthesis.cancel();
        currentUtterance = null;
    }
}

function addMessage(text, sender, autoSpeak = false) {
    const messageElement = document.createElement('div');
    messageElement.classList.add('message', sender);
    messageElement.textContent = text;

    if (sender === 'bot') {
        const speakBtn = document.createElement('button');
        speakBtn.innerHTML = '🔊';
        speakBtn.classList.add('speak-btn');

        let isSpeaking = false;
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'en-US';
        utterance.rate = 1.0;

        speakBtn.onclick = () => {
            if (!isSpeaking) {
                stopCurrentSpeech();
                currentUtterance = utterance;
                speechSynthesis.speak(utterance);
                speakBtn.innerHTML = '🔇';
                isSpeaking = true;
            } else {
                stopCurrentSpeech();
                speakBtn.innerHTML = '🔊';
                isSpeaking = false;
            }
        };

        if (autoSpeak) {
            stopCurrentSpeech();
            currentUtterance = utterance;
            speechSynthesis.speak(utterance);
            speakBtn.innerHTML = '🔇';
            isSpeaking = true;
        }

        messageElement.appendChild(speakBtn);
    }

    messagesContainer.appendChild(messageElement);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

async function handleSend() {
    const text = userInput.value.trim();
    if (text && activeSessionId) {
        stopCurrentSpeech();
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
            
            if (!response.ok) {
                addMessage('Error: Could not process your request', 'bot');
                return;
            }
            
            const data = await response.json();
            addMessage(data.response, 'bot', true);

            if (data.updated_title) {
                updateChatTitle(data.updated_title);
                await fetchChatHistory();
            }
        } catch (error) {
            console.error('Error:', error);
            addMessage('Network error. Please try again.', 'bot');
        }
    }
}

function updateChatTitle(firstMessage) {
    const historyItems = document.querySelectorAll('#history-list li');
    if (historyItems.length > 0) {
        const title = firstMessage.length > 30 ? firstMessage.substring(0, 30) + '...' : firstMessage;
        historyItems[0].textContent = title;
    }
}

sendButton.addEventListener('click', handleSend);
userInput.addEventListener('keypress', (event) => {
    if (event.key === 'Enter') {
        handleSend();
    }
});

const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
recognition.continuous = false;
recognition.interimResults = false;
recognition.language = 'en-US';

recognition.onstart = () => {
    isListening = true;
    userInput.placeholder = 'Listening...';
    userInput.disabled = true;
    microphoneButton.innerHTML = '⏹';
};

recognition.onend = () => {
    isListening = false;
    userInput.placeholder = 'Type your message...';
    userInput.disabled = false;
    microphoneButton.innerHTML = '🎙';
};

recognition.onerror = (event) => {
    console.error('Speech recognition error:', event.error);
    addMessage(`Sorry, I couldn't understand. Error: ${event.error}`, 'bot');
};

recognition.onresult = (event) => {
    let interimTranscript = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
            userInput.value = transcript;
            handleSend();
        } else {
            interimTranscript += transcript;
        }
    }
    if (interimTranscript) {
        userInput.placeholder = `Interim: ${interimTranscript}`;
    }
};

microphoneButton.addEventListener('click', () => {
    if (!isListening) {
        recognition.start();
    } else {
        recognition.stop();
    }
});

async function fetchChatHistory() {
    try {
        const response = await fetch('/api/chat-history');
        if (!response.ok) return;
        
        const data = await response.json();
        const historyList = document.getElementById('history-list');
        
        if (historyList) {
            historyList.innerHTML = '';
            data.chat_history.forEach(chat => {
                const li = document.createElement('li');
                li.textContent = chat.title;
                li.dataset.sessionId = chat.chat_session_id;
                li.onclick = () => loadChat(chat.chat_session_id);
                historyList.appendChild(li);
            });
        }
    } catch (error) {
        console.error('Error fetching chat history:', error);
    }
}

async function loadChat(sessionId) {
    activeSessionId = sessionId;
    messagesContainer.innerHTML = '';
    
    try {
        const response = await fetch(`/api/get-chat/${sessionId}`);
        if (!response.ok) return;
        
        const chatSession = await response.json();
        chatSession.messages.forEach(msg => {
            addMessage(msg.user.text, 'user');
            addMessage(msg.bot.text, 'bot');
        });
        
        document.querySelectorAll('#history-list li').forEach(li => {
            li.classList.remove('active');
            if (li.dataset.sessionId === sessionId) {
                li.classList.add('active');
            }
        });
    } catch (error) {
        console.error('Error loading chat:', error);
    }
}

async function createNewChat() {
    try {
        const response = await fetch('/api/new-session', { method: 'POST' });
        if (!response.ok) return;
        
        const data = await response.json();
        activeSessionId = data.chat_session_id;
        messagesContainer.innerHTML = '';
        await fetchChatHistory();
    } catch (error) {
        console.error('Error creating new chat:', error);
    }
}

toggleHistoryBtn.addEventListener('click', () => {
    chatHistory.style.display = chatHistory.style.display === 'none' ? 'block' : 'none';
});

document.addEventListener('DOMContentLoaded', async () => {
    try {
        const emailResponse = await fetch('/api/get-email');
        if (emailResponse.ok) {
            const { email } = await emailResponse.json();
            if (email === 'Guest') {
                return;
            }
        }
    } catch (error) {
        console.error('Error checking email:', error);
    }
    
    await fetchChatHistory();
    await createNewChat();
});
