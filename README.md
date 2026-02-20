# 🎬 Vibe Studio v2.0

**AI-Powered Video Creator & Editor** — A full-stack application for creating short-form videos with AI assistance, real MP4 export, and Claude Desktop integration.

---

## ✨ Features

### 🎥 Video Creation
- **8 Video Categories**: Motivational, Travel, Food, Fitness, Corporate, Celebration, **Religious**, Chill
- **8 Audio Vibes**: Energetic, Chill, Cinematic, Romantic, **Religious/Nasheeds**, Corporate, Travel, Custom
- Upload photos, videos, and audio → get a polished MP4
- Ken Burns effect on images, color grading per category
- Portrait (9:16), Landscape (16:9), or Square (1:1) output

### ✂️ Built-in Editor
- **Trim** video clips with precise start/end controls
- **Reorder** media by drag-and-drop
- **Add captions** per slide
- **Delete** unwanted items
- Real-time preview of uploaded media

### 🤖 AI Chatbot
- Built-in AI assistant for prompt-based video creation
- Say *"I want a religious video with nasheeds"* and it configures everything
- Works with Anthropic API key for smart responses
- Falls back to intelligent templates without API key

### 📡 MCP Server (Claude Desktop)
- Connect Claude Desktop to Vibe Studio
- Create and manage video projects from Claude chat
- Generate videos, trim clips, update captions — all via prompts

### 🎬 Real MP4 Export
- Uses **FFmpeg** for actual video encoding (not browser-based!)
- Concatenates segments, applies filters, merges audio
- Download the finished MP4 directly

---

## 🚀 Quick Start

### Prerequisites

1. **Python 3.10+**
2. **FFmpeg** (required for video generation)

   ```bash
   # Mac
   brew install ffmpeg

   # Ubuntu/Debian
   sudo apt install ffmpeg

   # Windows (using Chocolatey)
   choco install ffmpeg
   ```

### Installation

```bash
cd vibe-studio
pip install -r requirements.txt
python app.py
```

Open **http://localhost:8000** in your browser. That's it.

Open **http://localhost:8000** in your browser.

### Optional: AI Chatbot

Set your Anthropic API key for intelligent AI chat responses:

```bash
export ANTHROPIC_API_KEY=sk-ant-your-key-here
python app.py
```

Without the key, the chatbot uses smart template-based responses (still works great!).

---

## 📡 MCP Server Setup (Claude Desktop)

This lets you control Vibe Studio from Claude Desktop via natural language.

### 1. Start both servers

```bash
# Terminal 1: Start Vibe Studio
python app.py

# Terminal 2: Start MCP server
python mcp/server.py
```

### 2. Configure Claude Desktop

Edit your Claude Desktop config file:

- **Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Add:

```json
{
  "mcpServers": {
    "vibe-studio": {
      "command": "python",
      "args": ["/full/path/to/vibe-studio/mcp/server.py"]
    }
  }
}
```

### 3. Use it!

In Claude Desktop, you can now say things like:

- *"Create a religious video project with nasheed audio"*
- *"Check if Vibe Studio is running"*
- *"Generate the video for my project"*
- *"List all available categories and audio vibes"*
- *"Trim the first video clip from 5 to 15 seconds"*

### Available MCP Tools

| Tool | Description |
|------|-------------|
| `vibe_create_project` | Create a new project with category & audio vibe |
| `vibe_get_project` | Get project details |
| `vibe_update_project` | Update category, audio, duration |
| `vibe_generate_video` | Generate the final MP4 |
| `vibe_list_categories` | List all categories & audio vibes |
| `vibe_status` | Check server health & FFmpeg status |
| `vibe_trim_video` | Trim a video clip |
| `vibe_update_caption` | Update caption for a media item |
| `vibe_reorder_media` | Reorder the media timeline |

---

## 🗂️ Project Structure

```
vibe-studio/
├── app.py                 # FastAPI backend (main server)
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── templates/
│   └── index.html        # Full UI (editor, chat, upload, preview)
├── static/
│   ├── uploads/          # Uploaded media (per project)
│   └── outputs/          # Generated MP4 files
└── mcp/
    └── server.py         # MCP server for Claude Desktop
```

---

## 📖 How It Works

### Video Generation Pipeline

1. **Upload** → Photos & videos stored in project folder
2. **Configure** → Pick category (color grading), audio vibe, duration
3. **Edit** → Trim videos, reorder slides, add captions
4. **Generate** → FFmpeg processes each item:
   - Images → Ken Burns pan/zoom effect → video segment
   - Videos → Trim + scale + color filter → segment
   - All segments → Concatenated → Audio merged → Final MP4

### Categories & Their Looks

| Category | Effect |
|----------|--------|
| 💪 Motivational | High brightness, saturated colors |
| ✈️ Travel | Enhanced saturation, warm tones |
| 🍕 Food | Warm, appetizing color grading |
| 🏋️ Fitness | High contrast, vivid |
| 🏢 Corporate | Subtle, professional look |
| 🎉 Celebration | Bright, vibrant, festive |
| 🕌 Religious | Soft, warm golden tones, gentle |
| 😎 Chill | Muted, relaxed color palette |

---

## 🔧 API Reference

All endpoints are available at `http://localhost:8000/api/`:

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/project/create` | Create project |
| GET | `/api/project/{id}` | Get project |
| PUT | `/api/project/{id}` | Update project |
| POST | `/api/project/{id}/upload` | Upload media files |
| DELETE | `/api/project/{id}/media/{mid}` | Remove media |
| PUT | `/api/project/{id}/media/{mid}` | Update media item |
| PUT | `/api/project/{id}/reorder` | Reorder media |
| POST | `/api/project/{id}/trim/{mid}` | Trim video |
| POST | `/api/project/{id}/generate` | Generate MP4 |
| GET | `/api/download/{filename}` | Download video |
| POST | `/api/chat` | AI chatbot |
| GET | `/api/categories` | List categories |
| GET | `/api/audio-vibes` | List audio vibes |
| GET | `/api/status` | Server status |

---

## 🌐 Deployment

### Local Network

```bash
python app.py  # Accessible at http://your-ip:8000
```

### Cloud Server (e.g., Ubuntu VPS)

```bash
# Install FFmpeg
sudo apt update && sudo apt install ffmpeg

# Install Python deps
pip install -r requirements.txt

# Run with production settings
PORT=80 python app.py
```

### Docker (create your own Dockerfile)

```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y ffmpeg
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8000
CMD ["python", "app.py"]
```

---

## 📝 License

MIT — Use freely, modify, deploy.
