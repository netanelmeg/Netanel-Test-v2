#!/usr/bin/env python3
"""Validate the frontmatter of every agent and skill definition in this repo.

A definition with malformed frontmatter silently fails to load, so this script
is the only guard against a broken agent or skill. The frontmatter block is
parsed with pyyaml, a strict YAML 1.1 parser. It is not the loader Claude Code
uses, and every divergence found so far runs in the strict direction -- this
script rejects input the real loader may well accept. Duplicate keys are an
error here; YAML 1.1 scalar typing reads `yes` as a bool and `12:30:00` as an
int where a YAML 1.2 core-schema loader keeps both as strings, and both of
those land on a key this script checks. So a FAIL is a reason to look, not
proof the file is broken -- and the converse, that nothing broken for the real
loader can pass here, is the useful guarantee and is not one this script can
make. pyyaml is a hard dependency with no fallback: two parsers would mean a
file could pass on one machine and fail on another.

What is checked: the file opens with a `---` line and has a closing `---`; the
block between them is valid YAML; it parses to a mapping; no key is repeated
(pyyaml allows duplicates with last-wins, this script does not -- though a key
a `<<` merge supplies and the mapping also states literally is an override, as
it is for pyyaml, not a repeat); the top-level keys `name`, `description`,
`tools` (agents) and `name`, `description` (skills) are present and non-empty;
and `name` matches the filename stem or directory name. Nested and structured
values (`metadata:` blocks, `tools: [a, b]` lists) are fully parsed, but only
the top-level keys listed above are inspected -- their contents, and any other
key, are not validated. A leading UTF-8 BOM is reported as a failure: whether
the real loader tolerates one cannot be checked from this repo, so it is
treated as broken rather than assumed fine.

One further limitation, also fail-closed: an alias referring to a node that
encloses it (a mapping anchored `&x` with `*x` nested inside it) is rejected
here though pyyaml itself resolves it, because the duplicate-key check replaces
pyyaml's two-phase mapping constructor with a plain one.

Exit codes: 0 all definitions valid, 1 at least one failure, 2 cannot run.
"""

import codecs
import sys
from pathlib import Path

try:
    import yaml
except ImportError as exc:
    print("validate-squad: pyyaml is required but not importable (%s).\n"
          "Install it with: python3 -m pip install pyyaml" % exc, file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT / ".claude" / "agents"
SKILLS = ROOT / ".claude" / "skills"


class StrictLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate mapping keys instead of last-wins."""


def _construct_mapping(loader, node, deep=False):
    if not isinstance(node, yaml.MappingNode):
        raise yaml.constructor.ConstructorError(
            None, None, "expected a mapping node, but found %s" % node.id,
            node.start_mark)
    # Merge keys must be flattened before SafeLoader.construct_mapping below,
    # or the `<<` node reaches construct_object with a tag SafeLoader has no
    # constructor for. The flatten inside that call then becomes a no-op.
    # flatten_mapping prepends the merge source's entries onto node.value, so
    # the scan below runs over the mapping's own entries, snapshotted first: a
    # key that a merge supplies and the mapping also states literally is an
    # override, which is the point of merge keys, not a duplicate.
    own = []
    for key_node, value_node in node.value:
        if key_node.tag == "tag:yaml.org,2002:merge":
            # Construct the merge source here so its own duplicates are caught.
            # flatten_mapping only splices its entries into the parent, so
            # otherwise a source reachable solely through `<<` never reaches any
            # constructor and its duplicate keys go unseen.
            loader.construct_object(value_node, deep=True)
        else:
            own.append((key_node, value_node))
    loader.flatten_mapping(node)
    seen = set()
    for key_node, _ in own:
        # deep=True: a shallow collection key is an empty placeholder, so two
        # distinct complex keys would compare equal.
        key = loader.construct_object(key_node, deep=True)
        try:
            if key in seen:
                raise yaml.constructor.ConstructorError(
                    None, None, "duplicate key: %s" % (key,), key_node.start_mark)
            seen.add(key)
        except TypeError:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping", node.start_mark,
                "found unhashable key", key_node.start_mark)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def parse_frontmatter(text):
    """Return (mapping, None) or (None, error)."""
    lines = text.splitlines()
    if not lines or lines[0].rstrip() != "---":
        return None, "no frontmatter: line 1 is not '---'"

    end = None
    for index in range(1, len(lines)):
        if lines[index].rstrip() == "---":
            end = index
            break
    if end is None:
        return None, "unterminated frontmatter"

    # Leading newline so pyyaml's line numbers match the file's, not the block's.
    block = "\n" + "\n".join(lines[1:end])
    # The catch below is deliberately broad and must stay that way. This is the
    # parser boundary and the input is arbitrary file content: pyyaml's
    # constructors raise plain ValueError and TypeError as well as YAMLError --
    # `when: 2024-13-45` reaches datetime.date and comes out as ValueError.
    # Anything escaping here aborts the run and discards the failures already
    # reported, so naming the types seen so far is the bug, not the fix.
    # Exception and not BaseException: KeyboardInterrupt and SystemExit still
    # propagate.
    try:
        data = yaml.load(block, Loader=StrictLoader)
    except Exception as exc:
        return None, "invalid YAML: %s" % " ".join(str(exc).split())

    if data is None:
        return None, "empty frontmatter"
    if not isinstance(data, dict):
        return None, "frontmatter is not a mapping of keys to values (got %s)" % type(data).__name__
    return data, None


def read_frontmatter(path):
    try:
        raw = path.read_bytes()
        # utf-8-sig strips a BOM if present and is plain utf-8 otherwise, so the
        # rest of the file still parses; the BOM itself is reported below.
        text = raw.decode("utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        return None, "unreadable: %s" % exc
    if raw.startswith(codecs.BOM_UTF8):
        return None, "file starts with a UTF-8 BOM; remove it"
    return parse_frontmatter(text)


def is_filled(value):
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value)
    return False


def check_required(data, keys):
    errors = []
    for key in keys:
        if key not in data:
            errors.append("missing required key: %s" % key)
        elif is_filled(data[key]):
            continue
        elif isinstance(data[key], (str, list)):
            errors.append("empty value for key: %s" % key)
        else:
            errors.append("value for key '%s' must be text or a list, got %s"
                          % (key, type(data[key]).__name__))
    return errors


def check_name(data, expected, label):
    name = data.get("name")
    if not is_filled(name):
        return []
    if not isinstance(name, str):
        return ["name must be a string, got %s" % type(name).__name__]
    if name.strip() != expected:
        return ["name '%s' does not match %s '%s'" % (name.strip(), label, expected)]
    return []


def check_agent(path):
    if not path.is_file():
        return ["not a regular file"]
    data, error = read_frontmatter(path)
    if error:
        return [error]
    return check_required(data, ("name", "description", "tools")) \
        + check_name(data, path.stem, "filename stem")


def check_skill(directory):
    skill_file = directory / "SKILL.md"
    if not skill_file.is_file():
        return ["missing SKILL.md"]
    data, error = read_frontmatter(skill_file)
    if error:
        return [error]
    return check_required(data, ("name", "description")) \
        + check_name(data, directory.name, "directory name")


def list_entries(directory, lister, empty_error):
    """Return (entries, errors). Never raises: a directory that cannot be
    listed is a reported failure, not an aborted run."""
    if not directory.is_dir():
        return [], ["not a directory" if directory.exists() else "directory not found"]
    try:
        entries = sorted(lister(directory))
    except OSError as exc:
        return [], ["unlistable: %s" % exc]
    if not entries:
        return [], [empty_error]
    return entries, []


def main():
    failures = []

    agent_files, agent_errors = list_entries(
        AGENTS, lambda d: (c for c in d.iterdir() if c.suffix == ".md"),
        "no agent definitions found (*.md)")
    skill_dirs, skill_errors = list_entries(
        SKILLS, lambda d: (c for c in d.iterdir() if c.is_dir()),
        "no skill directories found")

    if agent_errors:
        failures.append((AGENTS, agent_errors))
    if skill_errors:
        failures.append((SKILLS, skill_errors))

    for path in agent_files:
        errors = check_agent(path)
        if errors:
            failures.append((path, errors))

    for directory in skill_dirs:
        errors = check_skill(directory)
        if errors:
            failures.append((directory, errors))

    checked = len(agent_files) + len(skill_dirs)

    if failures:
        for path, errors in failures:
            print("FAIL %s" % path.relative_to(ROOT))
            for error in errors:
                print("    %s" % error)
        print("%d files checked, %d failed" % (checked, len(failures)))
        return 1

    print("%d files checked (%d agents, %d skills), 0 failed"
          % (checked, len(agent_files), len(skill_dirs)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
