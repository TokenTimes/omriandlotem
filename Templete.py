HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>SatoshiGPT</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/tailwindcss/2.2.19/tailwind.min.css" rel="stylesheet">
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #1a202c;
            color: #edf2f7;
            display: flex;
            height: 100vh;
            margin: 0;
            overflow: hidden;
        }
        .sidebar {
            width: 300px;
            background: #2d3748;
            display: flex;
            flex-direction: column;
            border-right: 1px solid #4a5568;
            padding: 10px;
            transition: transform 0.3s ease-in-out;
            position: fixed;
            left: 0;
            top: 0;
            bottom: 0;
            z-index: 1000;
        }
        .sidebar.hidden {
            transform: translateX(-100%);
        }
        .chat-container {
            flex-grow: 1;
            margin-left: 300px;
            background: #2d3748;
            display: flex;
            flex-direction: column;
            height: 100%;
            transition: margin-left 0.3s ease-in-out;
        }
        .chat-container.expanded {
            margin-left: 0;
        }
        .messages {
            flex-grow: 1;
            overflow-y: auto;
            padding: 20px;
        }
        .message {
            margin-bottom: 15px;
            display: flex;
        }
        .message.user {
            justify-content: flex-end;
        }
        .message.bot {
            justify-content: flex-start;
        }
        .bubble {
            max-width: 70%;
            padding: 10px 15px;
            border-radius: 15px;
        }
        .bubble.user {
            background: #3182ce;
            color: #fff;
        }
        .bubble.bot {
            background: #4a5568;
            color: #edf2f7;
        }
        .input-container {
            padding: 10px;
            background: #2d3748;
            display: flex;
        }
        .input-container input {
            flex-grow: 1;
            padding: 10px;
            border: none;
            border-radius: 5px;
            margin-right: 10px;
            background: #4a5568;
            color: #fff;
        }
        .input-container button {
            padding: 10px 15px;
            background: #3182ce;
            border: none;
            border-radius: 5px;
            color: #fff;
            cursor: pointer;
        }
        .input-container button:hover {
            background: #2b6cb0;
        }
        .sidebar ul {
            list-style-type: none;
            padding: 0;
        }
        .sidebar li {
            padding: 10px;
            margin: 5px 0;
            background: #4a5568;
            border-radius: 5px;
            cursor: pointer;
            color: #fff;
            text-align: center;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .sidebar li:hover {
            background: #3182ce;
        }
        .sidebar li button {
            background: transparent;
            border: none;
            color: #fff;
            cursor: pointer;
        }
        .sidebar li button:hover {
            color: #ff4d4d;
        }
        .toggle-button {
            position: absolute;
            top: 10px;
            left: 10px;
            background: #3182ce;
            color: white;
            border: none;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            z-index: 1100;
        }
        .toggle-button:hover {
            background: #2b6cb0;
        }
    </style>
</head>
<body>
    <button class="toggle-button" onclick="toggleSidebar()">☰</button>
    <div class="sidebar hidden" id="sidebar">
        <h2 style="margin-top: 10px;">Conversations</h2>
        <ul id="conversations-list"></ul>
        <button onclick="createNewConversation()" style="margin-top: 10px; background: #3182ce; color: white; padding: 10px; border: none; border-radius: 5px; cursor: pointer;">New Conversation</button>
    </div>
    <div class="chat-container" id="chat-container">
        <div id="messages" class="messages"></div>
        <div class="input-container">
            <input id="message-input" type="text" placeholder="Type a message..." onkeypress="handleKeyPress(event)"/>
            <button onclick="sendMessage()">Send</button>
        </div>
    </div>

    <script>
        let currentConversationId = null;
        let sidebarVisible = true;

        function toggleSidebar() {
            const sidebar = document.getElementById('sidebar');
            const chatContainer = document.getElementById('chat-container');
            sidebarVisible = !sidebarVisible;
            sidebar.classList.toggle('hidden', !sidebarVisible);
            chatContainer.classList.toggle('expanded', !sidebarVisible);
        }

        async function fetchConversations() {
            const response = await fetch('/api/conversations');
            const data = await response.json();
            const list = document.getElementById('conversations-list');
            list.innerHTML = '';
            data.conversations.forEach(id => {
                const item = document.createElement('li');
                const text = document.createElement('span');
                text.textContent = `Conversation ${id}`;
                text.style.flex = '1';
                text.onclick = () => loadConversation(id);
                
                const deleteButton = document.createElement('button');
                deleteButton.textContent = '✖';
                deleteButton.onclick = (e) => {
                    e.stopPropagation();
                    deleteConversation(id);
                };

                item.appendChild(text);
                item.appendChild(deleteButton);
                list.appendChild(item);
            });
        }

        async function createNewConversation() {
            const response = await fetch('/api/conversations', { method: 'POST' });
            const data = await response.json();
            currentConversationId = data.conversation_id;
            fetchConversations();
            loadConversation(currentConversationId);
        }

        async function deleteConversation(id) {
            const response = await fetch(`/api/conversations/${id}`, { method: 'DELETE' });
            if (response.ok) {
                if (currentConversationId === id) {
                    currentConversationId = null;
                }
                fetchConversations();
                const messagesDiv = document.getElementById('messages');
                messagesDiv.innerHTML = '';
            } else {
                alert('Failed to delete conversation.');
            }
        }

        async function loadConversation(id) {
            currentConversationId = id;
            const response = await fetch(`/api/conversations/${id}`);
            const data = await response.json();
            const messagesDiv = document.getElementById('messages');
            messagesDiv.innerHTML = '';
            data.messages.forEach(msg => addMessage(msg.role, msg.content));
        }

async function sendMessage() {
    const input = document.getElementById('message-input');
    const message = input.value.trim();
    if (!message) return;

    addMessage('user', message);
    input.value = '';

    const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message })
    });

    const data = await response.json();
    addMessage('bot', data.response);
}

        function addMessage(sender, content) {
            const messagesDiv = document.getElementById('messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender}`;

            const bubble = document.createElement('div');
            bubble.className = `bubble ${sender}`;
            bubble.textContent = content;

            messageDiv.appendChild(bubble);
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        function handleKeyPress(event) {
            if (event.key === 'Enter') sendMessage();
        }

        window.onload = async function () {
            const response = await fetch('/api/conversations');
            const data = await response.json();
            if (data.conversations.length === 0) {
                await createNewConversation();
            } else {
                currentConversationId = data.conversations[0];
                loadConversation(currentConversationId);
            }
        };

        fetchConversations();
    </script>
</body>
</html>
'''
