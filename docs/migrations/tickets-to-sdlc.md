# One-off migration: `~/.tickets` to `~/.sdlc`

A prompt for an AI agent. It is a one-off: it ships in no plugin, leaves no code, flag or marker behind, and is deleted from the repository once the real run is done. Give the whole file to an agent that can run Python and shell commands and has read and write access to the directories below, and append the parameters you want to change.

You are migrating a ticket store written by the old `ticket-*` skills (`~/.tickets`) to the store the `sdlc` plugin reads (`~/.sdlc`). You READ the old store and WRITE the new one. The old store is never modified and stays in place as the backup.

## Parameters

| Name | Default | Meaning |
| --- | --- | --- |
| `OLD_HOME` | `~/.tickets` | The old store. Read only. |
| `NEW_HOME` | `~/.sdlc` | The new store. Written only by this run. |
| `PLUGIN_DIR` | none | The `sdlc` plugin directory, the one holding `shared/sdlc.py`. Without it, look for `shared/sdlc.py` in the installed plugin cache under `~/.claude/plugins`; if that does not give exactly one directory, stop and ask. |
| `WORK_DIR` | `<system temp>/sdlc-migration` | Where your throwaway script, manifests and log go. It is neither `OLD_HOME`, `NEW_HOME` nor inside either. |
| `EXPECTED_TICKETS`, `EXPECTED_JOURNAL_ENTRIES` | none | When given, step 6 also checks the counts against them. The real store is expected to hold 97 tickets and 137 journal entries. |

Expand `~` yourself and use absolute paths everywhere.

## Rules

1. **Never write under `OLD_HOME`**: no file, no directory, no timestamp touched, no repair, no cleanup, not even a log. Open its files for reading only. If a step seems to need a write there, stop and report.
2. **Write `NEW_HOME` only in step 4**, and only the files this prompt names. Every other file you create (scripts, manifests, log, scratch checks) goes in `WORK_DIR`, never beside it and never in a home: any directory in `NEW_HOME` is read as a namespace.
3. **Never delete anything**, in either home or in `WORK_DIR`. A run is repeated by the user emptying `NEW_HOME`, never by you.
4. **No network, no credentials.** Do not run `gh`, `az` or anything that reaches a remote, and do not read a token. You do not refresh a mirror.
5. **Keep the report free of ticket content.** What you print and say reports counts, the kind of thing found, and config key names. Never a ticket id, title, namespace or product name, repository, organization, project, path inside a ticket, or a value from a file. Your log in `WORK_DIR` follows the same rule; the manifests there hold paths, so do not print them.
6. **When something is not covered here, do not guess.** Leave it out of `NEW_HOME`, count it in the report and stop at the end of the step rather than inventing a rule.
7. **Long paths.** A store may hold paths over 260 characters. On Windows address every path as `\\?\` plus the absolute path, in Python and in anything you shell out to, and expect `robocopy` to be the tool of last resort, not the first.
8. **Scripts are files.** Write each script into `WORK_DIR` and run it with `python -I script.py <arguments>`. Inline `python -c` with `\\?\` paths and backslashes breaks on quoting, and a shell may refuse compound commands (`cd`, `$()`, `tee`) when it runs unattended.

## What the two stores are

Old and new share the same shape: `{namespace}/{product}/{source}/{id}/` under the home, with the same names. A migrated ticket therefore keeps its namespace, product, source and id; only the files change as below.

| Old | New | Rule |
| --- | --- | --- |
| `config.json` at the root | `sdlc.json` | Step 3 |
| `{namespace}/config.json` | `{namespace}/namespace.json` | Step 3 |
| `{namespace}/{product}/config.json` | `{namespace}/{product}/product.json` | Step 3 |
| `{ticket}/ticket.json` | `ticket.json` | Copied byte for byte |
| `{ticket}/raw/` | `raw/` | Copied byte for byte, see Mirrors |
| `{ticket}/journal/*.md` | `journal/*.md` | Copied byte for byte, file names kept |
| `{ticket}/plan.md` | `plan.md` | Copied, then link lines rewritten, see Plans |
| `{ticket}/digest.md` | none | **Not migrated**, see Digests |
| `{ticket}/pulls.md` | `pulls.md` | Copied byte for byte |
| `{ticket}/artifacts/` | `artifacts/` | Copied byte for byte |
| anything else | see Strays | |

### Config keys

The only source of truth for what the new config accepts is `PLUGIN_DIR/shared/sdlclib/config.py`: read `ALLOWED_KEYS` and `SHARED_KEYS` there, and `check_value`/`check_sources` for what values are valid. Do not work from a remembered list.

Carry each key over **unchanged** (same name, same value) when the new level file allows it. The old suite used the same key names, so for a store written by it this is the common case: `default_source`, `default_namespace`, `default_product`, `scan_roots`, `protected_branches`, `sensitive`, `worktree_root` and `sources.{source}.{coordinate}`. The levels differ only in which file holds a key, so a key never moves between levels. **Drop** (leave out of the new file, name in the report, copy no value) when:

- the key is not allowed at that level, or is not a key at all;
- a `sources` entry names a source the plugin does not provide (`PLUGIN_DIR/shared/providers/*.json`), or a coordinate that source does not declare, or one declared for another level (an organization belongs in a namespace file, a project in a product file);
- the value is not valid for the key, or names a namespace or product that is not in the store;
- the level is the fallback `default` namespace or product and the key is `sources` (those are never bound);
- the key's name is `token`, `secret`, `password`, `pat`, `apikey`, `api_key` or `credentials`, or ends in `_token`, `_secret` or `_password`. Never copy one; give `credential` as the reason. Any other unknown key is dropped as `not allowed`, never as `credential`.

A dropped key stays in the old file, which is the backup. List the dropped keys in the report as `{level}: {key}` with the reason, never the value. Do not translate a dropped key into another one.

### Tickets

Copy the **whole ticket directory** (every entry in it) except `digest.md`, and rewrite only `plan.md` (Plans).

- `ticket.json` is carried over as is, every field. The new design still reads `source`, `id`, `title`, `state`, `type`, `url`, `fingerprint`, `last_fetched_at`, `coordinates`, `origin` and ignores any other field, so no field has to be renamed or dropped. A `native_type` or `parent` stays: `parent` is the only record of a local ticket's parent.
- **`fingerprint` is carried as is.** An Azure DevOps ticket keeps `{"rev": N}`, the same marker the new fetcher writes. A GitHub ticket's old fingerprint (`updated_at` and `comment_count`) is a different marker from the new one (`sha256` of the content), so the first refresh or revision check of such a ticket reports it changed. That is expected and harmless: say so in the report. A local ticket keeps its content hash.
- A **local** ticket's own file `raw/ticket.md` is copied identical; the check in step 6 proves it.

### Mirrors

The old `raw/` of a remote ticket has the old layout (`raw.json` holding `meta` and a `tree`, attachments named `{guid}{extension}`, extracted zips as `raw/{guid}/`). The new mirror is a different `raw/raw.json` (`meta`, the issue or work item, `comments`, relations, `attachments`). **Carry the old `raw/` over untouched as a cache** and do not convert it: a mirror is replaceable by definition and the old attachments are kept on a refresh. The new fetcher rebuilds it in the new shape the next time `/sdlc:intake <ref>` runs for that ticket. Report how many remote tickets hold a mirror in the old shape (a `raw/raw.json` that has a `tree` key and no `work_item` or `issue` key).

### Digests

`digest.md` is **not migrated.** It is a derived copy of the ticket (the new design keeps no derived copy: the mirror is read directly), and nothing in the new plugin reads it. It stays in `OLD_HOME`, the backup. Report how many were left behind.

### Plans

`plan.md` is copied as is: its structure and the step status vocabulary (`Pending`, `In Progress`, `Blocked`, `Done`) are unchanged. Only a link to a digest is rewritten, so no link dangles.

In `plan.md` (the file at the top of the ticket directory), replace every markdown link whose target, ignoring a `#fragment`, is `digest.md` or ends in `/digest.md`, as in `[digest.md](digest.md)`, `[digest](digest.md#discussion)` or a link into a sibling ticket's `../{other}/digest.md`:

- the new target is the same directory part followed by the ticket's own source file: `raw/raw.json` when that ticket has a `raw/raw.json` in `OLD_HOME`, else `raw/ticket.md`; the fragment is dropped; a target whose ticket directory or source file you cannot find is left as it is and counted as `unresolved digest links`;
- when the link text is exactly `digest.md` or `digest` (any case), the new text is the new target; any other link text is kept;
- touch nothing else: not another line, not the line endings, not the encoding, not the words "digest" in prose. Read and write the file as bytes decoded as UTF-8, keeping `\r\n` and `\n` as found, and write it back without a byte-order mark unless it had one.

Report how many plans were rewritten, how many links, and how many `**Status:**` lines in the copied plans do not start with one of the four status words (copied untouched).

### Journals, pulls, artifacts

- `journal/*.md` entries are copied **byte for byte, with their file names and modification times.** An entry is the one thing that cannot be regenerated: never edit, reformat, re-encode or rename one, even to repair a link to a digest inside it.
- `pulls.md` and `artifacts/` are copied byte for byte. `artifacts/` can hold very large trees; check the free space in step 1 and copy it like any other directory.

### Strays

Anything the new design has no place for is reported by kind and count, never deleted.

- **Inside a ticket directory**, an entry that is not `ticket.json`, `raw`, `journal`, `plan.md`, `digest.md`, `pulls.md` or `artifacts` (for example a legacy `plan/` directory holding a plan split across files) is **copied verbatim**, since it belongs to that ticket and harms nothing. Report its entry name (a generic name, not a path) and how many tickets hold it. Say that the new plugin does not read it.
- **Above a ticket directory**, an entry that is not a namespace, a product or a source directory (a stray file or directory at the root, in a namespace, in a product, or a source directory the plugin has no provider for) is **not copied**: a directory in the new home is read as a namespace, a product or a ticket, so a stray would be misread. It stays in the backup. Report the level and count.
- A ticket whose `ticket.json` is unreadable, is not a JSON object, or whose `source` and `id` do not match its directory, is not migrated at all: this makes step 2 fail.

## Procedure

Do the steps in order. Run steps 1 and 2 completely before any write to `NEW_HOME`.

### Step 1: Refuse unsafe runs

Resolve every path to its real absolute form first (follow links, normalise case on Windows). **Stop with a one-line reason and write nothing** when any of these holds:

- `OLD_HOME` does not exist or is not a directory;
- `NEW_HOME` and `OLD_HOME` are the same directory, or either is inside the other;
- `NEW_HOME` exists and is not an **empty directory** (a file, a link, or a directory holding anything at all, hidden entries included). `NEW_HOME` that does not exist is fine; create it in step 4;
- `WORK_DIR` is, or is inside, `OLD_HOME` or `NEW_HOME`;
- `PLUGIN_DIR` does not hold `shared/sdlc.py` and `shared/sdlclib/config.py`;
- the free space on the volume of `NEW_HOME` is less than 1.1 times the size of `OLD_HOME`.

Then create `WORK_DIR` if it is missing, and save the helper below as `WORK_DIR/treehash.py`.

````python
"""Hash a directory tree without touching it: treehash.py DIR [--glob PATTERN] [--manifest FILE]."""

import fnmatch
import hashlib
import json
import os
import sys


def long_path(path):
    path = os.path.abspath(path)
    if os.name == "nt" and not path.startswith("\\\\?\\"):
        return "\\\\?\\" + path
    return path


def file_hash(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main(argv):
    root = long_path(argv[1])
    pattern = argv[argv.index("--glob") + 1] if "--glob" in argv else None
    manifest_path = argv[argv.index("--manifest") + 1] if "--manifest" in argv else None

    manifest = {}
    directories = 0
    for current, names, files in os.walk(root):
        names.sort()
        directories += len(names)
        for name in files:
            full = os.path.join(current, name)
            relative = os.path.relpath(full, root).replace(os.sep, "/")
            if pattern is None or fnmatch.fnmatchcase(relative, pattern):
                manifest[relative] = file_hash(full)

    tree = hashlib.sha256()
    for relative in sorted(manifest):
        tree.update(f"{relative}\0{manifest[relative]}\n".encode("utf-8"))

    if manifest_path:
        with open(manifest_path, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, ensure_ascii=False)
    print(json.dumps({"files": len(manifest), "directories": directories, "tree_sha256": tree.hexdigest()}))


main(sys.argv)
````

`fnmatch`'s `*` crosses `/`, so `*/journal/*.md` matches a journal entry at any depth; use `*/*/*/*/journal/*.md` for the entries of tickets exactly.

### Step 2: Inventory and validate the old store (read only)

1. Run `treehash.py OLD_HOME --manifest WORK_DIR/old.manifest.json`. Keep its summary as **hash-before**.
2. Walk `OLD_HOME` and classify every entry as above. Check, and collect every failure before reporting any:
   - every namespace and product directory name is a lowercase slug (`[a-z0-9][a-z0-9-]*`, the same rule `layout.py` applies); an entry whose name starts with `.` or fails the rule is a stray, not a failure;
   - every ticket directory under a source the plugin provides (`PLUGIN_DIR/shared/providers/*.json`; the file name is the source, not a prefix) has a name that fits that provider's `id.pattern`. A source directory the plugin does not provide is a stray, not a failure;
   - every ticket directory holds a `ticket.json` that parses to an object whose `source` and `id` equal its directory's source and name, and whose `type` is one of `user-story`, `task`, `bug`, `spike`, `tech-debt`;
   - no old config file is unreadable JSON or not an object.
3. If anything failed, print the failures as counts by kind and **stop**: nothing has been written anywhere but `WORK_DIR`.
4. Otherwise record the inventory: namespaces, products, tickets per source, journal entries (files directly in a `journal/` directory of a ticket), tickets holding each entry kind, `digest.md` files, `plan.md` files, `pulls.md` files, files under `artifacts/`.

### Step 3: Plan the config files

For each old `config.json` read it, apply the key rules above, and hold the result in memory. Each old config file gets exactly one counterpart at its level, written even when every key was dropped (then `{}`). A level with no old config file gets none.

### Step 4: Write `NEW_HOME`

1. Create `NEW_HOME` (and parents) if missing.
2. Write `sdlc.json`, each `namespace.json` and each `product.json` from step 3: UTF-8 without a byte-order mark, 2-space indentation, `ensure_ascii=False`, keys in their original order, a trailing newline.
3. For every ticket, create its directory at the same relative path and copy every entry of the old ticket directory into it except `digest.md`, preserving file contents and modification times, then rewrite `plan.md` as in Plans. Do it as one script in `WORK_DIR`, ticket by ticket, never writing outside `NEW_HOME`, with `shutil.copy2` (or `copytree`) on long-path-prefixed paths, and opening every old file for reading only. Write the plan from the old bytes in memory, not by editing the copy. A failure on one file is an error: stop, say how many tickets were done, and leave `NEW_HOME` as it is.
4. Copy nothing else: strays above a ticket directory stay in the backup.

### Step 5: Rebuild nothing, regenerate nothing

Do not run `fetch`, do not create `digest.md`, do not write a journal entry about the migration, do not touch `.gitignore` or any marker file. `NEW_HOME` holds exactly the old content, reshaped as above.

### Step 6: Verify

Run every check and report all of them, passing or failing. Do not stop at the first failure.

1. **Old store untouched.** Run `treehash.py OLD_HOME` again: `tree_sha256`, `files` and `directories` must equal **hash-before**. This is a failure with the highest priority: if it fails, say so first and change nothing further.
2. **Resolve every ticket.** With the environment variable `SDLC_HOME` set to `NEW_HOME` (for these calls only), run
   `python PLUGIN_DIR/shared/sdlc.py resolve {namespace}/{product}/{source}:{id}`
   once per migrated ticket, from a script that reads only the exit code and the JSON field `exists` and `paths.ticket_dir`. It passes when the exit code is 0, `exists` is true and `paths.ticket_dir` is that ticket's directory under `NEW_HOME`. A source prefix in the reference is the provider's file name (`ado`, `github`, `local`). Do not print the JSON: it carries ticket paths. If a call fails with a config message, read which key the message names and apply the "Config keys" rules (drop that key from the new config file and report it: a repair in `NEW_HOME` only) and rerun the whole check once; if it still fails, report the failure count and stop there.
3. **Counts.** Tickets in `NEW_HOME` (directories with a `ticket.json` at ticket depth) equal tickets in `OLD_HOME`, and equal `EXPECTED_TICKETS` when given. Journal entries (`*/*/*/*/journal/*.md`) equal those in `OLD_HOME`, and equal `EXPECTED_JOURNAL_ENTRIES` when given. Report the real numbers either way.
4. **Journal content.** Run `treehash.py` over both homes with `--glob "*/*/*/*/journal/*.md"`: the `files` and `tree_sha256` values must be equal (the hash covers each relative path, so file names are checked too).
5. **Everything copied verbatim is identical.** Run `treehash.py NEW_HOME --manifest WORK_DIR/new.manifest.json`. Compare it with `old.manifest.json` and require exactly this: every old file except a `digest.md` at ticket depth, a `config.json` at the root, namespace or product depth, a stray above ticket depth, and a top-level `plan.md` is in the new manifest with the same hash; every top-level `plan.md` is present; the new manifest holds nothing else except `sdlc.json`, `namespace.json` and `product.json` files. Report the counts of each group, and the file count of any difference (never a path).
6. **Plans.** For each rewritten `plan.md`, the old and new texts have the same number of lines and differ only on lines that held a digest link; no link in any top-level `plan.md` still targets `digest.md`, except the counted `unresolved digest links`.
7. **Local ticket files.** Every `raw/ticket.md` in `OLD_HOME` is byte-identical in `NEW_HOME` (covered by check 5; report its count).
8. **Parents (informational).** For every ticket whose `ticket.json` has a `parent`, run `resolve` on it with `--context {namespace}/{product}` of its own ticket and `SDLC_HOME` as above; report how many resolved and how many did not. A reference that did not resolve was already dangling in the old store when its target was never filed; this check never fails the migration.

### Step 7: Report

Print only this, with real values, and nothing from inside a ticket:

```
Migration {PASSED | FAILED}   OLD_HOME and NEW_HOME as given
Old store untouched:          yes | NO
Namespaces / products:        N / N
Tickets:                      N (ado N, github N, local N)   expected N | not given
Journal entries:              N copied, hashes equal yes | NO   expected N | not given
resolve succeeded:            N of N
Config files written:         sdlc.json N, namespace.json N, product.json N
Config keys dropped:          none | {level}: {key} - {reason}, one per line
Plans copied / rewritten:     N / N     digest links rewritten N, unresolved N
Status lines off-vocabulary:  N
Digests left in the backup:   N (not migrated, by design)
pulls.md copied:              N        artifacts files copied: N
Remote mirrors in old shape:  N (rebuilt by /sdlc:intake <ref> when next used)
GitHub tickets whose first refresh will report "changed": N
Entries kept verbatim that the plugin does not read:  {entry name}: N tickets, one per line, or none
Entries left in the backup (not copied):              {level}: N, one per line, or none
Parents resolved / not:       N / N
```

`PASSED` needs: the old store untouched, every check in step 6 passing, and no stop in an earlier step. End with the one remaining manual step: the old directory is the backup; it is kept until the user has used the new store and decides to remove it, and this prompt file is deleted from the repository after the real run.
