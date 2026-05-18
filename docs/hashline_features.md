# Hashline Features Documentation

This document describes the new hashline features added to aider, which help you visualize and use line hashes when working with the hashline edit format.

## Overview

The hashline edit format uses 6-character hashes to reference specific lines in your code. This makes edits more precise and less error-prone than line numbers, which can shift as code changes.

## New Commands

### `/edit-file`

Open a file in your editor with hashline annotations, then automatically add it to the chat.

**Usage:**
```
/edit-file <filename>
```

**Example:**
```
/edit-file src/main.py
```

**What it does:**
1. Computes hash values for every line in the file
2. Opens your editor with the annotated version showing:
   - 6-character hash for each line
   - Line number
   - Original code content
3. When you close the editor, the original file is automatically added to the chat
4. Displays a summary of the hashline information

**Editor display format:**
```
# Hashline annotations for: main.py
# Format: HASH | LINE_NUMBER | CONTENT
# Use these hashes when requesting edits with aider
#======================================================================

a1b2c3 |    1 | def hello():
d4e5f6 |    2 |     print("Hello, World!")
789abc |    3 | 
def012 |    4 | def add(a, b):
345678 |    5 |     return a + b
```

### `/hashline`

Show hashline annotations for files in the chat.

**Usage:**
```
/hashline              # Show summary for all files in chat
/hashline <filename>   # Show full hashline annotations for a specific file
```

**Examples:**
```
/hashline
/hashline src/main.py
```

**What it shows:**
- For specific files: Full hashline annotations with all line hashes
- For all files: Summary including line count and first/last hash values

## How to Use Hashes

When asking aider to make edits, you can reference lines by their hash values:

### Replace a single line
```
Replace line a1b2c3 with:
def hello(name):
    print(f"Hello, {name}!")
```

### Replace a range of lines
```
Replace lines a1b2c3..d4e5f6 with:
def calculate(x, y):
    result = x + y
    return result
```

### Insert after a line
```
After line a1b2c3, insert:
import logging
logger = logging.getLogger(__name__)
```

### Delete lines
```
Delete lines a1b2c3..d4e5f6
```

## Persistent Storage

Hash values are cached in the `.aider/hashline_cache/` directory within your project root. This means:

### Cache Invalidation

The cache automatically invalidates when:
1. **File is modified**: Cache stores file modification time (mtime). If file mtime is newer than cached mtime, cache is considered stale and recomputed.
2. **Manual invalidation**: Use `hashline_mgr.invalidate_cache(file_path)` to force recomputation.
3. **Clear all cache**: Use `hashline_mgr.clear_all_cache()` to wipe the entire cache directory.

**Automatic behavior:**
- When you call `get_hashes(file_path)`, it first tries to load from cache
- If cache is stale (file modified), it automatically recomputes and saves new cache
- No manual intervention needed for normal usage

**Example:**
```python
from aider.hashline_manager import HashlineManager

mgr = HashlineManager(root_dir='/path/to/project')

# This will use cache if valid, or recompute if stale
hashes = mgr.get_hashes('/path/to/file.py')

# Force recomputation
mgr.invalidate_cache('/path/to/file.py')
hashes = mgr.get_hashes('/path/to/file.py')  # Will recompute
```

1. Hashes are computed once and reused
2. Cache is automatically invalidated when files change
3. No manual cache management needed

## Benefits

1. **Precise references**: Hashes uniquely identify lines regardless of position changes
2. **Visual feedback**: See exactly which lines you're referencing
3. **Reduced errors**: No more counting line numbers manually
4. **Better LLM context**: The hashline format helps the LLM understand exactly which lines to modify

## Tips

1. Use `/edit-file` when you want to review a file and plan edits
2. Use `/hashline` to quickly check hash values without opening an editor
3. Copy hash values directly from the editor display when asking for edits
4. The hash format is `abcdef` (6 hex characters) - always copy exactly

## Troubleshooting

**Q: The hashes don't match what I see in the editor**
A: Make sure you're looking at the same version of the file. Hashes are computed from the current file content.

**Q: Can I edit the annotated file directly?**
A: No, the annotated display is read-only. Edit the original file in your regular editor, then use `/hashline` to see updated hashes.

**Q: Where are the cached hashes stored?**
A: In `.aider/hashline_cache/` within your project root. Each file gets a JSON cache file.

## Technical Details

- Hashes are computed using SHA-256, truncated to 6 hex characters
- The hash includes both the line content and its 1-based position
- This ensures identical lines at different positions get distinct hashes
- Cache files are in JSON format for easy inspection/debugging
