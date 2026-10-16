"""Exercise delivery boundaries using isolated Git and CLI fixtures."""

import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import delivery


LEAD = "Co-authored-by: OpenAI Codex GPT-6.1-Sol <noreply@openai.com>"


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True,
                                   stderr=subprocess.PIPE).strip()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value)


def commit(root, message="Fixture"):
    git(root, "add", ".")
    git(root, "commit", "-m", message)


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        environment = mock.patch.dict(os.environ, {
            "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "protocol.file.allow",
            "GIT_CONFIG_VALUE_0": "always",
        })
        environment.start()
        self.addCleanup(environment.stop)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.root = self.base / "port"
        self.source = self.base / "canonical"
        self.origin = self.base / "origin.git"
        for path in (self.root, self.source):
            path.mkdir()
            git(path, "init", "-b", "main")
            git(path, "config", "user.name", "Test")
            git(path, "config", "user.email", "test@example.invalid")
        write(self.source / "pstack/plugin.json", json.dumps({
            "name": "pstack", "version": "1.0.0", "license": "MIT", "keywords": [],
        }))
        write(self.source / "pstack/LICENSE", "MIT fixture\n")
        write(self.source / "pstack/skills/example/SKILL.md",
              "---\nname: example\ndescription: Fixture workflow.\ndisable-model-invocation: true\n---\n\nHello.\n")
        commit(self.source)
        git(self.root, "submodule", "add", "--name", "upstream", self.source.as_uri(),
            str(delivery.pstack.SUBMODULE))
        baking = self.root / delivery.pstack.BAKING
        write(baking / "upstream.json", json.dumps({
            "repository": self.source.as_uri(), "ref": "main", "path": "pstack",
            "commit": git(self.source, "rev-parse", "HEAD"),
            "tree": git(self.source, "rev-parse", "HEAD:pstack"),
        }))
        write(baking / "release.json", '{"version": "0.1.0"}\n')
        write(baking / "port/PORT.md", "Portable harness instructions.\n")
        write(baking / "port/models.md", "interrogate reviewers: inherit-parent, auto\n")
        write(baking / "port/setup-pstack.md", "Setup fixture.\n")
        write(baking / "tests/test_smoke.py", "import unittest\nclass Smoke(unittest.TestCase):\n def test_ok(self): self.assertTrue(True)\n")
        (baking / "scripts").mkdir()
        for name in ("pstack.py", "delivery.py"):
            shutil.copy2(SCRIPTS / name, baking / "scripts" / name)
        write(self.root / ".gitignore", ".cache/\n.worktrees/\n__pycache__/\n")
        delivery.pstack.bake(self.root)
        commit(self.root)
        git(self.base, "init", "--bare", str(self.origin))
        git(self.root, "remote", "add", "origin", str(self.origin))
        git(self.root, "push", "--set-upstream", "origin", "main")
        git(self.origin, "symbolic-ref", "HEAD", "refs/heads/main")
        self.message_file = self.base / "message.txt"
        self.message_file.write_text("Update reviewed upstream\n\n" + LEAD + "\n" + delivery.REVIEWER + "\n")

    def producer(self):
        producer = self.base / "producer"
        git(self.base, "clone", str(self.origin), str(producer))
        git(producer, "config", "user.name", "Test")
        git(producer, "config", "user.email", "test@example.invalid")
        return producer

    def candidate(self, bump=True):
        write(self.source / "pstack/LICENSE", "MIT fixture next revision\n")
        commit(self.source)
        result = delivery.pstack.prepare_sync(self.root)
        candidate = Path(result["worktree"])
        if bump:
            delivery.pstack.bump_version(candidate)
        delivery.pstack.bake(candidate)
        git(candidate, "add", ".")
        return candidate, git(candidate, "write-tree")

    def publish(self, candidate, tree):
        return delivery.publish(self.root, candidate, tree, self.message_file, LEAD)

    def test_fast_forward_refresh_updates_only_primary_and_preserves_branch(self):
        before = git(self.root, "rev-parse", "HEAD")
        producer = self.producer()
        write(producer / "README.md", "Published documentation.\n")
        commit(producer)
        git(producer, "push", "origin", "main")
        with delivery.pstack.sync_lock(self.root):
            result = delivery.refresh_primary(self.root)
        self.assertEqual(result["status"], "updated")
        self.assertEqual(result["before"], before)
        self.assertEqual(git(self.root, "branch", "--show-current"), "main")
        self.assertEqual((self.root / "README.md").read_text(), "Published documentation.\n")
        self.assertFalse(git(self.root, "status", "--porcelain"))

    def test_dirty_main_and_source_are_preserved_before_fetch(self):
        before = git(self.root, "rev-parse", "HEAD")
        write(self.root / "unknown.txt", "Preserve me.\n")
        with self.assertRaisesRegex(delivery.DeliveryError, "Preserve"):
            delivery.refresh_primary(self.root)
        self.assertEqual(git(self.root, "rev-parse", "HEAD"), before)
        (self.root / "unknown.txt").unlink()
        module = self.root / delivery.pstack.SUBMODULE
        write(module / "pstack/LICENSE", "Local edit.\n")
        with self.assertRaisesRegex(delivery.DeliveryError, "Preserve"):
            delivery.refresh_primary(self.root)
        self.assertEqual((module / "pstack/LICENSE").read_text(), "Local edit.\n")

    def test_ignored_source_files_are_preserved_before_update(self):
        module = self.root / delivery.pstack.SUBMODULE
        info = Path(git(module, "rev-parse", "--absolute-git-dir")) / "info/exclude"
        write(info, "private.note\n")
        write(module / "private.note", "Keep this.\n")
        with self.assertRaisesRegex(delivery.DeliveryError, "Preserve"):
            delivery.refresh_primary(self.root)
        self.assertEqual((module / "private.note").read_text(), "Keep this.\n")

    def test_diverged_primary_preserves_both_histories(self):
        producer = self.producer()
        write(producer / "remote.txt", "Remote.\n")
        commit(producer)
        git(producer, "push", "origin", "main")
        write(self.root / "local.txt", "Local.\n")
        commit(self.root)
        before = git(self.root, "rev-parse", "HEAD")
        with self.assertRaisesRegex(delivery.DeliveryError, "ahead of or diverged"):
            delivery.refresh_primary(self.root)
        self.assertEqual(git(self.root, "rev-parse", "HEAD"), before)
        self.assertTrue((self.root / "local.txt").exists())

    def test_refresh_preserves_ignored_files_that_incoming_git_would_replace(self):
        producer = self.producer()
        write(producer / "incoming.note", "Remote file.\n")
        commit(producer)
        git(producer, "push", "origin", "main")
        write(self.root / ".git/info/exclude", "incoming.note\n")
        write(self.root / "incoming.note", "Private ignored file.\n")
        with self.assertRaisesRegex(delivery.DeliveryError, "overlap local ignored work"):
            delivery.refresh_primary(self.root)
        self.assertEqual((self.root / "incoming.note").read_text(), "Private ignored file.\n")

    def test_fast_forward_refresh_moves_an_initialized_source_to_new_pin(self):
        candidate, _ = self.candidate()
        commit(candidate)
        git(candidate, "push", "origin", "HEAD:refs/heads/main")
        before = git(self.root / delivery.pstack.SUBMODULE, "rev-parse", "HEAD")
        result = delivery.refresh_primary(self.root)
        self.assertEqual(result["status"], "updated")
        self.assertNotEqual(git(self.root / delivery.pstack.SUBMODULE, "rev-parse", "HEAD"), before)
        self.assertEqual(git(self.root / delivery.pstack.SUBMODULE, "rev-parse", "HEAD"),
                         git(self.source, "rev-parse", "HEAD"))
        self.assertFalse(git(self.root, "status", "--porcelain"))

    def native_results(self, installed=True):
        return [{"marketplaces": [{"name": "starch-rival", "marketplaceSource": {"sourceType": "git"}}]},
                {"installed": [{"name": "starch-rival", "marketplaceName": "starch-rival",
                                 "installed": installed}]}, {"upgraded": ["starch-rival"]}]

    def test_native_refresh_happens_for_unchanged_and_pending_upstream(self):
        for status in ("unchanged", "candidate_pending"):
            with self.subTest(status=status), mock.patch.object(delivery.shutil, "which", return_value="/fixture/codex"), \
                    mock.patch.object(delivery, "json_command", side_effect=self.native_results()) as cli, \
                    mock.patch.object(delivery.pstack, "check", return_value={"status": status, "wakeAgent": False}):
                result = delivery.precheck(self.root)
                self.assertEqual(result["status"], status)
                self.assertFalse(result["wakeAgent"])
                self.assertEqual(result["codex_refresh"]["status"], "refreshed")
                self.assertEqual(cli.call_args.args[2:], ("plugin", "marketplace", "upgrade", "starch-rival", "--json"))

    def test_precheck_releases_lock_before_pstack_check(self):
        def check(root):
            with delivery.pstack.sync_lock(root):
                return {"status": "unchanged", "wakeAgent": False}
        with mock.patch.object(delivery, "refresh_codex", return_value={"status": "skipped"}), \
                mock.patch.object(delivery.pstack, "check", side_effect=check):
            self.assertFalse(delivery.precheck(self.root)["wakeAgent"])

    def test_native_refresh_skips_missing_cli_unconfigured_and_uninstalled(self):
        with mock.patch.object(delivery.shutil, "which", return_value=None):
            self.assertEqual(delivery.refresh_codex(self.root)["reason"], "codex_cli_unavailable")
        with mock.patch.object(delivery.shutil, "which", return_value="codex"), \
                mock.patch.object(delivery, "json_command", return_value={"marketplaces": []}) as cli:
            self.assertEqual(delivery.refresh_codex(self.root)["reason"], "marketplace_unconfigured")
            self.assertEqual(cli.call_count, 1)
        with mock.patch.object(delivery.shutil, "which", return_value="codex"), \
                mock.patch.object(delivery, "json_command", side_effect=self.native_results(False)[:2]) as cli:
            self.assertEqual(delivery.refresh_codex(self.root)["reason"], "plugin_not_installed")
            self.assertEqual(cli.call_count, 2)

    def test_native_failure_is_not_reported_as_unchanged(self):
        with mock.patch.object(delivery, "refresh_codex", side_effect=delivery.DeliveryError("CLI failed")), \
                mock.patch.object(delivery.pstack, "check") as check:
            with self.assertRaisesRegex(delivery.DeliveryError, "CLI failed") as failure:
                delivery.precheck(self.root)
            self.assertEqual(failure.exception.state["repository_refresh"]["status"], "unchanged")
            check.assert_not_called()

    def test_cli_errors_are_one_json_line_and_nonzero(self):
        output = io.StringIO()
        with mock.patch.object(sys, "argv", ["delivery.py", "precheck"]), \
                mock.patch.object(delivery, "precheck", side_effect=delivery.DeliveryError("fetch failed")), \
                contextlib.redirect_stdout(output):
            code = delivery.main()
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output.getvalue()), {"status": "error", "error": "fetch failed"})
        self.assertEqual(len(output.getvalue().splitlines()), 1)

    def test_stale_reviewed_tree_and_unknown_candidate_reject_publication(self):
        candidate, tree = self.candidate()
        before = git(self.root, "rev-parse", "HEAD")
        with self.assertRaisesRegex(delivery.DeliveryError, "reviewed Git tree"):
            self.publish(candidate, "0" * 40)
        with self.assertRaisesRegex(delivery.DeliveryError, "registered upstream candidate"):
            self.publish(self.root, tree)
        self.assertEqual(git(self.root, "rev-parse", "HEAD"), before)

    def test_unstaged_or_untracked_candidate_changes_are_preserved(self):
        candidate, tree = self.candidate()
        write(candidate / "untracked.txt", "Keep.\n")
        with self.assertRaisesRegex(delivery.DeliveryError, "untracked"):
            self.publish(candidate, tree)
        (candidate / "untracked.txt").unlink()
        write(candidate / delivery.pstack.BAKING / "release.json", '{"version":"9.0.0"}')
        with self.assertRaisesRegex(delivery.DeliveryError, "unstaged"):
            self.publish(candidate, tree)
        self.assertTrue(candidate.exists())

    def test_release_version_and_review_trailer_are_required(self):
        candidate, tree = self.candidate(bump=False)
        with self.assertRaisesRegex(delivery.DeliveryError, "newer than primary"):
            self.publish(candidate, tree)
        self.message_file.write_text("Update\n\n" + LEAD + "\n")
        with self.assertRaisesRegex(delivery.DeliveryError, "Claude Sonnet 5.5"):
            self.publish(candidate, tree)
        self.message_file.write_text("Update\n\n" + LEAD + "\n" + delivery.REVIEWER + "\nOther: trailing\n")
        with self.assertRaisesRegex(delivery.DeliveryError, "final contiguous"):
            self.publish(candidate, tree)

    def test_updated_base_requires_reconciliation_and_new_review(self):
        candidate, tree = self.candidate()
        producer = self.producer()
        write(producer / "README.md", "Concurrent update.\n")
        commit(producer)
        git(producer, "push", "origin", "main")
        with self.assertRaisesRegex(delivery.DeliveryError, "reconcile and obtain review again"):
            self.publish(candidate, tree)
        self.assertTrue(git(candidate, "diff", "--cached", "--name-only"))

    def test_successful_publication_commits_exact_reviewed_tree_and_pushes_main_only(self):
        candidate, tree = self.candidate()
        result = self.publish(candidate, tree)
        self.assertEqual(result["status"], "published")
        self.assertTrue(result["published"])
        self.assertTrue(result["cleanup_pending"])
        self.assertEqual(git(self.root, "rev-parse", "HEAD^{tree}"), tree)
        self.assertEqual(git(self.root, "rev-parse", "HEAD"), git(self.origin, "rev-parse", "main"))
        self.assertEqual(git(self.origin, "for-each-ref", "--format=%(refname)", "refs/heads"), "refs/heads/main")
        self.assertFalse(git(self.root, "status", "--porcelain"))
        self.assertEqual(result["integrated_safety"]["tests_run"], 1)
        self.assertTrue(candidate.exists())
        self.assertEqual(git(self.root / delivery.pstack.SUBMODULE, "rev-parse", "HEAD"),
                         git(self.source, "rev-parse", "HEAD"))

    def test_push_failure_preserves_integrated_commit_and_explicit_phase(self):
        candidate, tree = self.candidate()
        original = delivery.git
        def fail_push(root, *args):
            if args[:1] == ("push",):
                raise delivery.DeliveryError("network unavailable")
            return original(root, *args)
        with mock.patch.object(delivery, "git", side_effect=fail_push):
            with self.assertRaisesRegex(delivery.DeliveryError, "network unavailable") as failure:
                self.publish(candidate, tree)
        self.assertFalse(failure.exception.state["published"])
        self.assertEqual(failure.exception.state["phase"], "integrated")
        self.assertEqual(git(self.root, "rev-parse", "HEAD^{tree}"), tree)
        self.assertNotEqual(git(self.root, "rev-parse", "HEAD"), git(self.origin, "rev-parse", "main"))
        self.assertTrue(candidate.exists())

    def test_publication_executes_each_checkouts_reviewed_validator(self):
        candidate, _ = self.candidate()
        script = candidate / delivery.pstack.BAKING / "scripts/pstack.py"
        original = script.read_text()
        before = 'return {"status": "valid", "skills_checked": count'
        self.assertEqual(original.count(before), 1)
        script.write_text(original.replace(before,
                          'return {"status": "valid", "validator_checkout": str(root), "skills_checked": count'))
        delivery.pstack.bake(candidate)
        git(candidate, "add", ".")
        result = self.publish(candidate, git(candidate, "write-tree"))
        self.assertEqual(result["candidate_validation"]["validator_checkout"], str(candidate))
        self.assertEqual(result["integrated_validation"]["validator_checkout"], str(self.root))

    def test_commit_hook_cannot_publish_contents_outside_the_reviewed_tree(self):
        candidate, tree = self.candidate()
        hook = self.root / ".git/hooks/pre-commit"
        write(hook, "#!/bin/sh\nprintf 'Hook injected change\\n' > injected.txt\ngit add injected.txt\n")
        hook.chmod(0o755)
        before = git(self.root, "rev-parse", "HEAD")
        with self.assertRaisesRegex(delivery.DeliveryError, "Committed contents or message differ") as failure:
            self.publish(candidate, tree)
        self.assertEqual(failure.exception.state["phase"], "candidate_committed")
        self.assertFalse(failure.exception.state["published"])
        self.assertEqual(git(self.root, "rev-parse", "HEAD"), before)
        self.assertTrue((candidate / "injected.txt").exists())

    def test_matching_baseline_failures_are_distinguished_from_regressions(self):
        red = {"tests_run": 1, "successful": False, "failures": [{"test": "t.x", "detail": "same assertion"}],
               "errors": [], "skips": []}
        with mock.patch.object(delivery, "run_safety", side_effect=[red, red]):
            self.assertTrue(delivery.safety_with_baseline(self.root, self.root)["preexisting_failures_only"])
        baseline = {**red, "failures": [{"test": "t.x", "detail": "different assertion"}]}
        with mock.patch.object(delivery, "run_safety", side_effect=[red, baseline]):
            with self.assertRaisesRegex(delivery.DeliveryError, "new or worsened"):
                delivery.safety_with_baseline(self.root, self.root)


if __name__ == "__main__":
    unittest.main()
