# Hashline Edit Format

## Overview

Hashline is a token-efficient edit format that uses line hashes to reference code locations, instead of repeating the original code in SEARCH blocks.

## Format Specification

### REPLACE - Replace existing lines

```
path/to/file.py
<<<<<<< HASH start_hash..end_hash
new code line 1
new code line 2
>>>>>>> REPLACE
```

- `start_hash` and `end_hash` are 6-character hex hashes shown in the file content
- Range is inclusive - both start and end lines are replaced
- For single line: use same hash twice (`hash..hash`)

### INSERT - Insert after a line

```
path/to/file.py
<<<<<<< HASH target_hash
new code line 1
new code line 2
>>>>>>> INSERT
```

- New lines are inserted AFTER the line with `target_hash`

### CREATE - Create new file

```
new_file.py
<<<<<<< CREATE
new file content
>>>>>>> END
```

## Examples

### Example 1: Simple line replacement

**Original file (as shown to LLM):**

```
a1b2c3 | def hello():
d4e5f6 |     print("world")
```

**LLM response:**

```
file.py
<<<<<<< HASH d4e5f6..d4e5f6
    print("hello world")
>>>>>>> REPLACE
```

### Example 2: Multi-line replacement

**Original file:**

```
a1b2c3 | def process(data):
d4e5f6 |     result = []
789abc |     for item in data:
def012 |         result.append(item)
345678 |     return result
```

**LLM response:**

```
file.py
<<<<<<< HASH d4e5f6..345678
    result = []
    for item in data:
        if item.valid:
            result.append(transform(item))
    return sorted(result)
>>>>>>> REPLACE
```

### Example 3: Insert new code

**Original file:**

```
a1b2c3 | import os
d4e5f6 |
789abc | def main():
```

**LLM response:**

```
file.py
<<<<<<< HASH a1b2c3
import sys
import logging
>>>>>>> INSERT
```

### Example 4: Delete lines

**Original file:**

```
a1b2c3 | def hello():
d4e5f6 |     # TODO: remove this
789abc |     print("hello")
```

**LLM response:**

```
file.py
<<<<<<< HASH d4e5f6..d4e5f6
>>>>>>> REPLACE
```

### Example 5: Create new file

**LLM response:**

```
utils.py
<<<<<<< CREATE
def helper():
    return "help"

class Config:
    pass
>>>>>>> END
```

## Rules for LLM

1. **Copy hashes EXACTLY** - do not modify, recalculate, or fabricate hashes
2. **Do NOT include original code** - only output new code in the edit block
3. **Do NOT include hash prefixes** in the new code
4. **Use FULL file path** as shown by the user
5. **For single line**: use same hash twice (`hash..hash`)
6. **To delete**: use REPLACE with empty content
7. **To move code**: use REPLACE to delete + INSERT to insert

## Token Efficiency

Compared to SEARCH/REPLACE format:

| Edit Size | SEARCH/REPLACE | Hashline    | Savings |
| --------- | -------------- | ----------- | ------- |
| 1 line    | ~20 tokens     | ~15 tokens  | 25%     |
| 5 lines   | ~60 tokens     | ~30 tokens  | 50%     |
| 10 lines  | ~120 tokens    | ~55 tokens  | 54%     |
| 20 lines  | ~240 tokens    | ~105 tokens | 56%     |

## Error Handling

If a hash is not found in the file, the edit fails with a clear error message indicating which hash was not found. The system may suggest similar hashes to help correct the mistake.

## Implementation Notes

- Hashes are computed from `SHA256(line_number:line_content)[:6]`
- Edits are applied from bottom to top to avoid line number shifts
- All edits use the original file's hash mapping (not sequential updates)
