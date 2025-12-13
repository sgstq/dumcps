from collections import deque
from pathlib import Path

import pytest

from ssh_mcp import server


class FakeClock:
    def __init__(self) -> None:
        self.current = 0.0

    def monotonic(self) -> float:
        return self.current

    def sleep(self, duration: float) -> None:
        self.current += duration


class FakeChannel:
    def __init__(self, clock: FakeClock, events: list[tuple[float, str]]) -> None:
        self.clock = clock
        self._events = deque(events)
        self._buffer = bytearray()
        self.sent_payloads: list[bytes] = []

    def _release_events(self) -> None:
        while self._events and self._events[0][0] <= self.clock.monotonic():
            _, data = self._events.popleft()
            self._buffer.extend(data.encode("utf-8"))

    def send(self, payload: bytes) -> int:
        self.sent_payloads.append(payload)
        return len(payload)

    def recv_ready(self) -> bool:
        self._release_events()
        return bool(self._buffer)

    def recv(self, size: int) -> bytes:
        self._release_events()
        if not self._buffer:
            return b""
        chunk = self._buffer[:size]
        del self._buffer[:size]
        return bytes(chunk)


class FakeSFTP:
    def __init__(self, remote_files: dict[str, str] | None = None) -> None:
        self.remote_files = remote_files or {}
        self.put_calls: list[tuple[str, str]] = []
        self.get_calls: list[tuple[str, str]] = []

    def put(self, local_path: str, remote_path: str) -> None:
        self.put_calls.append((local_path, remote_path))

    def get(self, remote_path: str, local_path: str) -> None:
        self.get_calls.append((remote_path, local_path))
        Path(local_path).write_text(self.remote_files.get(remote_path, ""))


@pytest.fixture
def fake_clock(monkeypatch: pytest.MonkeyPatch) -> FakeClock:
    clock = FakeClock()
    monkeypatch.setattr(server.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(server.time, "sleep", clock.sleep)
    return clock


def test_collect_command_output_waits_for_delayed_data(fake_clock: FakeClock) -> None:
    channel = FakeChannel(fake_clock, events=[(3.0, "slow"), (4.5, "done")])

    output = server._collect_command_output(channel, wait_seconds=5.0)

    assert "slow" in output
    assert "done" in output


def test_send_command_handles_long_running_commands(fake_clock: FakeClock) -> None:
    channel = FakeChannel(fake_clock, events=[(2.0, "first"), (6.0, "second")])
    server.SESSION.shell = channel

    try:
        output = server.send_command("echo hi", wait_seconds=7.0)
    finally:
        server.SESSION.shell = None

    assert channel.sent_payloads == [b"echo hi\n"]
    assert "second" in output


def test_upload_file_requires_active_connection(tmp_path: Path) -> None:
    local_file = tmp_path / "missing.txt"
    server.SESSION.sftp = None
    try:
        message = server.upload_file(str(local_file), "/tmp/remote.txt")
    finally:
        server.SESSION.sftp = None

    assert message == "Error: No active connection."


def test_upload_file_rejects_missing_source(tmp_path: Path) -> None:
    fake_sftp = FakeSFTP()
    server.SESSION.sftp = fake_sftp
    missing = tmp_path / "missing.bin"

    try:
        message = server.upload_file(str(missing), "/var/data.bin")
    finally:
        server.SESSION.sftp = None

    assert "not found" in message
    assert fake_sftp.put_calls == []


def test_upload_file_uses_sftp_put(tmp_path: Path) -> None:
    fake_sftp = FakeSFTP()
    server.SESSION.sftp = fake_sftp

    local_file = tmp_path / "payload.txt"
    local_file.write_text("payload")

    try:
        message = server.upload_file(str(local_file), "/tmp/payload.txt")
    finally:
        server.SESSION.sftp = None

    assert message == f"Uploaded {local_file.resolve()} -> /tmp/payload.txt"
    assert fake_sftp.put_calls == [(str(local_file.resolve()), "/tmp/payload.txt")]


def test_download_file_requires_active_connection(tmp_path: Path) -> None:
    destination = tmp_path / "download" / "file.txt"
    server.SESSION.sftp = None
    try:
        message = server.download_file("/remote/file.txt", str(destination))
    finally:
        server.SESSION.sftp = None

    assert message == "Error: No active connection."


def test_download_file_creates_parent_dirs(tmp_path: Path) -> None:
    fake_sftp = FakeSFTP(remote_files={"/remote/file.txt": "data"})
    server.SESSION.sftp = fake_sftp
    destination = tmp_path / "nested" / "deep" / "file.txt"

    try:
        message = server.download_file("/remote/file.txt", str(destination))
    finally:
        server.SESSION.sftp = None

    assert message == f"Downloaded /remote/file.txt -> {destination.resolve()}"
    assert fake_sftp.get_calls == [
        ("/remote/file.txt", str(destination.resolve()))
    ]
    assert destination.read_text() == "data"
