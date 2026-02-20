"""
Vibe Studio MCP Server
═══════════════════════
Connect Claude Desktop to Vibe Studio so you can create videos
by chatting with Claude from your desktop.

Setup:
  1. Start Vibe Studio:  python app.py
  2. Start MCP server:   python mcp/server.py
  3. Add to Claude Desktop config (see below)

Claude Desktop config (~/.claude/claude_desktop_config.json):
{
  "mcpServers": {
    "vibe-studio": {
      "command": "python",
      "args": ["/path/to/vibe-studio/mcp/server.py"]
    }
  }
}
"""

import json
import sys
import os
import asyncio

# Add parent dir to path so we can reference the app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

VIBE_STUDIO_URL = os.environ.get("VIBE_STUDIO_URL", "http://localhost:8000")

try:
    import httpx
except ImportError:
    print("Install httpx: pip install httpx")
    sys.exit(1)


# ── MCP Protocol (simplified stdio-based) ─────────────────────────────────────
# This implements the MCP protocol over stdio for Claude Desktop

def send_response(id, result):
    """Send a JSON-RPC response to stdout."""
    msg = json.dumps({"jsonrpc": "2.0", "id": id, "result": result})
    sys.stdout.write(f"Content-Length: {len(msg)}\r\n\r\n{msg}")
    sys.stdout.flush()

def send_error(id, code, message):
    msg = json.dumps({"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}})
    sys.stdout.write(f"Content-Length: {len(msg)}\r\n\r\n{msg}")
    sys.stdout.flush()


TOOLS = [
    {
        "name": "vibe_create_project",
        "description": "Create a new video project in Vibe Studio. Returns a project ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["motivational", "travel", "food", "fitness", "corporate", "celebration", "religious", "chill"],
                    "description": "Video category/vibe"
                },
                "audio_vibe": {
                    "type": "string",
                    "enum": ["energetic", "chill", "cinematic", "romantic", "religious", "corporate", "travel", "custom"],
                    "description": "Audio mood"
                },
                "duration": {
                    "type": "integer",
                    "description": "Target video duration in seconds",
                    "default": 30
                }
            },
            "required": ["category"]
        }
    },
    {
        "name": "vibe_get_project",
        "description": "Get details of an existing Vibe Studio project.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "Project ID"}
            },
            "required": ["project_id"]
        }
    },
    {
        "name": "vibe_update_project",
        "description": "Update project settings (category, audio vibe, duration).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "category": {"type": "string"},
                "audio_vibe": {"type": "string"},
                "target_duration": {"type": "integer"}
            },
            "required": ["project_id"]
        }
    },
    {
        "name": "vibe_generate_video",
        "description": "Generate the final MP4 video from the project's media files using FFmpeg. Returns a download URL.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "Project ID"},
                "duration": {"type": "integer", "description": "Duration in seconds"},
                "width": {"type": "integer", "default": 1080},
                "height": {"type": "integer", "default": 1920},
            },
            "required": ["project_id"]
        }
    },
    {
        "name": "vibe_list_categories",
        "description": "List all available video categories and audio vibes.",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "vibe_status",
        "description": "Check Vibe Studio server status (is it running? is FFmpeg available?).",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "vibe_trim_video",
        "description": "Trim a video clip in a project.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "media_id": {"type": "string"},
                "start": {"type": "number", "description": "Start time in seconds"},
                "end": {"type": "number", "description": "End time in seconds"}
            },
            "required": ["project_id", "media_id"]
        }
    },
    {
        "name": "vibe_update_caption",
        "description": "Update caption for a media item.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "media_id": {"type": "string"},
                "caption": {"type": "string"}
            },
            "required": ["project_id", "media_id", "caption"]
        }
    },
    {
        "name": "vibe_reorder_media",
        "description": "Reorder media items in a project.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "order": {"type": "array", "items": {"type": "string"}, "description": "Ordered list of media IDs"}
            },
            "required": ["project_id", "order"]
        }
    },
]


async def handle_tool_call(name, arguments):
    """Execute a tool call against the Vibe Studio API."""
    async with httpx.AsyncClient(base_url=VIBE_STUDIO_URL, timeout=120) as client:
        try:
            if name == "vibe_create_project":
                r = await client.post("/api/project/create", data={
                    "category": arguments.get("category", "motivational"),
                    "audio_vibe": arguments.get("audio_vibe", "energetic"),
                    "duration": arguments.get("duration", 30),
                })
                return r.json()

            elif name == "vibe_get_project":
                r = await client.get(f"/api/project/{arguments['project_id']}")
                return r.json()

            elif name == "vibe_update_project":
                pid = arguments.pop("project_id")
                r = await client.put(f"/api/project/{pid}", json=arguments)
                return r.json()

            elif name == "vibe_generate_video":
                pid = arguments.pop("project_id")
                r = await client.post(f"/api/project/{pid}/generate", json=arguments)
                data = r.json()
                if "download_url" in data:
                    data["full_download_url"] = f"{VIBE_STUDIO_URL}{data['download_url']}"
                return data

            elif name == "vibe_list_categories":
                cats = (await client.get("/api/categories")).json()
                vibes = (await client.get("/api/audio-vibes")).json()
                return {"categories": cats, "audio_vibes": vibes}

            elif name == "vibe_status":
                r = await client.get("/api/status")
                return r.json()

            elif name == "vibe_trim_video":
                pid = arguments["project_id"]
                mid = arguments["media_id"]
                r = await client.post(f"/api/project/{pid}/trim/{mid}", json={
                    "start": arguments.get("start", 0),
                    "end": arguments.get("end"),
                })
                return r.json()

            elif name == "vibe_update_caption":
                pid = arguments["project_id"]
                mid = arguments["media_id"]
                r = await client.put(f"/api/project/{pid}/media/{mid}", json={
                    "caption": arguments["caption"]
                })
                return r.json()

            elif name == "vibe_reorder_media":
                pid = arguments["project_id"]
                r = await client.put(f"/api/project/{pid}/reorder", json={
                    "order": arguments["order"]
                })
                return r.json()

            else:
                return {"error": f"Unknown tool: {name}"}

        except httpx.ConnectError:
            return {"error": "Cannot connect to Vibe Studio. Make sure it's running: python app.py"}
        except Exception as e:
            return {"error": str(e)}


def read_message():
    """Read a JSON-RPC message from stdin."""
    headers = {}
    while True:
        line = sys.stdin.readline()
        if not line or line.strip() == "":
            break
        if ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip()] = v.strip()

    length = int(headers.get("Content-Length", 0))
    if length == 0:
        return None
    body = sys.stdin.read(length)
    return json.loads(body)


def main():
    """Main MCP server loop (stdio transport)."""
    sys.stderr.write("Vibe Studio MCP Server starting...\n")
    sys.stderr.flush()

    while True:
        try:
            msg = read_message()
            if msg is None:
                break

            method = msg.get("method")
            id = msg.get("id")
            params = msg.get("params", {})

            if method == "initialize":
                send_response(id, {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "vibe-studio", "version": "2.0.0"}
                })

            elif method == "notifications/initialized":
                pass  # No response needed

            elif method == "tools/list":
                send_response(id, {"tools": TOOLS})

            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                result = asyncio.run(handle_tool_call(tool_name, arguments))
                send_response(id, {
                    "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                })

            elif method == "shutdown":
                send_response(id, None)
                break

            else:
                if id:
                    send_error(id, -32601, f"Method not found: {method}")

        except Exception as e:
            sys.stderr.write(f"Error: {e}\n")
            sys.stderr.flush()
            if 'id' in dir() and id:
                send_error(id, -32603, str(e))


if __name__ == "__main__":
    main()
