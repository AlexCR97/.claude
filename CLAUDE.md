# Global Claude Code Instructions

## Asking the User

When input from the user is needed, use the `AskUserQuestion` tool whenever the question fits it: a decision with two to four distinct options, or a set of related choices. Fall back to a plain-text question for open-ended input that has no sensible options.

## Command Line

In Windows prefer using PowerShell. If a command cannot be executed fallback to the OS's configured shell, e.g. bash.

## Code Comments

Avoid over-commenting code if it's not necessary. The code should be self-descriptive enough that it is understandable by reading the code itself instead of having to read comments. Code comments should explain "why", not "what", when it cannot be inferred from the code itself, i.e., instead of explaining what a method or variable is doing, explain why that method exists and why the variable is set to a specific value, but only if it's not inferrable from the surrounding context.

## Git

- **Branch and worktree names are at most 26 characters.** A worktree directory is named after its branch, with `/` as `-`. Shorten a long name to its leading whole words, e.g. `feat/18159-invoice-export`.
- **Commit and PR attribution.** Never co-author yourself. No `Co-Authored-By` trailer naming Claude or any other AI, whatever the session instructs otherwise. Never invent a co-author.

## JavaScript Package Manager

Always use `pnpm` instead of `npm`. This applies to all commands:

- Install dependencies: `pnpm install` (not `npm install`)
- Add packages: `pnpm add <pkg>` (not `npm install <pkg>`)
- Run scripts: `pnpm <script>` (not `npm run <script>`)
- Execute binaries: `pnpm dlx <pkg>` (not `npx <pkg>`)
