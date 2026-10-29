# Examples — open-with

`/open-with [app]`

`[app]` is optional; omitting it opens VS Code.

| Invocation            | Opens the session's folders in           |
| --------------------- | ---------------------------------------- |
| `/open-with`          | VS Code, as one multi-root workspace     |
| `/open-with zed`      | Zed, as one workspace                    |
| `/open-with fresh`    | Fresh, one Windows Terminal tab per root |
| `/open-with explorer` | File Explorer, one window per root       |
| `/open-with vs`       | Visual Studio, one window per root       |

**Refuses:** an app with no file in `apps/`, and an app whose command cannot be found.
