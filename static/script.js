const messagesContainer = document.getElementById('messages');
const userInput = document.getElementById('user-input');
const sendButton = document.getElementById('send-button');
const microphoneButton = document.getElementById('microphone');

let isListening = false; // Flag to prevent multiple simultaneous recognition starts

function speak(text) {
    if ('speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(text);
        window.speechSynthesis.speak(utterance);
    } else {
        console.warn('Speech synthesis not supported in this browser.');
    }
}

async function fetchBotResponse(text) {
    try {
        const response = await fetch('/api/typed-input', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text }),
        });
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        return { response: 'Sorry, something went wrong.' };
    }
}

// Function to add a message to the chat
function addMessage(text, sender) {
    const messageElement = document.createElement('div');
    messageElement.classList.add('message', sender);
    messageElement.textContent = text;
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
    if (text) {
        addMessage(text, 'user'); // Show user message
        userInput.value = '';
        try {
            const response = await fetch('/api/typed-input', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ text })
            });
            const data = await response.json();
            const botResponse = data.response;
            addMessage(botResponse, 'bot'); // Show bot response
            // Trigger text-to-speech after displaying the text
            speak(botResponse);
        } catch (error) {
            console.error('Error:', error);
        }
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
    addMessage(text, 'user'); // Display the user's voice input
    fetch('/api/typed-input', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
    })
    .then(response => response.json())
    .then(data => {
        const botResponse = data.response;
        addMessage(botResponse, 'bot'); // Display bot response
        // Trigger text-to-speech after displaying the text
        speak(botResponse);
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
