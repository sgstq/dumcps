"""Stateful SSH MCP server for interactive shell sessions.

This server exposes a handful of MCP tools the agent can call to
maintain a persistent SSH shell, send commands through it, and transfer
files. It mirrors the prototype that used Paramiko and the FastMCP
runner but packages it as an importable module/CLI so it can be wired
into Claude Desktop (or any MCP-compatible agent).
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import paramiko
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("InteractiveSSH")


@dataclass
class Preset:
    host: str
    username: str
    password: str


@dataclass
class Session:
    client: paramiko.SSHClient | None = None
    shell: paramiko.Channel | None = None
    sftp: paramiko.SFTPClient | None = None
    hostname: str | None = None
    username: str | None = None

    def close(self) -> None:
        for attr in ("shell", "sftp", "client"):
            if connection := getattr(self, attr):
                try:
                    connection.close()
                except Exception:
                    pass
                finally:
                    setattr(self, attr, None)
        self.hostname = None
        self.username = None


SESSION = Session()
PRESETS: Dict[str, Preset] = {}
_PRESET_ENV_VAR = "SSH_MCP_PRESETS"


def _load_presets() -> None:
    """Populate PRESETS from JSON stored in SSH_MCP_PRESETS env var."""
    raw = os.getenv(_PRESET_ENV_VAR)
    if not raw:
        return
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in {_PRESET_ENV_VAR}: {exc.msg}") from exc

    for name, creds in data.items():
        if not {"host", "username", "password"} <= set(creds):
            raise RuntimeError(
                f"Preset '{name}' must define host, username, and password"
            )
        PRESETS[name] = Preset(
            host=creds["host"],
            username=creds["username"],
            password=creds["password"],
        )


_load_presets()


def _resolve_preset(target: str, username: str | None, password: str | None) -> Preset:
    if target in PRESETS:
        return PRESETS[target]
    if not (username and password):
        raise ValueError(
            "Username and password are required unless you reference a preset"
        )
    return Preset(host=target, username=username, password=password)


def _read_buffer(shell: paramiko.Channel, window: float = 0.2) -> str:
    buffer: list[str] = []
    deadline = time.monotonic() + window
    while True:
        if shell.recv_ready():
            data = shell.recv(4096).decode("utf-8", errors="ignore")
            buffer.append(data)
            deadline = time.monotonic() + window
            continue
        if time.monotonic() >= deadline:
            break
        time.sleep(0.05)
    return "".join(buffer)


@mcp.tool()
def connect(
    target: str, username: str | None = None, password: str | None = None
) -> str:
    """Connect to a remote host and open an interactive shell."""
    preset = _resolve_preset(target, username, password)
    SESSION.close()

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        preset.host,
        username=preset.username,
        password=preset.password,
        look_for_keys=False,
        allow_agent=False,
    )

    shell = client.invoke_shell(term="xterm")
    shell.settimeout(0.0)

    SESSION.client = client
    SESSION.shell = shell
    SESSION.sftp = client.open_sftp()
    SESSION.hostname = preset.host
    SESSION.username = preset.username

    time.sleep(1.0)
    output = _read_buffer(shell)
    return (
        f"Connected to {preset.username}@{preset.host}.\n"
        f"Initial Output:\n{output.strip()}"
    )


@mcp.tool()
def disconnect() -> str:
    """Terminate any existing SSH session."""
    if not SESSION.client:
        return "No active connection to close."
    SESSION.close()
    return "Disconnected."


def _collect_command_output(
    shell: paramiko.Channel, wait_seconds: float | None
) -> str:
    """Gather shell output for up to ``wait_seconds`` seconds.

    When ``wait_seconds`` is ``None`` we return after a single buffer drain,
    mirroring the previous behaviour. Otherwise we keep polling the channel
    until the deadline elapses and then do a final drain to capture any prompt
    that arrived right as the timeout expired.
    """

    if wait_seconds is None:
        return _read_buffer(shell)

    wait_seconds = max(0.0, wait_seconds)
    deadline = time.monotonic() + wait_seconds
    chunks: list[str] = []

    while time.monotonic() < deadline:
        chunk = _read_buffer(shell)
        if chunk:
            chunks.append(chunk)
            continue
        time.sleep(0.05)

    trailing = _read_buffer(shell)
    if trailing:
        chunks.append(trailing)
    return "".join(chunks)


@mcp.tool()
def send_command(command: str, wait_seconds: float | None = 2.0) -> str:
    """Run a command (or respond to prompts) over the active shell.

    ``wait_seconds`` controls how long to keep listening for additional output.
    Pass ``None`` to perform a single non-blocking drain of the shell buffer.
    """
    shell = SESSION.shell
    if not shell:
        return "Error: No active connection. Use connect first."

    shell.send((command + "\n").encode("utf-8"))
    return _collect_command_output(shell, wait_seconds)


@mcp.tool()
def upload_file(local_path: str, remote_path: str) -> str:
    """Upload a local file to the remote host via SFTP."""
    sftp = SESSION.sftp
    if not sftp:
        return "Error: No active connection."

    source = Path(local_path).expanduser().resolve(strict=False)
    if not source.exists():
        return f"Error: Local file '{source}' not found."

    sftp.put(str(source), remote_path)
    return f"Uploaded {source} -> {remote_path}"


@mcp.tool()
def download_file(remote_path: str, local_path: str) -> str:
    """Download a remote file to the local machine via SFTP."""
    sftp = SESSION.sftp
    if not sftp:
        return "Error: No active connection."

    target = Path(local_path).expanduser().resolve(strict=False)
    target.parent.mkdir(parents=True, exist_ok=True)
    sftp.get(remote_path, str(target))
    return f"Downloaded {remote_path} -> {target}"


def main() -> None:
    """Entry point for running the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
