#!/usr/bin/env python3
"""Refresh native distribution and publish agent-reviewed Starch Rival updates.

The caller owns model review; a reviewed Git tree binds publication to the
contents that caller reviewed. Origin: the 2026-10-15 native-update task.
No command installs a plugin or changes a scheduler or user model settings.
"""

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pstack


REVIEWER = "Co-authored-by: Claude Sonnet 5.5 <noreply@anthropic.com>"


class DeliveryError(pstack.PortError):
    def __init__(self, message, **state):
        super().__init__(message)
        self.state = state


def command(root, *argv, input=None):
    result = subprocess.run(argv, cwd=root, input=input, text=True, capture_output=True)
    if result.returncode:
        raise DeliveryError("Command failed: " + " ".join(argv),
                            detail=(result.stderr or result.stdout).strip()[-12000:])
    return result.stdout.strip()


def git(root, *args):
    return command(root, "git", *args)


def ancestor(root, before, after):
    result = subprocess.run(["git", "merge-base", "--is-ancestor", before, after],
                            cwd=root, capture_output=True, text=True)
    if result.returncode not in (0, 1):
        raise DeliveryError("Cannot compare Git history", detail=result.stderr.strip())
    return result.returncode == 0


def clean_module(root):
    module = root / pstack.SUBMODULE
    if not (module / ".git").exists():
        return False
    # Include ignored files: checkout could otherwise silently replace one
    # when the incoming upstream revision starts tracking that path.
    if (git(module, "status", "--porcelain", "--untracked-files=all", "--ignore-submodules=none")
            or git(module, "ls-files", "--others", "--ignored", "--exclude-standard")):
        raise DeliveryError("Preserve local source-submodule work before delivery", worktree=str(root))
    return True


def primary_clean(root):
    if (pstack.maintenance_root(root) != root.resolve()
            or git(root, "branch", "--show-current") != "main"):
        raise DeliveryError("Delivery requires the primary checkout on main")
    if git(root, "status", "--porcelain", "--untracked-files=all", "--ignore-submodules=none"):
        raise DeliveryError("Preserve the primary checkout's changes before delivery", worktree=str(root))
    return clean_module(root)


def update_module(root):
    git(root, "submodule", "update", "--init", "--", str(pstack.SUBMODULE))
    clean_module(root)


def refresh_primary(root):
    """Called under the shared lock; only advance the tracked origin/main."""
    initialized = primary_clean(root)
    if git(root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}") != "origin/main":
        raise DeliveryError("main must track origin/main before automatic refresh")
    before = git(root, "rev-parse", "HEAD")
    git(root, "fetch", "--quiet", "--no-tags", "origin", "+refs/heads/main:refs/remotes/origin/main")
    remote = git(root, "rev-parse", "refs/remotes/origin/main")
    if not ancestor(root, before, remote):
        raise DeliveryError("main is ahead of or diverged from origin/main; preserve and reconcile it",
                            local_commit=before, remote_commit=remote)
    tracked = set(git(root, "ls-files", "-z").split("\0"))
    incoming = git(root, "diff", "--name-only", "-z", before, remote).split("\0")
    if any(name and name not in tracked and ((root / name).exists() or (root / name).is_symlink())
           for name in incoming):
        raise DeliveryError("Incoming files overlap local ignored work; preserve it before refreshing")
    git(root, "-c", "submodule.recurse=false", "merge", "--ff-only", "refs/remotes/origin/main")
    if initialized:
        update_module(root)
    primary_clean(root)
    return {"status": "updated" if before != remote else "unchanged",
            "before": before, "commit": remote,
            "source": "updated" if initialized else "uninitialized_preserved"}


def json_command(root, *argv):
    try:
        return json.loads(command(root, *argv))
    except ValueError as error:
        raise DeliveryError("Expected JSON from " + " ".join(argv)) from error


def validate_checkout(root):
    # A candidate may deliberately change its baker/validation behavior. Run
    # the reviewed checkout's implementation, rather than this process's
    # pre-refresh pstack import, both before and after integration.
    result = json_command(root, sys.executable,
                          str(root / pstack.BAKING / "scripts/pstack.py"), "validate", "--tracked")
    if not isinstance(result, dict) or result.get("status") != "valid" or result.get("tracked") is not True:
        raise DeliveryError("Checkout validator did not confirm tracked publication contents", worktree=str(root))
    return result


def refresh_codex(root):
    executable = shutil.which("codex")
    if not executable:
        return {"status": "skipped", "reason": "codex_cli_unavailable"}
    marketplaces = json_command(root, executable, "plugin", "marketplace", "list", "--json")
    if not isinstance(marketplaces, dict) or not isinstance(marketplaces.get("marketplaces"), list):
        raise DeliveryError("Unexpected Codex marketplace list schema")
    matches = [entry for entry in marketplaces["marketplaces"]
               if isinstance(entry, dict) and entry.get("name") == pstack.PLUGIN_NAME]
    if not matches:
        return {"status": "skipped", "reason": "marketplace_unconfigured"}
    if (len(matches) != 1 or not isinstance(matches[0].get("marketplaceSource"), dict)
            or matches[0]["marketplaceSource"].get("sourceType") != "git"):
        return {"status": "skipped", "reason": "marketplace_is_not_git"}
    plugins = json_command(root, executable, "plugin", "list", "--json")
    if not isinstance(plugins, dict) or not isinstance(plugins.get("installed"), list):
        raise DeliveryError("Unexpected Codex plugin list schema")
    installed = [entry for entry in plugins["installed"] if isinstance(entry, dict)
                 and entry.get("name") == pstack.PLUGIN_NAME
                 and entry.get("marketplaceName") == pstack.PLUGIN_NAME
                 and entry.get("installed") is True]
    if not installed:
        return {"status": "skipped", "reason": "plugin_not_installed"}
    result = json_command(root, executable, "plugin", "marketplace", "upgrade", pstack.PLUGIN_NAME, "--json")
    return {"status": "refreshed", "marketplace": pstack.PLUGIN_NAME, "result": result}


def precheck(root):
    root = pstack.maintenance_root(root)
    details = {}
    try:
        with pstack.sync_lock(root):
            details["repository_refresh"] = refresh_primary(root)
            # Distribution is independent of canonical pstack changes. Always
            # refresh before asking check() whether an adaptation agent is needed.
            details["codex_refresh"] = refresh_codex(root)
        # check() owns the same non-reentrant lock. Do not hold it recursively.
        return {**pstack.check(root), **details}
    except (pstack.PortError, OSError, ValueError) as error:
        raise DeliveryError(str(error), **{**details, **getattr(error, "state", {})}) from error


def candidate_ready(root, candidate, reviewed_tree):
    candidate = candidate.resolve()
    manifest = pstack.read_manifest(candidate)
    expected, branch = pstack.candidate_location(root, manifest)
    if candidate != expected.resolve():
        raise DeliveryError("Only the registered upstream candidate can be published")
    registrations = git(root, "worktree", "list", "--porcelain").split("\n\n")
    if not any("worktree " + str(candidate) in entry.splitlines()
               and "branch refs/heads/" + branch in entry.splitlines() for entry in registrations):
        raise DeliveryError("Candidate is not registered on its expected task branch")
    if git(candidate, "branch", "--show-current") != branch:
        raise DeliveryError("Candidate is not on its expected task branch")
    if git(candidate, "diff", "--name-only", "--ignore-submodules=none"):
        raise DeliveryError("Candidate has unstaged tracked changes; stage the final reviewed contents")
    if git(candidate, "ls-files", "--others", "--exclude-standard"):
        raise DeliveryError("Candidate has untracked files; preserve or account for them before publication")
    if not clean_module(candidate):
        raise DeliveryError("Initialize the candidate source before publication")
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", reviewed_tree):
        raise DeliveryError("reviewed-tree must be a complete Git tree object ID")
    actual = git(candidate, "write-tree")
    if actual != reviewed_tree:
        raise DeliveryError("Staged candidate differs from the reviewed Git tree", reviewed_tree=reviewed_tree,
                            staged_tree=actual)
    return candidate


def commit_message(root, message_file, lead_coauthor):
    message = message_file.read_text()
    lines = message.rstrip().splitlines()
    if (not re.fullmatch(r"Co-authored-by: [^<>\n]+ <[^<>\s]+>", lead_coauthor)
            or lead_coauthor == REVIEWER):
        raise DeliveryError("Declare the lead model's exact Co-authored-by trailer")
    start = len(lines)
    while start and lines[start - 1].startswith("Co-authored-by: "):
        start -= 1
    block = lines[start:]
    if (start == 0 or lines[start - 1] != "" or REVIEWER not in block or lead_coauthor not in block
            or any(not re.fullmatch(r"Co-authored-by: [^<>\n]+ <[^<>\s]+>", line) for line in block)
            or any(line.startswith("Co-authored-by:") for line in lines[:start])):
        raise DeliveryError("Commit message needs a final contiguous co-author block with the lead and Claude Sonnet 5.5")
    parsed = command(root, "git", "interpret-trailers", "--parse", input=message).splitlines()
    if any(trailer not in parsed for trailer in block):
        raise DeliveryError("git interpret-trailers did not parse every intended co-author")
    return message


# The child emits machine-readable identities and normalized traceback text.
# unittest's standard runner reports the human summary on stderr separately.
SAFETY_RUNNER = r'''
import json, pathlib, sys, unittest
root = pathlib.Path(sys.argv[1]).resolve()
suite = unittest.defaultTestLoader.discover(str(root / "automation/baking/tests"))
result = unittest.TextTestRunner(verbosity=1).run(suite)
def entries(values):
    return [{"test": test.id(), "detail": detail.replace(str(root), "<checkout>")}
            for test, detail in values]
print(json.dumps({"tests_run": result.testsRun, "failures": entries(result.failures),
                  "errors": entries(result.errors), "skips": entries(result.skipped),
                  "unexpected_successes": [{"test": test.id(), "detail": "unexpected success"}
                                            for test in result.unexpectedSuccesses],
                  "expected_failures": entries(result.expectedFailures),
                  "successful": result.wasSuccessful()}))
'''


def run_safety(root):
    output = command(root, sys.executable, "-c", SAFETY_RUNNER, str(root))
    try:
        result = json.loads(output.splitlines()[-1])
    except (ValueError, IndexError) as error:
        raise DeliveryError("Safety suite did not produce its result summary") from error
    if not isinstance(result.get("tests_run"), int) or result["tests_run"] <= 0:
        raise DeliveryError("Safety suite discovered no tests")
    return result


def safety_with_baseline(root, candidate):
    result = run_safety(candidate)
    if result["successful"]:
        return {"candidate": result}
    baseline = run_safety(root)
    kinds = ("failures", "errors", "unexpected_successes")
    known = {(kind, item["test"], item["detail"]) for kind in kinds
             for item in baseline.get(kind, [])}
    new = [{"kind": kind, **item} for kind in kinds
           for item in result.get(kind, []) if (kind, item["test"], item["detail"]) not in known]
    if new:
        raise DeliveryError("Candidate has new or worsened safety failures", new_failures=new,
                            candidate_safety=result, baseline_safety=baseline)
    return {"candidate": result, "baseline": baseline, "preexisting_failures_only": True}


def publish(root, candidate, reviewed_tree, message_file, lead_coauthor):
    root = pstack.maintenance_root(root)
    state = {"published": False, "candidate": str(candidate.resolve()), "phase": "preflight"}
    try:
        with pstack.sync_lock(root):
            primary_clean(root)
            candidate = candidate_ready(root, candidate, reviewed_tree)
            message = commit_message(candidate, message_file, lead_coauthor)
            state["repository_refresh"] = refresh_primary(root)
            if not ancestor(root, git(root, "rev-parse", "HEAD"), git(candidate, "rev-parse", "HEAD")):
                raise DeliveryError("The updated primary base is not an ancestor of the candidate; reconcile and obtain review again")
            version = pstack.read_release(candidate)["version"]
            previous = pstack.read_release(root)["version"]
            if tuple(map(int, version.split("."))) <= tuple(map(int, previous.split("."))):
                raise DeliveryError("Candidate release version must be newer than primary", version=version,
                                    primary_version=previous)
            state.update(phase="candidate_validation", version=version)
            state["candidate_validation"] = validate_checkout(candidate)
            state["safety"] = safety_with_baseline(root, candidate)
            candidate_ready(root, candidate, reviewed_tree)
            # Feed the exact inspected bytes, avoiding message-file TOCTOU or
            # accidental literal shell escapes in multiline descriptions.
            command(candidate, "git", "commit", "--cleanup=verbatim", "--file=-", input=message)
            commit = git(candidate, "rev-parse", "HEAD")
            state.update(phase="candidate_committed", commit=commit)
            if (git(candidate, "rev-parse", "HEAD^{tree}") != reviewed_tree
                    or git(candidate, "show", "--format=%B", "--no-patch", "HEAD") != message.rstrip()):
                raise DeliveryError("Committed contents or message differ from the reviewed inputs; preserve and inspect the candidate")
            primary_clean(root)
            git(root, "-c", "submodule.recurse=false", "merge", "--ff-only", commit)
            state["phase"] = "integrated"
            update_module(root)
            primary_clean(root)
            state["integrated_validation"] = validate_checkout(root)
            integrated = run_safety(root)
            state["integrated_safety"] = integrated
            candidate_result = state["safety"]["candidate"]
            kinds = ("failures", "errors", "unexpected_successes")
            expected = {(kind, item["test"], item["detail"]) for kind in kinds
                        for item in candidate_result.get(kind, [])}
            if any((kind, item["test"], item["detail"]) not in expected
                   for kind in kinds for item in integrated.get(kind, [])):
                raise DeliveryError("Post-integration safety has a new or worsened failure")
            primary_clean(root)
            if git(root, "rev-parse", "HEAD") != commit:
                raise DeliveryError("Primary changed during publication; preserve and inspect it")
            git(root, "push", "origin", "HEAD:refs/heads/main")
            state.update(status="published", phase="pushed", published=True, cleanup_pending=True,
                         cleanup_reason="Candidate retained until its ignored and generated files are accounted for")
            return state
    except (pstack.PortError, OSError, ValueError) as error:
        raise DeliveryError(str(error), **{**state, **getattr(error, "state", {})}) from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("precheck")
    publisher = commands.add_parser("publish")
    publisher.add_argument("--candidate", type=Path, required=True)
    publisher.add_argument("--reviewed-tree", required=True)
    publisher.add_argument("--message-file", type=Path, required=True)
    publisher.add_argument("--lead-coauthor", required=True)
    args = parser.parse_args()
    try:
        if args.command == "precheck":
            result = precheck(pstack.ROOT)
        else:
            result = publish(pstack.ROOT, args.candidate, args.reviewed_tree,
                             args.message_file, args.lead_coauthor)
        print(json.dumps(result, separators=(",", ":")))
        return 0
    except (pstack.PortError, OSError, ValueError) as error:
        print(json.dumps({"status": "error", "error": str(error),
                          **getattr(error, "state", {})}, separators=(",", ":")))
        return 1


if __name__ == "__main__":
    sys.exit(main())
