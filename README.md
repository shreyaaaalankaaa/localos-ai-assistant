# LocalOS AI Assistant

A desktop AI assistant that runs local large language models through Ollama and provides conversational assistance, productivity tools, and system automation through a modern desktop interface.

The project combines React, FastAPI, and local LLM inference to create an extensible assistant capable of interacting with files, applications, and user workflows while keeping inference on the local machine.

---

## Features

- Local LLM inference using Ollama
- Multiple interaction modes (Chat, Reasoning, Coding)
- Voice input and text-to-speech
- Persistent conversation history
- Local memory management
- File search and document interaction
- Application and website launcher
- Notes and reminders
- Dark desktop-inspired interface
- Cross-platform desktop support

---

## Tech Stack

### Frontend

- React
- TypeScript
- Vite
- Tailwind CSS
- Framer Motion

### Backend

- FastAPI
- Python
- Ollama

### AI

- Qwen
- DeepSeek
- Llama
- LangChain

### Storage

- Local JSON storage
- File-based memory

---

## Project Structure

```
localos-ai-assistant/
│
├── frontend/
├── backend/
├── public/
├── assets/
├── models/
├── docs/
└── README.md
```

---

## Installation

Clone the repository.

```bash
git clone https://github.com/<username>/localos-ai-assistant.git
```

Navigate to the project.

```bash
cd localos-ai-assistant
```

Install frontend dependencies.

```bash
npm install
```

Install backend dependencies.

```bash
pip install -r requirements.txt
```

Start Ollama.

```bash
ollama serve
```

Run the frontend.

```bash
npm run dev
```

Run the backend.

```bash
uvicorn main:app --reload
```

---

## Supported Models

- qwen3
- qwen2.5-coder
- deepseek-r1
- llama3.2

Models can be switched depending on the selected interaction mode.

---

## Future Improvements

- Retrieval-Augmented Generation (RAG)
- Plugin architecture
- Calendar and email integrations
- Local vector database
- Multi-agent workflows
- Cross-device synchronization

---

## Author

**Shreya Lanka**

Cybersecurity Undergraduate

Interested in AI, Software Engineering, Cybersecurity, and Full-Stack Development.

LinkedIn: <www.linkedin.com/in/shreya-lanka-057a0b28a>

GitHub: <https://github.com/shreyaaaalankaaa>
