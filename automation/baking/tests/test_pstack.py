import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import yaml


BAKING = Path("automation/baking")
SUBMODULE = BAKING / "upstream"
SCRIPT = Path(__file__).resolve().parents[1] / "scripts/pstack.py"


def git(root, *args):
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True, stderr=subprocess.PIPE,
    ).strip()


class PortTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("pstack", SCRIPT)
        cls.port = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.port)

    def setUp(self):
        # Local fixture repositories need file transport, scoped to this test's
        # subprocesses; never change the user's Git configuration.
        transport = mock.patch.dict(os.environ, {
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "protocol.file.allow",
            "GIT_CONFIG_VALUE_0": "always",
        })
        transport.start()
        self.addCleanup(transport.stop)
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
        self.write(self.source / "another-plugin/README.md", "An unrelated plugin.\n")
        self.commit(self.source)
        self.source_url = self.source.as_uri()
        git(self.root, "-c", "protocol.file.allow=always", "submodule", "add", "--depth", "1",
            "--name", "upstream", self.source_url, str(SUBMODULE))
        self.module = self.root / SUBMODULE
        self.package = self.module / "pstack"
        self.write(self.root / BAKING / "upstream.json", json.dumps({
            "repository": self.source_url, "ref": "main", "path": "pstack",
            "commit": git(self.source, "rev-parse", "HEAD"),
            "tree": git(self.source, "rev-parse", "HEAD:pstack"),
        }))
        self.write(self.root / BAKING / "port/PORT.md", "Use the live harness and Sonnet 5.5.\n")
        self.write(self.root / BAKING / "port/models.md", "interrogate reviewers: inherit-parent, claude-sonnet-5-5\n")
        self.write(self.root / BAKING / "port/setup-pstack.md", "# Portable setup\n\nRead the models file.\n")
        self.write(self.root / ".gitignore", ".cache/\n.worktrees/\n")
        (self.root / BAKING / "scripts").mkdir()
        shutil.copy2(SCRIPT, self.root / BAKING / "scripts/pstack.py")
        self.commit(self.root)

    @staticmethod
    def write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)

    @staticmethod
    def commit(root):
        git(root, "add", ".")
        git(root, "commit", "-m", "Fixture")

    def bake_and_commit(self):
        self.port.bake(self.root)
        self.commit(self.root)

    def baked_state(self):
        return {
            str(path.relative_to(self.root)): (path.read_bytes(), path.stat().st_mtime_ns)
            for harness in ("codex", "claude")
            for path in (self.root / harness).rglob("*") if path.is_file()
        }

    def test_build_preserves_source_resources_and_native_invocation_policy(self):
        original = (self.package / "skills/example/SKILL.md").read_bytes()
        result = self.port.build(self.root)
        self.assertEqual(result["skills"], 2)
        for harness in ("codex", "claude"):
            output = self.root / harness
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
        self.assertEqual((self.package / "skills/example/SKILL.md").read_bytes(), original)
        self.port.validate(self.root)

    def test_build_compatibility_command_bakes_packages_at_repository_root(self):
        self.port.build(self.root)
        for harness in ("codex", "claude"):
            self.assertTrue((self.root / harness / "port-manifest.json").is_file())
        self.assertFalse((self.root / "dist").exists())

    def test_fingerprint_is_independent_of_the_runtime_yaml_version(self):
        before = self.port.fingerprint(self.root)
        with mock.patch.object(yaml, "__version__", "a-different-runtime-version"):
            self.assertEqual(self.port.fingerprint(self.root), before)

    def test_manual_upstream_edits_are_not_built_as_an_authentic_snapshot(self):
        self.write(self.package / "LICENSE", "edited\n")
        with self.assertRaises(self.port.PortError):
            self.port.build(self.root)
        manifest = json.loads((self.root / BAKING / "upstream.json").read_text())
        manifest["tree"] = self.port.tree_hash(self.package)
        self.write(self.root / BAKING / "upstream.json", json.dumps(manifest))
        # Recomputing local bytes cannot give them the pinned commit's provenance.
        with self.assertRaises(self.port.PortError):
            self.port.build(self.root)

    def test_clone_requires_initialization_then_builds_the_pinned_package(self):
        clone = self.base / "clone"
        git(self.base, "clone", str(self.root), str(clone))
        with self.assertRaisesRegex(self.port.PortError, "submodule update --init"):
            self.port.build(clone)
        git(clone, "submodule", "update", "--init", str(SUBMODULE))
        self.assertEqual(git(clone / SUBMODULE, "rev-parse", "HEAD"),
                         git(self.source, "rev-parse", "HEAD"))
        self.assertEqual(self.port.build(clone)["skills"], 2)
        self.port.validate(clone)
        self.assertFalse((clone / "codex/another-plugin").exists())
        self.assertFalse((clone / "codex/.git").exists())

    def test_unregistered_source_is_rejected_even_when_its_bytes_match(self):
        git(self.root, "rm", "--cached", str(SUBMODULE))
        with self.assertRaises(self.port.PortError):
            self.port.build(self.root)

    def test_submodule_registration_must_match_the_expected_path_and_repository(self):
        git(self.root, "config", "--file", ".gitmodules", "submodule.upstream.path",
            "another-source")
        with self.assertRaises(self.port.PortError):
            self.port.build(self.root)
        git(self.root, "config", "--file", ".gitmodules", "submodule.upstream.path", str(SUBMODULE))
        git(self.root, "config", "--file", ".gitmodules", "submodule.upstream.url",
            "https://example.invalid/a-different-repository.git")
        with self.assertRaises(self.port.PortError):
            self.port.build(self.root)

    def test_submodule_head_and_registered_commit_must_match_the_manifest(self):
        self.write(self.source / "pstack/docs/guide.md", "Another revision.\n")
        self.commit(self.source)
        latest = git(self.source, "rev-parse", "HEAD")
        git(self.module, "fetch", "origin")
        git(self.module, "checkout", "--detach", latest)
        with self.assertRaises(self.port.PortError):
            self.port.build(self.root)
        manifest = json.loads((self.root / BAKING / "upstream.json").read_text())
        manifest.update(commit=latest, tree=git(self.source, "rev-parse", "HEAD:pstack"))
        self.write(self.root / BAKING / "upstream.json", json.dumps(manifest))
        # Updating only the metadata and working tree leaves the old GitHub link.
        with self.assertRaises(self.port.PortError):
            self.port.build(self.root)
        git(self.root, "add", str(SUBMODULE))
        self.assertEqual(self.port.build(self.root)["skills"], 2)

    def test_fingerprint_ignores_submodule_git_metadata_and_other_plugins(self):
        before = self.port.fingerprint(self.root)
        git_directory = git(self.module, "rev-parse", "--absolute-git-dir")
        (self.module / ".git").write_text("gitdir: " + git_directory + "\n")
        self.write(self.module / "another-plugin/README.md", "Locally changed unrelated plugin.\n")
        self.assertEqual(self.port.fingerprint(self.root), before)
        self.write(self.package / "docs/guide.md", "Changed actual input.\n")
        self.assertNotEqual(self.port.fingerprint(self.root), before)

    def test_install_is_idempotent_and_preserves_unrelated_skills(self):
        self.bake_and_commit()
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
        self.bake_and_commit()
        self.write(self.home / ".claude/skills/example/SKILL.md", "User-owned\n")
        with self.assertRaises(self.port.PortError):
            self.port.install(self.root, ["codex", "claude"], self.home)
        self.assertFalse((self.home / ".codex/skills/example").exists())
        self.assertEqual((self.home / ".claude/skills/example/SKILL.md").read_text(), "User-owned\n")

    def test_install_copies_existing_baked_bytes_without_rebaking(self):
        self.port.bake(self.root)
        baked = self.root / "codex/skills/example/SKILL.md"
        # Valid YAML has multiple byte representations. Installation must retain
        # the reviewed representation rather than regenerate equivalent metadata.
        text = baked.read_text().replace("---\n", "---\n# Reviewed baked metadata.\n", 1)
        baked.write_text(text)
        self.commit(self.root)
        before = self.baked_state()

        self.port.install(self.root, ["codex"], self.home)

        self.assertEqual(self.baked_state(), before)
        installed = self.home / ".codex/skills/example/SKILL.md"
        self.assertIn("# Reviewed baked metadata.\n", installed.read_text())
        self.assertEqual((installed.resolve().parents[2] / "LICENSE").read_bytes(),
                         b"Original MIT license\n")
        self.assertEqual(git(self.root, "status", "--porcelain"), "")

    def test_install_rejects_stale_baked_packages_without_overwriting_them(self):
        self.bake_and_commit()
        self.write(self.root / BAKING / "port/PORT.md", "A new adapter awaits baking.\n")
        self.commit(self.root)
        before = self.baked_state()

        with self.assertRaises(self.port.PortError):
            self.port.install(self.root, ["codex"], self.home)

        self.assertEqual(self.baked_state(), before)
        self.assertFalse((self.home / ".codex/skills").exists())
        self.assertFalse((self.root / ".cache/installed").exists())

    def test_install_rejects_missing_baked_files_without_recreating_them(self):
        self.bake_and_commit()
        (self.root / "claude/docs/guide.md").unlink()
        self.commit(self.root)
        before = self.baked_state()

        with self.assertRaises(self.port.PortError):
            self.port.install(self.root, ["codex", "claude"], self.home)

        self.assertEqual(self.baked_state(), before)
        self.assertFalse((self.home / ".codex/skills").exists())
        self.assertFalse((self.home / ".claude/skills").exists())
        self.assertFalse((self.root / ".cache/installed").exists())

    def test_install_rejects_an_unbaked_checkout_without_generating_packages(self):
        with self.assertRaises(self.port.PortError):
            self.port.install(self.root, ["codex"], self.home)

        self.assertFalse((self.root / "codex").exists())
        self.assertFalse((self.root / "claude").exists())
        self.assertFalse((self.root / ".cache/installed").exists())
        self.assertFalse((self.home / ".codex/skills").exists())

    def test_moved_cli_bakes_and_validates_from_another_working_directory(self):
        script = self.root / BAKING / "scripts/pstack.py"
        for command in ("bake", "validate"):
            with self.subTest(command=command):
                result = subprocess.run(
                    [sys.executable, str(script), command], cwd=self.base,
                    capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotEqual(json.loads(result.stdout)["status"], "error")
        self.assertTrue((self.root / "codex/skills/example/SKILL.md").is_file())
        self.assertTrue((self.root / "claude/skills/example/SKILL.md").is_file())
        self.assertFalse((self.base / "codex").exists())
        self.assertFalse((self.root / BAKING / "codex").exists())

    def test_building_new_candidate_does_not_change_installed_skill_contents(self):
        self.bake_and_commit()
        self.port.install(self.root, ["codex"], self.home)
        installed = self.home / ".codex/skills/example/SKILL.md"
        previous = installed.read_bytes()
        self.write(self.root / BAKING / "port/PORT.md", "A changed adapter for review.\n")
        self.port.build(self.root)
        self.assertEqual(installed.read_bytes(), previous)
        self.assertEqual((installed.resolve().parents[2] / "PORT.md").read_text(), "Use the live harness and Sonnet 5.5.\n")
        with self.assertRaises(self.port.PortError):
            self.port.install(self.root, ["codex"], self.home)
        self.commit(self.root)
        self.port.install(self.root, ["codex"], self.home)
        self.assertEqual((installed.resolve().parents[2] / "PORT.md").read_text(), "A changed adapter for review.\n")

    def test_modified_installed_release_is_preserved_on_reinstall(self):
        self.bake_and_commit()
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
        self.bake_and_commit()
        baked_before = self.baked_state()
        self.write(self.source / "pstack/docs/guide.md", "Updated upstream guide\n")
        self.commit(self.source)
        original = (self.package / "docs/guide.md").read_text()
        original_head = git(self.module, "rev-parse", "HEAD")
        first = self.port.prepare_sync(self.root)
        candidate = Path(first["worktree"])
        self.assertEqual((candidate / SUBMODULE / "pstack/docs/guide.md").read_text(), "Updated upstream guide\n")
        self.assertEqual((self.package / "docs/guide.md").read_text(), original)
        self.assertEqual(git(self.module, "rev-parse", "HEAD"), original_head)
        self.assertEqual(git(candidate / SUBMODULE, "rev-parse", "HEAD"),
                         git(self.source, "rev-parse", "HEAD"))
        self.assertNotEqual(git(candidate / SUBMODULE, "rev-parse", "--absolute-git-dir"),
                            git(self.module, "rev-parse", "--absolute-git-dir"))
        self.assertEqual(set(git(candidate, "diff", "--cached", "--name-only").splitlines()),
                         {str(SUBMODULE), str(BAKING / "upstream.json")})
        detached = subprocess.run(
            ["git", "-C", str(candidate / SUBMODULE), "symbolic-ref", "--quiet", "HEAD"],
            capture_output=True,
        )
        self.assertEqual(detached.returncode, 1)
        self.port.build(candidate)
        self.port.validate(candidate)
        self.write(candidate / "agent-notes.txt", "Unfinished reconciliation\n")
        second = self.port.prepare_sync(self.root)
        self.assertEqual(first["worktree"], second["worktree"])
        self.assertTrue(second["reused"])
        self.assertEqual((candidate / "agent-notes.txt").read_text(), "Unfinished reconciliation\n")
        self.assertEqual(git(self.root, "branch", "--show-current"), "main")
        self.assertEqual(self.baked_state(), baked_before)
        pending = self.port.check(self.root)
        self.assertEqual(pending["status"], "candidate_pending")
        self.assertFalse(pending["wakeAgent"])
        self.assertEqual(pending["worktree"], str(candidate))

    def test_validate_rejects_missing_or_modified_support_files_and_modes(self):
        self.port.build(self.root)
        output = self.root / "codex"
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
        self.bake_and_commit()
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
        self.port.bake(candidate)
        self.commit(candidate)
        git(self.root, "merge", "--ff-only", git(candidate, "branch", "--show-current"))
        with self.assertRaises(self.port.PortError):
            self.port.build(self.root)
        git(self.root, "submodule", "update", "--init", str(SUBMODULE))
        self.port.install(self.root, ["codex"], self.home)
        self.assertEqual((self.root / "codex/docs/guide.md").read_bytes(), content)
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
        previous = (self.root / BAKING / "upstream.json").read_bytes()
        with self.assertRaises(self.port.PortError):
            self.port.check(self.root, source=str(self.base / "missing-source"))
        self.assertEqual((self.root / BAKING / "upstream.json").read_bytes(), previous)

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
        self.bake_and_commit()
        self.port.install(self.root, ["codex"], self.home)
        self.write(self.home / ".codex/skills/unrelated/SKILL.md", "Keep user work\n")
        shutil.rmtree(self.source / "pstack/skills/example")
        self.commit(self.source)
        result = self.port.prepare_sync(self.root)
        candidate = Path(result["worktree"])
        self.port.bake(candidate)
        self.commit(candidate)
        git(self.root, "merge", "--ff-only", result["branch"])
        git(self.root, "submodule", "update", "--init", str(SUBMODULE))
        installed = self.port.install(self.root, ["codex"], self.home)
        self.assertEqual(installed["removed_owned_links"], 1)
        self.assertFalse((self.home / ".codex/skills/example").is_symlink())
        self.assertEqual((self.home / ".codex/skills/unrelated/SKILL.md").read_text(), "Keep user work\n")
        self.assertTrue((self.home / ".codex/skills/setup-pstack/SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main()
