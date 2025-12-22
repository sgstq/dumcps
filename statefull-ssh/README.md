# 🚀 Stateful SSH MCP

A persistent, stateful SSH adapter for MCP-capable agents (like Codex). Unlike standard tools, this maintains a **live shell session**, allowing for directory changes, environment persistence, and interactive `sudo` prompts to work exactly like a real terminal.

---

## 🤔 Why this exists?
Standard AI tools rely on "one-shot" execution where **state is lost between commands.** Running `cd /app` followed by `ls` fails because the second command starts in a fresh home directory. Furthermore, existing agents **cannot use interactive shells** or handle prompts like `sudo` passwords.

**Stateful SSH MCP** solves this by keeping a single terminal "pipe" open. Directory changes, environment exports, and interactive prompts persist throughout the entire agent task.

---

## 🛠️ Installation & Setup

### Option A: Docker Flow (Recommended) 🐳
The fastest way to get started. It runs in an isolated container and stays ready in the background.

1.  **Launch the container:**
    ```bash
    export SSH_MCP_PRESETS='{"dev": {"host": "10.0.0.15", "username": "admin", "password": "..."}}'
    docker compose up -d ssh-mcp
    ```

2.  **Add to Codex (`~/.codex/config.toml`):**
    ```toml
    [mcp_servers."ssh-interactive"]
    command = "docker"
    args = ["exec", "-i", "statefull-ssh-mcp", "python", "-m", "ssh_mcp"]
    ```

### Option B: Local Development 🐍
Use this if you want to run directly on your host machine or are developing the plugin.

1.  **Sync Dependencies:**
    ```bash
    uv sync
    source .venv/bin/activate
    ```

2.  **Add to Codex (`~/.codex/config.toml`):**
    ```toml
    [mcp_servers."ssh-local"]
    command = "python"
    args = ["-m", "ssh_mcp"]
    cwd = "/absolute/path/to/statefull-ssh"
    env = { PYTHONPATH = "src" }
    ```

---

## 🔧 Available Tools
Once the server is running, your agent can access these tools:

| Tool | Description |
| :--- | :--- |
| **`connect`** | Starts the SSH + SFTP session using a preset or manual credentials. |
| **`send_command`** | Executes a command in the **persistent** shell. |
| **`upload_file`** | Pushes a local file to the remote server via SFTP. |
| **`download_file`** | Pulls a remote file to your local machine. |
| **`disconnect`** | Gracefully closes the active session and shell. |

### 💡 Example Workflow
> **User:** "Update the web app on dev and check the logs."
>
> 1. `connect("dev")`
> 2. `send_command("cd /var/www/html && git pull")` — *The directory change persists!*
> 3. `send_command("sudo systemctl restart apache2")` — *Handles the sudo prompt in-session.*
> 4. `download_file("/var/log/apache2/error.log", "local_error.log")`
> 5. `disconnect()`

---

## ⚙️ Configuration (Presets)
To avoid passing passwords in plain text during every chat, use the `SSH_MCP_PRESETS` environment variable.

**JSON Structure:**
```json
{
  "prod": {
    "host": "ssh.example.com",
    "username": "ops",
    "password": "secure-password"
  }
}
```
*After setting this, the agent simply calls `connect("prod")`.*

---

## 🏗️ Technical Details

### Project Layout
```text
statefull-ssh/
├── src/ssh_mcp/
│   ├── server.py     # FastMCP + Paramiko implementation
│   └── __main__.py   # Entry point for python -m
├── Dockerfile        # Python 3.14-alpine based
├── pyproject.toml    # uv/PEP 621 metadata
└── uv.lock           # Deterministic dependency lock
```

### Development Commands
* **Check Code:** `uv run ruff check src`
* **Type Safety:** `uv run mypy src`
* **Run Tests:** `uv run pytest`
