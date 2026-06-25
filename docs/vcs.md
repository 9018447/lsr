# Version Control Support

`lsr` uses a pluggable VCS backend. It prefers **Jujutsu (jj)** when a colocated
jj repository is present and falls back to **Git** (via GitPython) otherwise.

## Detection order

When `lsr` starts, it searches for a repository root using this order:

1. `jj root` — if a `.jj` directory is found, `lsr` uses the **JjRepo** backend.
2. `git.Repo(..., search_parent_directories=True)` — if a `.git` directory is
   found, `lsr` uses the **GitRepo** backend.
3. If neither is found and `--vcs` is enabled, `lsr` offers to create a new
   colocated repository (`git init && jj git init --colocate`).

## CLI flags

- `--vcs` / `--no-vcs` — enable or disable VCS integration. `--git` and
  `--no-git` are accepted as aliases for backward compatibility.
- `--gitignore` / `--no-gitignore` — control whether `lsr` suggests adding
  `.lsr*` to `.gitignore`. The file is still named `.gitignore` because both
  Git and colocated jj use it.

## Slash commands

- `/vcs <args>` — run the active VCS command (`jj --no-pager <args>` in jj
  mode, `git <args>` in git mode).
- `/git <args>` and `/jj <args>` — aliases for `/vcs`.
- `/commit [message]` — commit changes in the active backend.
- `/undo` — undo the last `lsr` commit.
- `/diff` — show changes since the last message.

## Jujutsu specifics

`lsr` treats the working-copy parent (`@-`) as the equivalent of git `HEAD` and
the working copy (`@`) as the unstaged tree.

### Commit workflow

- Full working-copy commit: `jj describe -m "msg" && jj new`.
- File-specific commit: `jj describe -m "msg" && jj split -r @ -- <files>`.
  The selected files stay in `@-`; the remaining changes move to the new
  working copy `@`.

### Undo

`/undo` verifies that `@-` matches a commit made in the current `lsr` session,
then restores the changed files from `@--` and abandons `@-`.

## Git specifics

The Git backend preserves the original upstream behavior:

- Auto-commits use `git commit`.
- Author/committer attribution uses `GIT_AUTHOR_NAME` and `GIT_COMMITTER_NAME`.
- `/undo` uses `git checkout HEAD~1 -- <files>` followed by `git reset --soft
  HEAD~1`.
