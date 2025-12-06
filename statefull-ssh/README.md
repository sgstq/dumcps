# Stateful SSH MCP

A standalone, MCP-compatible adapter that provides a persistent SSH session
backed by Paramiko. Agents can establish a connection once and reuse the same
shell for subsequent commands, interactive prompts, or file transfers.

## Features
- **Stateful commands** – `send_command` reuses a single shell so directory
  changes, environment exports, and sudo prompts behave like a real terminal.
- **Credential presets** – optional `SSH_MCP_PRESETS` environment variable lets
  you predefine host/user/password tuples and switch between them by name.
- **File transfer tooling** – `upload_file` and `download_file` operate over the
  authenticated SFTP channel opened during `connect`.
- **Graceful disconnect** – close the active session explicitly before rotating
  credentials or switching targets.

## Project layout
```
statefull-ssh/
├── README.md           # this file
├── pyproject.toml      # uv/PEP 621 metadata
├── Dockerfile          # uv-enabled container image
├── docker-compose.yml  # helper service for docker/compose workflows
├── src/
│   └── ssh_mcp/
│       ├── __init__.py
│       ├── __main__.py # supports `python -m ssh_mcp`
│       └── server.py   # FastMCP + Paramiko implementation
└── uv.lock             # resolved dependency versions
```

## Requirements
- Python 3.14 or later
- [uv](https://github.com/astral-sh/uv) for dependency management
- Docker + Docker Compose (optional, only for container workflows)

## Installation (local environment)
```bash
cd statefull-ssh
uv sync            # creates .venv and installs dependencies
source .venv/bin/activate
```

## Configuration
- Presets: `ssh_mcp` reads credentials from the `SSH_MCP_PRESETS` environment
  variable. Supply JSON that maps preset names to credential dictionaries:

  ```bash
  export SSH_MCP_PRESETS='{
    "dev": {"host": "10.0.0.15", "username": "deployer", "password": "secret"},
    "prod": {"host": "ssh.example.com", "username": "ops", "password": "supersafe"}
  }'
  ```

  Calling `connect("dev")` uses the preset. Without presets the agent must pass
  `target`, `username`, and `password` explicitly.
- Virtualenv: `uv sync` creates `.venv/` and the Docker image installs the same
  environment. No extra steps are needed as long as you run commands via
  `uv run …` or, inside Docker, `python -m ssh_mcp`.

## Running the server locally
Inside the project directory:

```bash
PYTHONPATH=src python -m ssh_mcp
# or, with uv
uv run -m ssh_mcp
```

When wiring it into Codex CLI (or any MCP-aware agent) you have two options:

1. **Direct local execution** – if you run the MCP server on the host, point
   Codex to `python -m ssh_mcp` just like a normal script and keep `cwd` set to
   `/absolute/path/to/statefull-ssh` so `src` stays on `PYTHONPATH`.
2. **Docker execution** – if you're using the compose workflow below, point
   Codex to `docker exec statefull-ssh-mcp python -m ssh_mcp`. Because the
   container name is fixed, no special working directory is required.

### Codex configuration
Codex stores its settings at `~/.codex/config.toml`. Add entries like:

```json
{
  "mcpServers": {
    "ssh-interactive": {
      "command": "python",
      "args": ["-m", "ssh_mcp"],
      "cwd": "/absolute/path/to/statefull-ssh",
      "env": { "PYTHONPATH": "src" }
    },
  }
}
```

Codex’s `config.toml` uses TOML rather than JSON. Equivalent entries look like:

```toml
[mcp_servers."ssh-interactive"]
command = "python"
args = ["-m", "ssh_mcp"]
cwd = "/absolute/path/to/statefull-ssh"
env = { PYTHONPATH = "src" }

[mcp_servers."ssh-interactive-docker"]
command = "docker"
args = ["exec", "-i", "statefull-ssh-mcp", "python", "-m", "ssh_mcp"]
```

If you only need the Docker flow, keep the second block and omit the first one.
Example Codex configuration for the Docker option:
```json
{
  "mcpServers": {
    "ssh-interactive-docker": {
      "command": "docker",
      "args": ["exec", "-i", "statefull-ssh-mcp", "python", "-m", "ssh_mcp"]
    }
  }
}
```

## Docker / Docker Compose
The repository ships with a Dockerfile (based on `python:3.14-alpine`) that
installs `uv` plus the build tooling Paramiko/cryptography need. It also
includes a compose service that keeps a container running so the agent can
start the MCP server via `docker exec -i statefull-ssh-mcp ...`.

### Build and launch the service container
```bash
cd statefull-ssh
docker compose build ssh-mcp
SSH_MCP_PRESETS='{"dev": {...}}' docker compose up -d ssh-mcp
```

The compose file mounts `./src` read-only for iterative development. Once the
container is up you can launch the MCP server with:

```bash
docker exec -i statefull-ssh-mcp python -m ssh_mcp
```

Because the container name is fixed (`statefull-ssh-mcp`), agents can call the
same command from anywhere without worrying about Compose project names.

### Environment
`SSH_MCP_PRESETS` is passed through from your host environment. If you need to
inject additional variables (proxy settings, logging options, etc.) extend the
`environment` block in `docker-compose.yml`.

## Using the MCP server
Pick whichever environment you prefer (local Python or Docker) and run the same
tooling commands as the agent will. The Docker path gives Codex a predictable,
containerized runtime, but both options remain fully supported.

### Local workflow
```bash
cd /path/to/statefull-ssh
uv sync && source .venv/bin/activate
export SSH_MCP_PRESETS='{"dev": {...}}'
uv run -m ssh_mcp
```

Leave that process running; your MCP-capable client can now connect using the
`ssh_mcp` tools.

### Docker workflow
```bash
cd /path/to/statefull-ssh
docker compose up -d ssh-mcp
docker exec -i statefull-ssh-mcp python -m ssh_mcp
```

When the agent wants to start the MCP server, configure it to execute the same
`docker exec -i statefull-ssh-mcp python -m ssh_mcp` command. Because `docker exec`
does not depend on your current directory, no special `cwd` handling is needed
once the container is running (Compose is still used for build/up). The `-i`
flag keeps STDIN open so the MCP handshake can stream through the container, and
running `python -m ssh_mcp` avoids additional output that would break the MCP
handshake. If Codex reports “no such container,” rerun `docker compose up -d
ssh-mcp` and verify the name with `docker ps --format '{{.Names}}'`.

## MCP tools
- `connect(target, username?, password?)`: establishes the SSH + SFTP session.
- `disconnect()`: closes any active session.
- `send_command(command, wait_seconds=2.0)`: writes to the shell and returns the
  buffered output after a short delay.
- `upload_file(local_path, remote_path)`: pushes a local file through SFTP.
- `download_file(remote_path, local_path)`: retrieves a remote file.

## Typical workflow
1. `connect("dev")`
2. `send_command("cd /var/www && git pull")`
3. `send_command("sudo systemctl restart api")`
4. `download_file("/var/log/api.log", "./logs/api.log")`
5. `disconnect()`

Because the same shell stays open between steps, prompts (like sudo passwords)
or stateful operations (changing directories) behave naturally.

## Development
- Lint: `uv run ruff check src`
- Types: `uv run mypy src`
- Tests: `uv run pytest`

These commands assume you activated the project virtual environment via `uv
sync`. Adjust or extend them as needed for your workflow.
