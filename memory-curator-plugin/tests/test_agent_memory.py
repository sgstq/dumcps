from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PLUGIN_ROOT / "skills" / "agent-memory" / "scripts" / "agent_memory.py"


class AgentMemoryTests(unittest.TestCase):
    def run_tool(self, *args: str, cwd: Path, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(SCRIPT), *args],
            input=stdin,
            text=True,
            capture_output=True,
            cwd=cwd,
            check=False,
        )

    def test_init_creates_scaffold_in_current_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            result = self.run_tool("init", cwd=cwd)

            self.assertEqual(result.returncode, 0, result.stderr)
            memory_dir = cwd / ".agents" / "memory"
            self.assertTrue(memory_dir.is_dir())
            self.assertTrue((memory_dir / "MEMORY.md").is_file())
            self.assertTrue((memory_dir / ".log").is_file())
            self.assertTrue((memory_dir / "general.md").is_file())
            self.assertTrue((memory_dir / "sources").is_dir())

    def test_capture_stub_persists_source_and_updates_memory(self) -> None:
        transcript = "\n".join(
            [
                "User: please remember this",
                "INSIGHT: Deploys require the VPN before hitting the staging database.",
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            result = self.run_tool("capture", "--backend", "stub", cwd=cwd, stdin=transcript)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("updated:", result.stdout)

            memory_dir = cwd / ".agents" / "memory"
            sources = list((memory_dir / "sources").glob("*.md"))
            self.assertEqual(len(sources), 1)
            self.assertIn("VPN", sources[0].read_text(encoding="utf-8"))

            memory_text = (memory_dir / "general.md").read_text(encoding="utf-8")
            self.assertIn("Deploys require the VPN before hitting the staging database.", memory_text)

            index_text = (memory_dir / "MEMORY.md").read_text(encoding="utf-8")
            self.assertIn("[General](general.md)", index_text)

            log_text = (memory_dir / ".log").read_text(encoding="utf-8")
            self.assertIn("updated from", log_text)

    def test_capture_stub_no_source_copy_avoids_persisted_source(self) -> None:
        transcript = "INSIGHT: The release checklist lives outside the repo."
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            result = self.run_tool(
                "capture",
                "--backend",
                "stub",
                "--no-source-copy",
                cwd=cwd,
                stdin=transcript,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(any((cwd / ".agents" / "memory" / "sources").glob("*.md")))


if __name__ == "__main__":
    unittest.main()
