# Global Claude Code Instructions

## Command Line

In Windows prefer using PowerShell. If a command cannot be executed fallback to the OS's configured shell, e.g. bash.

## JavaScript Package Manager

Always use `pnpm` instead of `npm`. This applies to all commands:

- Install dependencies: `pnpm install` (not `npm install`)
- Add packages: `pnpm add <pkg>` (not `npm install <pkg>`)
- Run scripts: `pnpm <script>` (not `npm run <script>`)
- Execute binaries: `pnpm dlx <pkg>` (not `npx <pkg>`)
