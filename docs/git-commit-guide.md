# Committing to GitHub from the Terminal

A practical guide to committing and pushing code to GitHub using the command line.

## Prerequisites

- **Git installed** — check with `git --version`. If missing, install from [git-scm.com](https://git-scm.com/downloads) or via `brew install git` (macOS).
- **A GitHub account** and a repository (either created on GitHub or locally).
- **Authentication set up** — see [Authentication](#authentication) below.

## One-time setup

Set your identity so commits are attributed to you (use the email tied to your GitHub account):

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

Check your settings any time with:

```bash
git config --list
```

## The core commit workflow

### 1. Check what changed

```bash
git status              # see staged, unstaged, and untracked files
git diff                # see the actual line-by-line changes (unstaged)
git diff --staged       # see changes already staged
```

### 2. Stage your changes

Staging selects which changes go into the next commit.

```bash
git add path/to/file.py     # stage a specific file
git add .                   # stage everything in the current directory
git add -A                  # stage all changes in the repo (incl. deletions)
```

Unstage something if you added it by mistake:

```bash
git restore --staged path/to/file.py
```

### 3. Commit

```bash
git commit -m "Short summary of what changed"
```

For a longer message with a body, omit `-m` to open your editor, or use multiple `-m` flags:

```bash
git commit -m "Add login validation" -m "Rejects empty passwords and trims whitespace."
```

Stage tracked files and commit in one step (skips `git add` for already-tracked files):

```bash
git commit -am "Fix typo in header"
```

### 4. Push to GitHub

```bash
git push                          # push to the configured upstream branch
git push -u origin main           # first push of a new branch (sets upstream)
```

After `-u` is set once, plain `git push` works for that branch.

## Starting from scratch

### Clone an existing GitHub repo

```bash
git clone https://github.com/username/repo.git
cd repo
```

### Turn a local folder into a repo and connect it to GitHub

```bash
git init
git add -A
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/username/repo.git
git push -u origin main
```

## Authentication

GitHub no longer accepts account passwords over HTTPS. Use one of:

- **Personal Access Token (PAT)** — create at GitHub → Settings → Developer settings → Personal access tokens. Use it as the password when prompted. A credential helper can cache it:
  ```bash
  git config --global credential.helper store    # or 'osxkeychain' on macOS
  ```
- **SSH keys** — generate and add a key, then use the SSH remote URL:
  ```bash
  ssh-keygen -t ed25519 -C "you@example.com"
  cat ~/.ssh/id_ed25519.pub        # add this to GitHub → Settings → SSH keys
  git remote set-url origin git@github.com:username/repo.git
  ```
- **GitHub CLI** — `gh auth login` handles auth interactively (install via `brew install gh`).

## Working with branches

```bash
git switch -c feature/my-change    # create and switch to a new branch
git switch main                    # switch back to main
git push -u origin feature/my-change
```

Open a Pull Request afterward on GitHub, or with the CLI:

```bash
gh pr create
```

## Useful follow-ups

```bash
git log --oneline -10              # recent commit history, compact
git commit --amend                 # edit the most recent commit (before pushing)
git pull                           # fetch and merge remote changes
```

> **Tip:** Pull before you start working and before you push to avoid conflicts:
> `git pull --rebase` keeps history linear.

## Quick reference

| Action            | Command                          |
|-------------------|----------------------------------|
| See status        | `git status`                     |
| Stage all         | `git add -A`                     |
| Commit            | `git commit -m "message"`        |
| Stage + commit    | `git commit -am "message"`       |
| Push              | `git push`                       |
| Pull              | `git pull`                       |
| New branch        | `git switch -c name`             |
| View history      | `git log --oneline`              |
