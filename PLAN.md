# Plan: Improve `/edit` Command — Naming, Counter, and `/mark` Command

## Context

The current `/edit` command in `lsr/commands.py` creates temporary files for selected LaTeX sections, but:

1. Temp files use random hash names (`lsr_edit_<random>.tex`) — impossible to tell which sections are inside
2. There's no visual counter showing how many temp files have been created in the session
3. There's no way to "mark" sections as completed to visually track editing progress

## Approach

### 1. Rename Temp Files: `section_name_abc12345.tex`

Change `cmd_edit` to name temp files using sanitized section/subsection titles + short hash for deduplication.

**Naming formula:** `lsr_edit_<sanitized_title>_<hash8>.tex`

Where `<sanitized_title>`:

- Lowercase
- Spaces → underscores
- Strip LaTeX commands (e.g. `\textbf{foo}` → `foo`)
- Strip non-alphanumeric/underscore chars
- Truncate to 40 chars max
- If multiple sections selected, join **first 2 titles** with `__`

**Example:** `/edit paper.tex` selecting "Introduction" and "Methodology"
→ `lsr_edit_introduction__methodology_a3f2b1c0.tex`

### 2. Edit Counter Display

Add a class-level counter `self.edit_session_count` on `Commands`. Each call to `cmd_edit` increments it and shows the count in the CLI output.

**Display:** In the section listing header and summary:

```
╭─ Structure of paper.tex — Edit #3 ─╮
```

```
✔ Ready to edit! (session #3)
```

**Reset behavior:** Counter resets on `/mark` and `/clear`.

### 3. New `/mark` Command — Persistent Section Completion Tracking

`/mark` requires user to specify which sections to mark. Marks are **persisted** to `~/.lsr/marks.json` so new sessions can reuse them.

**Usage:**

- `/mark <file.tex> 1,3` → marks sections 1 and 3 as done
- `/mark <file.tex> all` → marks all sections in the file
- `/mark --reset` → clears ALL marks across all files
- `/mark --reset <file.tex>` → clears marks for a specific file

**Display in section listing (marked = green ✓, still selectable):**

```
╭─ Structure of paper.tex ─╮
   1. ✓ § Introduction [1-45]          ← marked (green)
   2.   § Methodology [46-120]          ← unmarked
   3.   § Results [121-200]             ← unmarked
```

**Side effects:** `/mark` also resets `edit_session_count` to 0.

**Persistence format** (`~/.lsr/marks.json`):

```json
{
  "/path/to/paper.tex": ["Introduction", "Results"],
  "/path/to/chapter2.tex": ["Background"]
}
```

## Files to Modify

| File                | Change                                                                                                                                                                                                            |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `lsr/commands.py`   | `__init__` (counter + mark state), `cmd_edit` (naming + counter), `cmd_edit_done` (verify glob), `_parse_and_select_sections` (show ✓), new `cmd_mark`, `_load_marks`, `_save_marks`, `cmd_clear` (reset counter) |
| `~/.lsr/marks.json` | Auto-created persistence file for marked sections                                                                                                                                                                 |

## Reuse

- Existing `_parse_and_select_sections()` (line 2080) — extend with marked-status display
- Existing `cmd_edit()` hash computation (line 2218) — reuse for filename dedup
- Existing `cmd_edit_done()` glob `lsr_edit_*.tex.session` (line 2279) — already handles arbitrary filenames
- Existing `lsr_home = ~/.lsr/` directory pattern (line 2241) — store `marks.json` here alongside `tmp/`

## Steps

- [ ] Add `edit_session_count = 0` and `_last_edit_file = None` to `Commands.__init__()`
- [ ] Create `_sanitize_filename(title)` helper — lowercase, strip LaTeX, spaces→underscores, truncate
- [ ] Create `_load_marks()` / `_save_marks()` helpers using `~/.lsr/marks.json`
- [ ] Modify `cmd_edit()` to build filename from first 2 section titles + hash instead of `tempfile.mkstemp`
- [ ] Add edit counter increment and display in `cmd_edit()` output
- [ ] Modify `_parse_and_select_sections()` to accept `marked_titles` param, show `✓` in green for marked sections
- [ ] Implement `cmd_mark()` — parse `<file> <indices>`, persist marks, reset counter
- [ ] Implement `/mark --reset` and `/mark --reset <file>` to clear persisted marks
- [ ] Reset `edit_session_count` in `cmd_clear()`
- [ ] Verify `cmd_edit_done()` still finds sessions (glob `lsr_edit_*.tex.session` unchanged)
- [ ] Test persistence: marks survive across new lsr sessions

## Verification

1. `/edit paper.tex`, select sections → temp file named `lsr_edit_introduction__methodology_a3f2b1c0.tex`
2. `/edit` again → counter shows `Edit #2`
3. `/mark paper.tex 1,2` → sections 1,2 get `✓` in future listings, counter resets
4. Restart lsr → marks still visible (persisted in `~/.lsr/marks.json`)
5. `/mark --reset` → all marks cleared across all files
6. `/edit-done` → changes merge back correctly with new filename format
7. `/clear` → counter resets to 0
8. Sections with special chars, spaces, LaTeX commands in titles produce clean filenames
