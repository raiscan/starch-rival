#!/usr/bin/env python3
"""Bake tracked pstack packages, install them, and prepare upstream candidates.

Inputs live under automation/baking/; codex/ and claude/ are the baked packages.
Origin: the 2026-10-15 task to port poteto's pstack with Sonnet 5.5 review.
Sync preparation never installs a candidate or executes downloaded scripts.
"""

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
import uuid

import yaml


ROOT = Path(__file__).resolve().parents[3]
BAKING = Path("automation/baking")
SUBMODULE = BAKING / "upstream"
HARNESSES = ("codex", "claude")
CODEX_FIELDS = {"name", "description", "license", "allowed-tools", "metadata"}
MODEL_PATH = "~/.config/pstack/models.md"
OLD_MODEL_PATH = "~/.cursor/rules/pstack-models.mdc"
PLUGIN_NAME = "starch-rival"
PLUGIN_HOME = "https://github.com/raiscan/starch-rival"
MARKETPLACES = {
    "codex": Path(".agents/plugins/marketplace.json"),
    "claude": Path(".claude-plugin/marketplace.json"),
}
ADAPTER = (
    "\n\n## Local harness adapter\n\n"
    "Read [PORT.md](../../PORT.md) before applying Cursor-specific tool, model, "
    "or setup instructions. It also defines this port's Sonnet 5.5 reviewer. "
    "User, repository, and live tool instructions take precedence.\n\n"
)


class PortError(Exception):
    pass


def git(root, *args, binary=False):
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=not binary,
    )
    if result.returncode:
        detail = result.stderr.decode() if binary else result.stderr
        raise PortError(detail.strip())
    return result.stdout if binary else result.stdout.strip()


def read_manifest(root):
    value = json.loads((root / BAKING / "upstream.json").read_text())
    for field in ("repository", "ref", "path", "commit", "tree"):
        if not isinstance(value.get(field), str) or not value[field]:
            raise PortError("Invalid upstream manifest field: " + field)
    path = PurePosixPath(value["path"])
    if path.is_absolute() or ".." in path.parts or value["path"].startswith("-"):
        raise PortError("Upstream path must be relative to the source repository")
    return value


def read_release(root):
    value = json.loads((root / BAKING / "release.json").read_text())
    if (not isinstance(value, dict) or set(value) != {"version"}
            or not isinstance(value["version"], str)
            or not re.fullmatch(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)", value["version"])):
        raise PortError("release.json must contain one MAJOR.MINOR.PATCH version")
    return value


def bump_version(root, version=None):
    previous = read_release(root)["version"]
    parts = tuple(int(part) for part in previous.split("."))
    version = version or ".".join(map(str, (*parts[:2], parts[2] + 1)))
    if (not isinstance(version, str)
            or not re.fullmatch(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)", version)
            or tuple(int(part) for part in version.split(".")) <= parts):
        raise PortError("The new release version must be a newer MAJOR.MINOR.PATCH version")
    (root / BAKING / "release.json").write_text(json.dumps({"version": version}, indent=2) + "\n")
    return {"status": "version_bumped", "previous_version": previous, "version": version}


def marketplace(harness):
    if harness == "codex":
        return {"name": PLUGIN_NAME, "interface": {"displayName": "Starch Rival"}, "plugins": [{
            "name": PLUGIN_NAME, "source": {"source": "local", "path": "./codex"},
            "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
            "category": "Productivity",
        }]}
    return {"name": PLUGIN_NAME, "owner": {"name": "raiscan"},
            "description": "Starch Rival, an unofficial port of poteto's pstack for Codex and Claude Code.",
            "plugins": [{"name": PLUGIN_NAME, "source": "./claude"}]}


def plugin_manifests(root, harness):
    upstream = read_manifest(root)
    original = json.loads((source_root(root) / "plugin.json").read_text())
    common = {
        "name": PLUGIN_NAME, "version": read_release(root)["version"],
        "description": "Starch Rival: an unofficial port of Lauren Tan (poteto)'s pstack workflows.",
        "author": {"name": "raiscan", "url": "https://github.com/raiscan"},
        "homepage": PLUGIN_HOME, "repository": PLUGIN_HOME,
        "license": original["license"],
        "keywords": list(dict.fromkeys([PLUGIN_NAME, *original.get("keywords", [])])),
    }
    portable = {**original, **common}
    portable["extensions"] = {**original.get("extensions", {}), "com.github.raiscan.starch-rival": {
        "upstream": {**upstream, "name": original["name"], "version": original.get("version"),
                     "author": original.get("author"), "homepage": original.get("homepage")},
    }}
    native = {**common, "skills": "./skills/"}
    if harness == "codex":
        native["interface"] = {"displayName": "Starch Rival", "developerName": "raiscan"}
    else:
        # Replaces Claude's default agents/ scan. Those verbatim Cursor agents
        # remain supporting references, not registered native Claude agents.
        native["agents"] = []
    return {Path("plugin.json"): portable, Path("." + harness + "-plugin/plugin.json"): native}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def object_hash(kind, body):
    return hashlib.sha1(kind.encode() + b" " + str(len(body)).encode() + b"\0" + body).digest()


def tree_hash(directory):
    entries = []
    for path in directory.iterdir():
        if path.is_symlink():
            raise PortError("Snapshot symlinks are unsupported: " + str(path))
        if path.is_dir():
            mode, digest, key = b"40000", bytes.fromhex(tree_hash(path)), os.fsencode(path.name) + b"/"
        elif path.is_file():
            mode = b"100755" if path.stat().st_mode & 0o111 else b"100644"
            digest, key = object_hash("blob", path.read_bytes()), os.fsencode(path.name)
        else:
            raise PortError("Unsupported snapshot entry: " + str(path))
        entries.append((key, mode + b" " + os.fsencode(path.name) + b"\0" + digest))
    return object_hash("tree", b"".join(body for _, body in sorted(entries))).hex()


def source_root(root):
    return root / SUBMODULE / read_manifest(root)["path"]


def source_manifest(root):
    manifest = read_manifest(root)
    module = root / SUBMODULE
    entry = git(root, "ls-files", "--stage", "--", str(SUBMODULE)).splitlines()
    expected = "160000 " + manifest["commit"] + " 0\t" + str(SUBMODULE)
    if entry != [expected]:
        raise PortError("The upstream gitlink must match upstream.json; stage the reconciled submodule pin")
    if git(root, "config", "--file", ".gitmodules", "submodule.upstream.url") != manifest["repository"]:
        raise PortError("The upstream submodule URL must match upstream.json")
    if git(root, "config", "--file", ".gitmodules", "submodule.upstream.path") != str(SUBMODULE):
        raise PortError("The upstream submodule path must be " + str(SUBMODULE))
    if not (module / ".git").exists():
        raise PortError("Initialize the source with: git submodule update --init -- " + str(SUBMODULE))
    if Path(git(module, "rev-parse", "--show-toplevel")).resolve() != module.resolve():
        raise PortError("Initialize the source with: git submodule update --init -- " + str(SUBMODULE))
    if git(module, "rev-parse", "HEAD") != manifest["commit"]:
        raise PortError("The upstream submodule HEAD differs from upstream.json; preserve local work, then run git submodule update --init -- " + str(SUBMODULE))
    if git(module, "rev-parse", "HEAD:" + manifest["path"]) != manifest["tree"]:
        raise PortError("The manifest subtree must match the pinned upstream commit")
    if tree_hash(source_root(root)) != manifest["tree"]:
        raise PortError(str(SUBMODULE) + "/pstack/ differs from its pinned Git tree; reconcile the source first")
    return manifest


def fingerprint(root):
    value = hashlib.sha256()
    for base in (source_root(root), root / BAKING / "port", root / BAKING / "scripts"):
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                value.update(str(path.relative_to(root)).encode() + b"\0" + path.read_bytes() + b"\0")
    for name in ("upstream.json", "release.json"):
        value.update((root / BAKING / name).read_bytes())
    return value.hexdigest()


def split_skill(text):
    match = re.match(r"\A---\n(.*?)\n---(?:\n|\Z)", text, re.DOTALL)
    if not match:
        raise PortError("A skill is missing YAML frontmatter")
    front = yaml.safe_load(match.group(1))
    if not isinstance(front, dict) or not isinstance(front.get("description"), str):
        raise PortError("A skill needs mapping frontmatter and a string description")
    return front, text[match.end():].lstrip("\n")


def adapted_body(root, name, body):
    if name == "setup-pstack":
        return (root / BAKING / "port/setup-pstack.md").read_text()
    if name == "interrogate" and (root / BAKING / "port/interrogate-routing.md").exists():
        start = "## Step 3, Spawn Reviewers\n"
        finish = "Read `references/reviewer-prompt.md`"
        if body.count(start) != 1 or body.count(finish) != 1:
            raise PortError("Upstream interrogate routing changed; reconcile the adapter explicitly")
        begin, end = body.index(start), body.index(finish)
        if end < begin:
            raise PortError("Upstream interrogate section boundaries changed")
        body = body[:begin] + (root / BAKING / "port/interrogate-routing.md").read_text() + "\n" + body[end:]
    return body


def bake(root):
    manifest = source_manifest(root)
    release = read_release(root)
    input_id = fingerprint(root)
    cache = root / ".cache"
    cache.mkdir(exist_ok=True)
    count = 0
    for harness in HARNESSES:
        with tempfile.TemporaryDirectory(prefix=".bake-", dir=cache) as temporary:
            output = Path(temporary) / harness
            shutil.copytree(source_root(root), output)
            for path in output.rglob("*.md"):
                path.write_bytes(path.read_bytes().replace(OLD_MODEL_PATH.encode(), MODEL_PATH.encode()))
            shutil.copy2(root / BAKING / "port/PORT.md", output / "PORT.md")
            shutil.copy2(root / BAKING / "port/models.md", output / "models.md")
            skills = sorted((output / "skills").glob("*/SKILL.md"))
            if not skills:
                raise PortError("No upstream skills were found")
            for skill in skills:
                name = skill.parent.name
                if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or len(name) > 64:
                    raise PortError("Unsupported skill directory name: " + name)
                front, body = split_skill(skill.read_text())
                front["name"] = name
                gated = front.get("disable-model-invocation", False)
                if not isinstance(gated, bool):
                    raise PortError("Invocation policy must be boolean: " + name)
                if harness == "codex":
                    front.pop("disable-model-invocation", None)
                    for key in list(front):
                        if key not in CODEX_FIELDS:
                            front.setdefault("metadata", {})["upstream-" + key] = str(front.pop(key))
                    if gated:
                        policy_file = skill.parent / "agents/openai.yaml"
                        policy_file.parent.mkdir(exist_ok=True)
                        policy = yaml.safe_load(policy_file.read_text()) if policy_file.exists() else {}
                        policy.setdefault("policy", {})["allow_implicit_invocation"] = False
                        policy_file.write_text(yaml.safe_dump(policy, sort_keys=False))
                body = adapted_body(root, name, body)
                skill.write_text("---\n" + yaml.safe_dump(front, sort_keys=False, allow_unicode=True) + "---" + ADAPTER + body)
            for relative, value in plugin_manifests(root, harness).items():
                write_json(output / relative, value)
            (output / "port-manifest.json").write_text(json.dumps({
                "upstream": manifest, "input_sha256": input_id, "harness": harness,
                "skills": len(skills), "version": release["version"],
            }, indent=2) + "\n")
            destination = root / harness
            if destination.exists():
                shutil.rmtree(destination)
            output.rename(destination)
            count = len(skills)
        write_json(root / MARKETPLACES[harness], marketplace(harness))
    return {"status": "baked", "skills": count, "harnesses": list(HARNESSES),
            "version": release["version"], "input_sha256": input_id}


def build(root):
    return bake(root)


def validate(root, tracked=False):
    upstream = source_manifest(root)
    release = read_release(root)
    source = source_root(root)
    input_id = fingerprint(root)
    count = 0
    for harness in HARNESSES:
        output = root / harness
        if not (output / "port-manifest.json").is_file():
            raise PortError("Missing baked package " + harness + "; run automation/baking/scripts/pstack.py bake")
        manifest = json.loads((output / "port-manifest.json").read_text())
        if manifest["input_sha256"] != input_id:
            raise PortError("Baked output is stale; run automation/baking/scripts/pstack.py bake and review it")
        expected_files = {path.relative_to(source) for path in source.rglob("*") if path.is_file()}
        generated_manifests = plugin_manifests(root, harness)
        additions = {Path("PORT.md"), Path("models.md"), Path("port-manifest.json"), *generated_manifests}
        skills = sorted((source / "skills").glob("*/SKILL.md"))
        if manifest != {"upstream": upstream, "input_sha256": input_id, "harness": harness,
                        "skills": len(skills), "version": release["version"]}:
            raise PortError("Baked package provenance or version differs: " + harness)
        for relative, expected in generated_manifests.items():
            if json.loads((output / relative).read_text()) != expected:
                raise PortError("Generated plugin manifest differs: " + str(output / relative))
            if relative not in expected_files and (output / relative).stat().st_mode & 0o111:
                raise PortError("Generated plugin metadata must not be executable: " + str(relative))
        if json.loads((root / MARKETPLACES[harness]).read_text()) != marketplace(harness):
            raise PortError("Native marketplace differs: " + str(MARKETPLACES[harness]))
        for path in (output / "port-manifest.json", root / MARKETPLACES[harness]):
            if path.is_symlink() or path.stat().st_mode & 0o111:
                raise PortError("Generated metadata must be a nonexecutable regular file: " + str(path))
        for original in skills:
            name = original.parent.name
            front, actual_body = split_skill((output / "skills" / name / "SKILL.md").read_text())
            upstream_front, upstream_body = split_skill(original.read_text().replace(OLD_MODEL_PATH, MODEL_PATH))
            expected_body = ADAPTER.lstrip("\n") + adapted_body(root, name, upstream_body)
            if actual_body != expected_body:
                raise PortError("Generated skill instructions differ from the defined adaptation: " + name)
            if front["name"] != name or not front["description"]:
                raise PortError("Invalid generated skill metadata: " + name)
            if harness == "codex":
                if set(front) - CODEX_FIELDS:
                    raise PortError("Unsupported Codex frontmatter: " + name)
                if upstream_front.get("disable-model-invocation"):
                    additions.add(Path("skills") / name / "agents/openai.yaml")
                    policy = yaml.safe_load((output / "skills" / name / "agents/openai.yaml").read_text())
                    if policy.get("policy", {}).get("allow_implicit_invocation") is not False:
                        raise PortError("Explicit-only invocation policy lost: " + name)
            elif front.get("disable-model-invocation") != upstream_front.get("disable-model-invocation"):
                raise PortError("Claude invocation policy lost: " + name)
            count += 1
        actual_files = {path.relative_to(output) for path in output.rglob("*") if path.is_file()}
        if actual_files != expected_files | additions:
            raise PortError("Generated support-file inventory differs from the complete upstream package")
        for relative in expected_files:
            original, generated = source / relative, output / relative
            if original.stat().st_mode & 0o111 != generated.stat().st_mode & 0o111:
                raise PortError("Generated executable mode changed: " + str(relative))
            if relative.parts[0] == "skills" and relative.name == "SKILL.md":
                continue
            if relative in generated_manifests:
                continue
            if harness == "codex" and relative.name == "openai.yaml":
                continue
            expected = original.read_bytes()
            if original.suffix == ".md":
                expected = expected.replace(OLD_MODEL_PATH.encode(), MODEL_PATH.encode())
            if generated.read_bytes() != expected:
                raise PortError("Generated support file differs from its defined adaptation: " + str(relative))
        for name in ("PORT.md", "models.md"):
            if (output / name).read_bytes() != (root / BAKING / "port" / name).read_bytes():
                raise PortError("Generated adapter differs: " + name)
    if tracked:
        validate_tracked(root)
    return {"status": "valid", "skills_checked": count, "version": release["version"], "tracked": tracked}


def validate_tracked(root):
    """Match the reviewed working bundles to the actual publication index."""
    expected = {Path(harness) / path.relative_to(root / harness)
                for harness in HARNESSES for path in (root / harness).rglob("*") if path.is_file()}
    expected.update(MARKETPLACES.values())
    expected.add(BAKING / "release.json")
    raw = git(root, "ls-files", "--stage", "-z", "--", *HARNESSES,
              *(str(path) for path in MARKETPLACES.values()), str(BAKING / "release.json"), binary=True)
    entries = {}
    for line in raw.split(b"\0"):
        if not line:
            continue
        metadata, path = line.split(b"\t", 1)
        mode, oid, stage = metadata.decode().split()
        relative = Path(os.fsdecode(path))
        if stage != "0" or relative in entries:
            raise PortError("Unmerged publication entry: " + str(relative))
        entries[relative] = (mode, oid)
    if set(entries) != expected:
        missing = sorted(str(path) for path in expected - set(entries))
        extra = sorted(str(path) for path in set(entries) - expected)
        raise PortError("Publication index inventory differs; stage every baked supporting file"
                        + ("; missing: " + ", ".join(missing) if missing else "")
                        + ("; extra: " + ", ".join(extra) if extra else ""))
    for relative, (mode, oid) in entries.items():
        path = root / relative
        expected_mode = "100755" if path.stat().st_mode & 0o111 else "100644"
        if path.is_symlink() or mode != expected_mode or oid != object_hash("blob", path.read_bytes()).hex():
            raise PortError("Publication index bytes or mode differ; stage the reviewed file: " + str(relative))


def owned_legacy_link(root, link, target):
    if not link.is_symlink():
        return False
    try:
        relative = Path(os.readlink(link)).relative_to(root / ".cache/installed")
    except ValueError:
        return False
    return bool(len(relative.parts) == 4 and re.fullmatch(r"[0-9a-f]{64}", relative.parts[0])
                and relative.parts[1:] == (target, "skills", link.name))


def retire_links(root, targets, home):
    """Retire this checkout's legacy links after native plugins are verified."""
    pending = []
    for target in dict.fromkeys(targets):
        if target not in HARNESSES:
            raise PortError("Unsupported install target: " + target)
        directory = home / ("." + target) / "skills"
        for parent in (directory.parent, directory):
            if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
                raise PortError("Preserve and inspect the foreign skills location: " + str(parent))
        if directory.exists():
            pending.extend(link for link in directory.iterdir() if owned_legacy_link(root, link, target))
    # All targets were inspected before removing the first link. Immutable
    # releases and foreign skills remain in place, including dangling links.
    for link in pending:
        link.unlink()
    return {"status": "legacy_links_retired", "targets": list(dict.fromkeys(targets)),
            "removed_owned_links": len(pending)}


def install(root, targets, home):
    if git(root, "rev-parse", "--git-dir") != ".git":
        raise PortError("Install from the integrated main checkout, not a task worktree")
    if git(root, "branch", "--show-current") != "main" or git(root, "status", "--porcelain"):
        raise PortError("Installation requires the clean, integrated main branch")
    for target in targets:
        if target not in HARNESSES:
            raise PortError("Unsupported install target: " + target)
    validate(root)
    input_id = fingerprint(root)
    release = root / ".cache/installed" / input_id
    names = sorted(path.parent.name for path in (root / "codex/skills").glob("*/SKILL.md"))
    changes = []
    stale = []

    for target in targets:
        source = release / target / "skills"
        destination = home / ("." + target) / "skills"
        for name in names:
            skill = source / name
            link = destination / name
            if link.exists() or link.is_symlink():
                if not owned_legacy_link(root, link, target):
                    raise PortError("Existing skill is not owned by this port: " + str(link))
            if not link.is_symlink() or os.readlink(link) != str(skill):
                changes.append((link, skill))
        if destination.exists():
            for link in destination.iterdir():
                if owned_legacy_link(root, link, target) and link.name not in names:
                    stale.append(link)
    release.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".install-", dir=release.parent) as temporary:
        snapshot = Path(temporary) / "release"
        snapshot.mkdir()
        for target in HARNESSES:
            shutil.copytree(root / target, snapshot / target)
            absolutize_links(snapshot / target, release / target)
        if release.exists():
            if tree_hash(release) != tree_hash(snapshot):
                raise PortError("An installed release was modified; preserve and inspect it: " + str(release))
        else:
            snapshot.rename(release)
    for link, skill in changes:
        link.parent.mkdir(parents=True, exist_ok=True)
        temporary = link.with_name("." + link.name + ".pstack-" + uuid.uuid4().hex)
        try:
            temporary.symlink_to(skill, target_is_directory=True)
            temporary.replace(link)
        finally:
            if temporary.is_symlink():
                temporary.unlink()
    for link in stale:
        link.unlink()
    return {"status": "installed", "targets": targets, "updated_links": len(changes),
            "removed_owned_links": len(stale), "release": str(release)}


def absolutize_links(package, installed):
    for path in package.rglob("*.md"):
        def absolute(match):
            try:
                destination = match.group(2).decode("utf-8")
            except UnicodeDecodeError:
                return match.group(0)
            if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", destination) or destination.startswith(("#", "/")):
                return match.group(0)
            relative, separator, anchor = destination.partition("#")
            source = (path.parent / relative).resolve()
            if not source.exists() or not source.is_relative_to(package):
                return match.group(0)
            target = installed / source.relative_to(package)
            return match.group(1) + os.fsencode(target) + (separator + anchor if separator else "").encode() + match.group(3)
        path.write_bytes(re.sub(rb"(\]\()([^\s)]+)(\))", absolute, path.read_bytes()))


@contextmanager
def sync_lock(root):
    cache = root / ".cache"
    cache.mkdir(exist_ok=True)
    with (cache / "sync.lock").open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise PortError("Another upstream check/preparation is already running") from error
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def fetch_upstream(root, source=None, ref=None):
    manifest = read_manifest(root)
    source, ref = source or manifest["repository"], ref or manifest["ref"]
    if ref.startswith("-") or ":" in ref:
        raise PortError("Expected one upstream ref, not a fetch refspec")
    cache = root / ".cache/upstream.git"
    if not cache.exists():
        cache.mkdir()
        git(cache, "init", "--bare", "--quiet")
    git(cache, "fetch", "--quiet", "--no-tags", "--depth=1", "--", source, ref)
    commit = git(cache, "rev-parse", "FETCH_HEAD")
    tree = git(cache, "rev-parse", "FETCH_HEAD:" + manifest["path"])
    if git(cache, "cat-file", "-t", tree) != "tree":
        raise PortError("The upstream package path is not a tree")
    return cache, {**manifest, "repository": source, "ref": ref, "commit": commit, "tree": tree}


def maintenance_root(root):
    first = git(root, "worktree", "list", "--porcelain").splitlines()[0]
    if not first.startswith("worktree "):
        raise PortError("Cannot locate the primary maintenance checkout")
    return Path(first.removeprefix("worktree ")).resolve()


def candidate_location(root, latest):
    suffix = latest["tree"][:12]
    return root / ".worktrees" / ("upstream-" + suffix), "feature/ai-upstream-" + suffix


def existing_candidate(root, latest):
    candidate, branch = candidate_location(root, latest)
    if not candidate.exists():
        return None
    if (git(candidate, "rev-parse", "--show-toplevel") != str(candidate)
            or git(candidate, "branch", "--show-current") != branch
            or read_manifest(candidate)["tree"] != latest["tree"]):
        raise PortError("An unknown or incomplete candidate occupies " + str(candidate))
    return {"status": "candidate", "wakeAgent": True, "reused": True,
            "worktree": str(candidate), "branch": branch, "upstream": latest}


def check(root, source=None, ref=None):
    root = maintenance_root(root)
    with sync_lock(root):
        _, latest = fetch_upstream(root, source, ref)
        current = read_manifest(root)
        changed = latest["tree"] != current["tree"]
        pending = existing_candidate(root, latest) if changed else None
        if pending:
            return {**pending, "status": "candidate_pending", "changed": True, "wakeAgent": False,
                    "current": current, "latest": latest}
        return {"status": "changed" if changed else "unchanged", "changed": changed,
                "wakeAgent": changed, "current": current, "latest": latest}


def prepare_sync(root, source=None, ref=None):
    root = maintenance_root(root)
    with sync_lock(root):
        if git(root, "status", "--porcelain"):
            raise PortError("Integrate or preserve the main checkout's changes before preparing a sync")
        cache, latest = fetch_upstream(root, source, ref)
        if latest["tree"] == read_manifest(root)["tree"]:
            return {"status": "unchanged", "wakeAgent": False}
        pending = existing_candidate(root, latest)
        if pending:
            return pending
        candidate, branch = candidate_location(root, latest)
        git(root, "worktree", "add", "-b", branch, str(candidate), "HEAD")
        git(candidate, "submodule", "update", "--init", "--depth", "1", "--", str(SUBMODULE))
        module = candidate / SUBMODULE
        git(module, "fetch", "--quiet", "--no-tags", "--depth=1", "--", str(cache), latest["commit"])
        git(module, "checkout", "--quiet", "--detach", latest["commit"])
        git(candidate, "config", "--file", ".gitmodules", "submodule.upstream.url", latest["repository"])
        (candidate / BAKING / "upstream.json").write_text(json.dumps(latest, indent=2) + "\n")
        git(candidate, "add", "--", ".gitmodules", str(SUBMODULE), str(BAKING / "upstream.json"))
        source_manifest(candidate)
        return {"status": "candidate", "wakeAgent": True, "reused": False,
                "worktree": str(candidate), "branch": branch, "upstream": latest}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("bake")
    commands.add_parser("build")
    validator = commands.add_parser("validate")
    validator.add_argument("--tracked", action="store_true", help="Require reviewed publication bytes and modes in the Git index")
    versioner = commands.add_parser("bump-version")
    versioner.add_argument("--version", help="A newer MAJOR.MINOR.PATCH version; defaults to the next patch")
    for name in ("install", "retire-links"):
        installer = commands.add_parser(name)
        installer.add_argument("--target", action="append", choices=HARNESSES, required=True)
        installer.add_argument("--home", type=Path, default=Path.home())
    for name in ("check", "prepare-sync"):
        command = commands.add_parser(name)
        command.add_argument("--source")
        command.add_argument("--ref")
        command.add_argument("--compact", action="store_true", help="Emit one JSON line for scheduler prechecks")
    args = parser.parse_args()
    try:
        if args.command == "bake":
            result = bake(ROOT)
        elif args.command == "build":
            result = build(ROOT)
        elif args.command == "validate":
            result = validate(ROOT, tracked=args.tracked)
        elif args.command == "bump-version":
            result = bump_version(ROOT, args.version)
        elif args.command == "install":
            result = install(ROOT, list(dict.fromkeys(args.target)), args.home.expanduser().resolve())
        elif args.command == "retire-links":
            result = retire_links(ROOT, list(dict.fromkeys(args.target)), args.home.expanduser().resolve())
        elif args.command == "check":
            result = check(ROOT, args.source, args.ref)
        else:
            result = prepare_sync(ROOT, args.source, args.ref)
        print(json.dumps(result, indent=None if getattr(args, "compact", False) else 2))
    except (PortError, OSError, ValueError, yaml.YAMLError) as error:
        print(json.dumps({"status": "error", "error": str(error)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
