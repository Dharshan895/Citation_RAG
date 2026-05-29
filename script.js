/* =========================
   ACTIVE SESSION + STORAGE
========================= */

let activeSessionId = null;

let sessions = [];


/* =========================
   SEND MESSAGE
========================= */

async function sendMessage() {

    let input = document.getElementById("message");

    let message = input.value.trim();

    if (!message) return;

    // Check active session
    if (!activeSessionId) {

        alert("Please upload a PDF first.");

        return;
    }

    // Add User Message to UI
    addMessage(message, "user");

    // Store User Message
    let currentSession = sessions.find(

        s => s.session_id === activeSessionId
    );

    currentSession.messages.push({

        text: message,

        type: "user"
    });

    // Clear Input
    input.value = "";

    // Typing Indicator
    let typingDiv = addMessage("Typing...", "bot");

    try {

        let res = await fetch("/chat", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({

                session_id: activeSessionId,

                message: message
            })
        });

        let data = await res.json();

        // Remove Typing
        typingDiv.remove();

        // Add Bot Message to UI
        addMessage(data.reply, "bot");

        // Store Bot Message
        currentSession.messages.push({

            text: data.reply,

            type: "bot"
        });

    } catch (error) {

        typingDiv.remove();

        addMessage("Something went wrong.", "bot");

        console.error(error);
    }
}


/* =========================
   ADD MESSAGE
========================= */

/* =========================
   ADD MESSAGE
========================= */

function addMessage(text, type) {

    let chatBox = document.getElementById("chat-box");

    // Main Wrapper
    let wrapper = document.createElement("div");

    wrapper.className = `message-wrapper ${type}`;

    // Bubble
    let bubble = document.createElement("div");

    bubble.className = `message-box ${type}`;

    bubble.textContent = text;

    wrapper.appendChild(bubble);

    chatBox.appendChild(wrapper);

    // Auto Scroll
    chatBox.scrollTop = chatBox.scrollHeight;

    return wrapper;
}


/* =========================
   UPLOAD PDF
========================= */

function uploadFile() {

    let input = document.getElementById("fileInput");

    input.click();

    input.onchange = async () => {

        let file = input.files[0];

        if (!file) return;

        let formData = new FormData();

        formData.append("file", file);

        try {

            let res = await fetch("/upload", {

                method: "POST",

                body: formData
            });

            let data = await res.json();

            // Active Session
            activeSessionId = data.session_id;

            // Create New Session
            sessions.push({

                session_id: data.session_id,

                title: file.name,

                messages: []
            });

            // Render Sidebar
            renderHistory();

            // Disable Upload
            document.getElementById("upload-btn").disabled = true;

            // Enable Input
            document.getElementById("message").disabled = false;

            // Clear UI
            document.getElementById("chat-box").innerHTML = "";

            // Welcome Message
            addMessage(

                "PDF uploaded successfully. Ask anything about the PDF.",

                "bot"
            );

        } catch (error) {

            alert("Upload Failed!");

            console.error(error);
        }
    };
}


/* =========================
   RENDER SIDEBAR HISTORY
========================= */

function renderHistory() {

    let sidebar = document.getElementById("history");

    sidebar.innerHTML = "";

    sessions.forEach((session) => {

        let div = document.createElement("div");

        div.classList.add("history-item");

        div.innerText = session.title;

        // Active Highlight
        if (session.session_id === activeSessionId) {

            div.style.background = "#2563eb";
        }

        // Session Switching
        div.onclick = () => {

            activeSessionId = session.session_id;

            // Re-render sidebar
            renderHistory();

            // Clear Current UI
            document.getElementById("chat-box").innerHTML = "";

            // Restore Old Messages
            session.messages.forEach((msg) => {

                addMessage(msg.text, msg.type);
            });

            // Enable Input
            document.getElementById("message").disabled = false;

            // Disable Upload
            document.getElementById("upload-btn").disabled = true;
        };

        sidebar.appendChild(div);
    });
}


/* =========================
   NEW CHAT
========================= */

function newChat() {

    // Reset Active Session
    activeSessionId = null;

    // Clear UI
    document.getElementById("chat-box").innerHTML = "";

    document.getElementById("message").value = "";

    // Enable Upload
    document.getElementById("upload-btn").disabled = false;

    // Disable Message Input
    document.getElementById("message").disabled = true;

    // Remove Active Highlight
    renderHistory();

    addMessage(

        "Upload a PDF to start chatting.",

        "bot"
    );
}


/* =========================
   TOGGLE SIDEBAR
========================= */

function toggleSidebar() {

    document
        .getElementById("sidebar")
        .classList.toggle("hidden");
}


/* =========================
   ENTER KEY SEND
========================= */

document
    .getElementById("message")
    .addEventListener(

        "keypress",

        function(event) {

            if (event.key === "Enter") {

                sendMessage();
            }
        }
);


/* =========================
   INITIAL MESSAGE
========================= */

window.onload = () => {

    addMessage(

        "Upload a PDF to start chatting.",

        "bot"
    );
};