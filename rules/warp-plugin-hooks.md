# Warp plugin (`warp@claude-code-warp`) local patch

The plugin's hook commands must be quoted, or every hook fails on this machine. A plugin update replaces the patched file, so reapply the fix after each update.

## Why

The plugin root is `C:\Users\Pablo Castillo\.claude\plugins\cache\claude-code-warp\warp\<version>\`, and the space in `Pablo Castillo` breaks the unquoted `${CLAUDE_PLUGIN_ROOT}/scripts/<name>.sh` commands. Bash splits them at the space and runs `C:/Users/Pablo` as a script. That path is a stray VC++ installer log, so bash fails with `syntax error near unexpected token '('`. The exit code is 2, which Claude Code treats as a blocking hook failure: the `Stop` hook blocks every turn from finishing, and `PostToolUse` errors after every tool call.

## Reapply after every plugin update

1. Open `~/.claude/plugins/cache/claude-code-warp/warp/<version>/hooks/hooks.json` for the newest installed version.
2. Change every `"command": "${CLAUDE_PLUGIN_ROOT}/scripts/<name>.sh"` to `"command": "\"${CLAUDE_PLUGIN_ROOT}/scripts/<name>.sh\""`. As of 2.4.0 there is one per event: `SessionStart`, `Stop`, `Notification`, `PermissionRequest`, `UserPromptSubmit`, `PostToolUse`, `StopFailure`. Quote any new ones too.
3. Run `/reload-plugins`.

When hook errors mention `C:/Users/Pablo` after a plugin update, an update has probably dropped the quotes. Offer to reapply them.

## Related

- The hook scripts need `jq`. It is installed through winget (`jqlang.jq`) in `%LOCALAPPDATA%\Microsoft\WinGet\Links`. If `jq: command not found` appears, check that it is still on the PATH.
- The `/dev/tty: No such device or address` message is harmless. The scripts fall back to `jq` output when `/dev/tty` is unavailable.
- The patch becomes unnecessary if upstream quotes its commands, or if the user profile path no longer contains a space.
