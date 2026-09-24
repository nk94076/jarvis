# JARVIS: notes for developers / AI coding assistants

## Before pushing any new code: check JARVIS's own self-upgrades
JARVIS can change its own code on the user's PC (safe self-code-upgrade, `jarvis/selfcode.py`).
Each applied change is stored as a patch and, when `GITHUB_TOKEN` is set, shared to the branch
`jarvis-self-upgrades` in `self_patches/patches.json`. The user may also send
`Documents/JARVIS Reports/jarvis_self_changes.md` (exported with "apne badlav export karo").

Every time, before pushing:
1. `git fetch origin jarvis-self-upgrades` and read `self_patches/patches.json` (skip if the branch does not exist).
2. For each patch (`summary`, `edits[{file, find, replace}]`):
   - Good and safe -> merge it into the code (so it becomes permanent), mention it in the commit message.
   - Conflicts with your change -> re-implement the intent on top of the new code.
   - Wrong / risky -> leave it out and tell the user why.
3. Merged patches no longer apply separately: `update.bat` runs `python -m jarvis.selfcode --reapply`,
   which skips patches whose `replace` text is already present.
4. Run `python -m jarvis.selftest` before pushing.

## Conventions
- Code comments are Hinglish; spoken replies are Indian English ("Sir").
- User data lives in `~/JARVIS Data` (never in the repo); user settings in `~/JARVIS Data/my_settings.py`.
- Protected files JARVIS may never self-edit: `jarvis/security.py`, `jarvis/selftest.py`, `jarvis/sandbox.py`, `jarvis/selfcode.py`.
- Bump `VERSION` in `jarvis/config.py` on every release; `update.bat` shows it.
