import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/pstack.py"


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


class PortTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("pstack", SCRIPT)
        cls.port = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.port)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / "source"
        self.root = self.base / "port"
        self.home = self.base / "home"
        self.source.mkdir()
        self.root.mkdir()
        for root in (self.source, self.root):
            git(root, "init", "-b", "main")
            git(root, "config", "user.name", "Test")
            git(root, "config", "user.email", "test@example.invalid")
        self.write(self.source / "pstack/LICENSE", "Original MIT license\n")
        self.write(self.source / "pstack/docs/guide.md", "The original guide.\n")
        self.write(self.source / "pstack/skills/example/SKILL.md", (
            "---\nname: Original Name\ndescription: A specific workflow.\n"
            "disable-model-invocation: true\nicon: crown\npaths: '**/*.ts'\n---\n\n"
            "# Example\n\nUse [the guide](../../docs/guide.md).\n"
            "Read `~/.cursor/rules/pstack-models.mdc`.\n"
        ))
        self.write(self.source / "pstack/skills/setup-pstack/SKILL.md", (
            "---\nname: setup-pstack\ndescription: Configure models.\n---\n\n"
            "Original Cursor setup.\n"
        ))
        self.commit(self.source)
        import shutil
        shutil.copytree(self.source / "pstack", self.root / "upstream")
        self.write(self.root / "upstream.json", json.dumps({
            "repository": str(self.source), "ref": "main", "path": "pstack",
            "commit": git(self.source, "rev-parse", "HEAD"),
            "tree": git(self.source, "rev-parse", "HEAD:pstack"),
        }))
        self.write(self.root / "port/PORT.md", "Use the live harness and Sonnet 5.5.\n")
        self.write(self.root / "port/models.md", "interrogate reviewers: inherit-parent, claude-sonnet-5-5\n")
        self.write(self.root / "port/setup-pstack.md", "# Portable setup\n\nRead the models file.\n")
        self.write(self.root / ".gitignore", ".cache/\n.worktrees/\ndist/\n")
        self.commit(self.root)

    @staticmethod
    def write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)

    @staticmethod
    def commit(root):
        git(root, "add", ".")
        git(root, "commit", "-m", "Fixture")

    def test_build_preserves_source_resources_and_native_invocation_policy(self):
        original = (self.root / "upstream/skills/example/SKILL.md").read_bytes()
        result = self.port.build(self.root)
        self.assertEqual(result["skills"], 2)
        for harness in ("codex", "claude"):
            output = self.root / "dist" / harness
            self.assertEqual((output / "LICENSE").read_text(), "Original MIT license\n")
            self.assertTrue((output / "docs/guide.md").is_file())
            text = (output / "skills/example/SKILL.md").read_text()
            self.assertIn("# Example", text)
            self.assertIn("../../PORT.md", text)
            self.assertIn("~/.config/pstack/models.md", text)
            self.assertIn("# Portable setup", (output / "skills/setup-pstack/SKILL.md").read_text())
            front = yaml.safe_load(text.split("---", 2)[1])
            self.assertEqual(front["name"], "example")
            if harness == "codex":
                self.assertNotIn("disable-model-invocation", front)
                self.assertEqual(front["metadata"]["upstream-paths"], "**/*.ts")
                policy = yaml.safe_load((output / "skills/example/agents/openai.yaml").read_text())
                self.assertFalse(policy["policy"]["allow_implicit_invocation"])
            else:
                self.assertTrue(front["disable-model-invocation"])
        self.assertEqual((self.root / "upstream/skills/example/SKILL.md").read_bytes(), original)
        self.port.validate(self.root)

    def test_manual_upstream_edits_are_not_built_as_an_authentic_snapshot(self):
        self.write(self.root / "upstream/LICENSE", "edited\n")
        with self.assertRaises(self.port.PortError):
            self.port.build(self.root)

    def test_install_is_idempotent_and_preserves_unrelated_skills(self):
        self.write(self.home / ".codex/skills/unrelated/SKILL.md", "User skill\n")
        self.port.install(self.root, ["codex", "claude"], self.home)
        self.port.install(self.root, ["codex", "claude"], self.home)
        for harness in ("codex", "claude"):
            link = self.home / ("." + harness) / "skills/example"
            self.assertTrue(link.is_symlink())
            self.assertEqual(link.resolve().parent.parent.parent.parent, self.root / ".cache/installed")
            self.assertEqual(link.resolve().parts[-3:], (harness, "skills", "example"))
        self.assertEqual((self.home / ".codex/skills/unrelated/SKILL.md").read_text(), "User skill\n")

    def test_install_preflights_every_target_before_changing_any_links(self):
        self.write(self.home / ".claude/skills/example/SKILL.md", "User-owned\n")
        with self.assertRaises(self.port.PortError):
            self.port.install(self.root, ["codex", "claude"], self.home)
        self.assertFalse((self.home / ".codex/skills/example").exists())
        self.assertEqual((self.home / ".claude/skills/example/SKILL.md").read_text(), "User-owned\n")

    def test_building_new_candidate_does_not_change_installed_skill_contents(self):
        self.port.install(self.root, ["codex"], self.home)
        installed = self.home / ".codex/skills/example/SKILL.md"
        previous = installed.read_bytes()
        self.write(self.root / "port/PORT.md", "A changed adapter for review.\n")
        self.port.build(self.root)
        self.assertEqual(installed.read_bytes(), previous)
        self.assertEqual((installed.resolve().parents[2] / "PORT.md").read_text(), "Use the live harness and Sonnet 5.5.\n")
        with self.assertRaises(self.port.PortError):
            self.port.install(self.root, ["codex"], self.home)
        self.commit(self.root)
        self.port.install(self.root, ["codex"], self.home)
        self.assertEqual((installed.resolve().parents[2] / "PORT.md").read_text(), "A changed adapter for review.\n")

    def test_modified_installed_release_is_preserved_on_reinstall(self):
        self.port.install(self.root, ["codex"], self.home)
        installed = self.home / ".codex/skills/example/SKILL.md"
        installed.write_text("A user's modification.\n")
        with self.assertRaises(self.port.PortError):
            self.port.install(self.root, ["codex"], self.home)
        self.assertEqual(installed.read_text(), "A user's modification.\n")

    def test_subtree_check_ignores_unrelated_monorepo_changes(self):
        self.write(self.source / "another-plugin.txt", "Unrelated\n")
        self.commit(self.source)
        result = self.port.check(self.root)
        self.assertFalse(result["changed"])
        self.assertFalse(result["wakeAgent"])
        self.assertEqual(result["status"], "unchanged")

    def test_prepare_reuses_candidate_without_installing_or_overwriting_work(self):
        self.write(self.source / "pstack/docs/guide.md", "Updated upstream guide\n")
        self.commit(self.source)
        original = (self.root / "upstream/docs/guide.md").read_text()
        first = self.port.prepare_sync(self.root)
        candidate = Path(first["worktree"])
        self.assertEqual((candidate / "upstream/docs/guide.md").read_text(), "Updated upstream guide\n")
        self.assertEqual((self.root / "upstream/docs/guide.md").read_text(), original)
        self.write(candidate / "agent-notes.txt", "Unfinished reconciliation\n")
        second = self.port.prepare_sync(self.root)
        self.assertEqual(first["worktree"], second["worktree"])
        self.assertTrue(second["reused"])
        self.assertEqual((candidate / "agent-notes.txt").read_text(), "Unfinished reconciliation\n")
        self.assertEqual(git(self.root, "branch", "--show-current"), "main")
        self.assertFalse((self.root / "dist").exists())
        pending = self.port.check(self.root)
        self.assertEqual(pending["status"], "candidate_pending")
        self.assertFalse(pending["wakeAgent"])
        self.assertEqual(pending["worktree"], str(candidate))

    def test_validate_rejects_missing_or_modified_support_files_and_modes(self):
        self.port.build(self.root)
        output = self.root / "dist/codex"
        guide = output / "docs/guide.md"
        guide.unlink()
        with self.assertRaises(self.port.PortError):
            self.port.validate(self.root)
        self.port.build(self.root)
        (output / "LICENSE").write_text("Lost original notice\n")
        with self.assertRaises(self.port.PortError):
            self.port.validate(self.root)
        self.port.build(self.root)
        (output / "LICENSE").chmod(0o755)
        with self.assertRaises(self.port.PortError):
            self.port.validate(self.root)

    def test_installed_markdown_links_are_absolute_and_do_not_need_symlink_traversal(self):
        import re
        import posixpath
        self.port.install(self.root, ["codex"], self.home)
        installed = self.home / ".codex/skills/example/SKILL.md"
        targets = re.findall(r"\]\(([^)]+)\)", installed.read_text())
        self.assertEqual(len(targets), 2)
        for target in targets:
            self.assertTrue(Path(target).is_absolute())
            self.assertTrue(Path(posixpath.normpath(target)).is_file())

    def test_support_file_line_endings_and_non_utf8_bytes_survive_build_and_install(self):
        content = b"First\r\nSecond\xff\r\n"
        (self.source / "pstack/docs/guide.md").write_bytes(content)
        self.commit(self.source)
        candidate = Path(self.port.prepare_sync(self.root)["worktree"])
        self.commit(candidate)
        git(self.root, "merge", "--ff-only", git(candidate, "branch", "--show-current"))
        self.port.install(self.root, ["codex"], self.home)
        self.assertEqual((self.root / "dist/codex/docs/guide.md").read_bytes(), content)
        release = (self.home / ".codex/skills/example").resolve().parents[1]
        self.assertEqual((release / "docs/guide.md").read_bytes(), content)

    def test_checks_from_another_worktree_share_primary_cache_and_candidates(self):
        other = self.base / "other"
        git(self.root, "worktree", "add", "-b", "other", str(other))
        self.write(self.source / "pstack/docs/guide.md", "New source\n")
        self.commit(self.source)
        result = self.port.prepare_sync(other)
        self.assertEqual(Path(result["worktree"]).parent, self.root / ".worktrees")
        self.assertFalse((other / ".cache").exists())
        self.assertEqual(self.port.check(other)["status"], "candidate_pending")

    def test_prepare_refuses_dirty_base(self):
        self.write(self.root / "user-work.txt", "Preserve me\n")
        with self.assertRaises(self.port.PortError):
            self.port.prepare_sync(self.root)
        self.assertFalse((self.root / ".worktrees").exists())

    def test_failed_fetch_is_an_error_and_preserves_the_pinned_source(self):
        previous = (self.root / "upstream.json").read_bytes()
        with self.assertRaises(self.port.PortError):
            self.port.check(self.root, source=str(self.base / "missing-source"))
        self.assertEqual((self.root / "upstream.json").read_bytes(), previous)

    def test_sync_lock_refuses_a_competing_updater(self):
        with self.port.sync_lock(self.root):
            with self.assertRaises(self.port.PortError):
                self.port.check(self.root)
        self.assertFalse(self.port.check(self.root)["wakeAgent"])

    def test_candidate_cannot_be_installed_before_integration(self):
        self.write(self.source / "pstack/docs/guide.md", "Next version\n")
        self.commit(self.source)
        candidate = Path(self.port.prepare_sync(self.root)["worktree"])
        with self.assertRaises(self.port.PortError):
            self.port.install(candidate, ["codex"], self.home)
        self.assertFalse((self.home / ".codex/skills").exists())

    def test_integrated_update_removes_only_retired_owned_skill_links(self):
        import shutil
        self.port.install(self.root, ["codex"], self.home)
        self.write(self.home / ".codex/skills/unrelated/SKILL.md", "Keep user work\n")
        shutil.rmtree(self.source / "pstack/skills/example")
        self.commit(self.source)
        result = self.port.prepare_sync(self.root)
        candidate = Path(result["worktree"])
        self.commit(candidate)
        git(self.root, "merge", "--ff-only", result["branch"])
        installed = self.port.install(self.root, ["codex"], self.home)
        self.assertEqual(installed["removed_owned_links"], 1)
        self.assertFalse((self.home / ".codex/skills/example").is_symlink())
        self.assertEqual((self.home / ".codex/skills/unrelated/SKILL.md").read_text(), "Keep user work\n")
        self.assertTrue((self.home / ".codex/skills/setup-pstack/SKILL.md").is_file())

    def test_archive_rejects_traversal(self):
        import io
        import tarfile
        data = io.BytesIO()
        with tarfile.open(fileobj=data, mode="w") as archive:
            item = tarfile.TarInfo("../escape")
            item.size = 1
            archive.addfile(item, io.BytesIO(b"x"))
        with self.assertRaises(self.port.PortError):
            self.port.extract_snapshot(data.getvalue(), self.base / "extract")
        self.assertFalse((self.base / "escape").exists())


if __name__ == "__main__":
    unittest.main()
