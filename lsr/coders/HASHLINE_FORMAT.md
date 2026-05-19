# Hashline Edit Format

## Overview

Hashline is a token-efficient edit format that uses line references (line number + short hash) to reference code locations, instead of repeating the original code in SEARCH blocks.

## Format Specification

### REPLACE - Replace existing lines

```
path/to/file.py
<<<<<<< HASH start_ref..end_ref
new code line 1
new code line 2
>>>>>>> REPLACE
```

- `start_ref` and `end_ref` are hash references in format `NNN:HHH` (3-digit line number + 3-char hex hash)
- Range is inclusive - both start and end lines are replaced
- For single line: use same ref twice (`003:abc..003:abc`)

### INSERT - Insert after a line

```
path/to/file.py
<<<<<<< HASH target_ref
new code line 1
new code line 2
>>>>>>> INSERT
```

- New lines are inserted AFTER the line with `target_ref`

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
001:abc | def hello():
002:def |     print("world")
```

**LLM response:**

```
file.py
<<<<<<< HASH 002:def..002:def
    print("hello world")
>>>>>>> REPLACE
```

### Example 2: Multi-line replacement

**Original file:**

```
001:abc | def process(data):
002:def |     result = []
003:789 |     for item in data:
004:de0 |         result.append(item)
005:345 |     return result
```

**LLM response:**

```
file.py
<<<<<<< HASH 002:def..005:345
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
001:a1b | import os
002:d4e |
003:789 | def main():
```

**LLM response:**

```
file.py
<<<<<<< HASH 001:a1b
import sys
import logging
>>>>>>> INSERT
```

### Example 4: Delete lines

**Original file:**

```
001:a1b | def hello():
002:d4e |     # TODO: remove this
003:789 |     print("hello")
```

**LLM response:**

```
file.py
<<<<<<< HASH 002:d4e..002:d4e
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
5. **For single line**: use same ref twice (`003:abc..003:abc`)
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

- Hashes are computed from `SHA256(line_number:line_content)[:3]`, displayed as `NNN:HHH`
- Edits are applied from bottom to top to avoid line number shifts
- All edits use the original file's hash mapping (not sequential updates)
