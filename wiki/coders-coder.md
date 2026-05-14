# coders-coder

## Overview

Directory-based community: aider/coders

- **Size**: 232 nodes
- **Cohesion**: 0.2257
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| ArchitectCoder | Class | /home/smh/aider/aider/coders/architect_coder.py | 6-48 |
| reply_completed | Function | /home/smh/aider/aider/coders/architect_coder.py | 11-48 |
| ArchitectPrompts | Class | /home/smh/aider/aider/coders/architect_prompts.py | 6-40 |
| AskCoder | Class | /home/smh/aider/aider/coders/ask_coder.py | 5-9 |
| AskPrompts | Class | /home/smh/aider/aider/coders/ask_prompts.py | 6-41 |
| compute_line_hash | Function | /home/smh/aider/aider/coders/base_coder.py | 56-59 |
| add_line_hashes | Function | /home/smh/aider/aider/coders/base_coder.py | 62-76 |
| strip_line_hashes | Function | /home/smh/aider/aider/coders/base_coder.py | 79-90 |
| UnknownEditFormat | Class | /home/smh/aider/aider/coders/base_coder.py | 93-99 |
| __init__ | Function | /home/smh/aider/aider/coders/base_coder.py | 94-99 |
| MissingAPIKeyError | Class | /home/smh/aider/aider/coders/base_coder.py | 102-103 |
| FinishReasonLength | Class | /home/smh/aider/aider/coders/base_coder.py | 106-107 |
| wrap_fence | Function | /home/smh/aider/aider/coders/base_coder.py | 110-111 |
| Coder | Class | /home/smh/aider/aider/coders/base_coder.py | 125-2518 |
| create | Function | /home/smh/aider/aider/coders/base_coder.py | 162-238 |
| clone | Function | /home/smh/aider/aider/coders/base_coder.py | 240-242 |
| get_announcements | Function | /home/smh/aider/aider/coders/base_coder.py | 244-332 |
| __init__ | Function | /home/smh/aider/aider/coders/base_coder.py | 336-579 |
| setup_lint_cmds | Function | /home/smh/aider/aider/coders/base_coder.py | 581-585 |
| show_announcements | Function | /home/smh/aider/aider/coders/base_coder.py | 587-591 |
| add_rel_fname | Function | /home/smh/aider/aider/coders/base_coder.py | 593-595 |
| drop_rel_fname | Function | /home/smh/aider/aider/coders/base_coder.py | 597-601 |
| abs_root_path | Function | /home/smh/aider/aider/coders/base_coder.py | 603-611 |
| show_pretty | Function | /home/smh/aider/aider/coders/base_coder.py | 616-624 |
| _stop_waiting_spinner | Function | /home/smh/aider/aider/coders/base_coder.py | 626-633 |
| get_abs_fnames_content | Function | /home/smh/aider/aider/coders/base_coder.py | 635-644 |
| choose_fence | Function | /home/smh/aider/aider/coders/base_coder.py | 646-672 |
| get_files_content | Function | /home/smh/aider/aider/coders/base_coder.py | 674-690 |
| get_read_only_files_content | Function | /home/smh/aider/aider/coders/base_coder.py | 692-703 |
| get_cur_message_text | Function | /home/smh/aider/aider/coders/base_coder.py | 705-709 |
| get_ident_mentions | Function | /home/smh/aider/aider/coders/base_coder.py | 711-715 |
| get_ident_filename_matches | Function | /home/smh/aider/aider/coders/base_coder.py | 717-740 |
| get_repo_map | Function | /home/smh/aider/aider/coders/base_coder.py | 742-781 |
| get_repo_messages | Function | /home/smh/aider/aider/coders/base_coder.py | 783-794 |
| get_readonly_files_messages | Function | /home/smh/aider/aider/coders/base_coder.py | 796-820 |
| get_chat_files_messages | Function | /home/smh/aider/aider/coders/base_coder.py | 822-848 |
| get_images_message | Function | /home/smh/aider/aider/coders/base_coder.py | 850-890 |
| run_stream | Function | /home/smh/aider/aider/coders/base_coder.py | 892-895 |
| init_before_message | Function | /home/smh/aider/aider/coders/base_coder.py | 897-907 |
| run | Function | /home/smh/aider/aider/coders/base_coder.py | 909-925 |
| copy_context | Function | /home/smh/aider/aider/coders/base_coder.py | 927-929 |
| get_input | Function | /home/smh/aider/aider/coders/base_coder.py | 931-943 |
| preproc_user_input | Function | /home/smh/aider/aider/coders/base_coder.py | 945-955 |
| run_one | Function | /home/smh/aider/aider/coders/base_coder.py | 957-977 |
| check_and_open_urls | Function | /home/smh/aider/aider/coders/base_coder.py | 979-995 |
| check_for_urls | Function | /home/smh/aider/aider/coders/base_coder.py | 997-1017 |
| keyboard_interrupt | Function | /home/smh/aider/aider/coders/base_coder.py | 1019-1033 |
| summarize_start | Function | /home/smh/aider/aider/coders/base_coder.py | 1035-1045 |
| summarize_worker | Function | /home/smh/aider/aider/coders/base_coder.py | 1047-1055 |
| summarize_end | Function | /home/smh/aider/aider/coders/base_coder.py | 1057-1067 |

*... and 182 more members.*

## Execution Flows

- **run_stream** (criticality: 0.73, depth: 6)
- **__init__** (criticality: 0.67, depth: 2)
- **warm_cache_worker** (criticality: 0.56, depth: 1)
- **format_messages** (criticality: 0.49, depth: 5)
- **handle_shell_commands** (criticality: 0.46, depth: 3)
- **dmp_apply** (criticality: 0.45, depth: 2)
- **dmp_lines_apply** (criticality: 0.45, depth: 2)
- **remove_reasoning_content** (criticality: 0.43, depth: 1)
- **git_cherry_pick_osr_onto_o** (criticality: 0.43, depth: 1)
- **git_cherry_pick_sr_onto_so** (criticality: 0.43, depth: 1)
- *... and 18 more flows.*

## Dependencies

### Outgoing

- `len` (116 edge(s))
- `append` (94 edge(s))
- `strip` (69 edge(s))
- `set` (46 edge(s))
- `dict` (45 edge(s))
- `join` (43 edge(s))
- `splitlines` (39 edge(s))
- `startswith` (35 edge(s))
- `get` (32 edge(s))
- `tool_output` (31 edge(s))
- `add` (27 edge(s))
- `Path` (26 edge(s))
- `tool_warning` (26 edge(s))
- `str` (25 edge(s))
- `ValueError` (25 edge(s))

### Incoming

- `/home/smh/aider/aider/coders/search_replace.py` (21 edge(s))
- `/home/smh/aider/aider/coders/editblock_coder.py` (16 edge(s))
- `/home/smh/aider/aider/coders/udiff_coder.py` (13 edge(s))
- `/home/smh/aider/aider/coders/patch_coder.py` (11 edge(s))
- `/home/smh/aider/aider/coders/base_coder.py` (8 edge(s))
- `/home/smh/aider/aider/coders/editblock_func_coder.py` (2 edge(s))
- `/home/smh/aider/aider/coders/architect_coder.py` (1 edge(s))
- `/home/smh/aider/aider/coders/architect_prompts.py` (1 edge(s))
- `/home/smh/aider/aider/coders/ask_coder.py` (1 edge(s))
- `/home/smh/aider/aider/coders/ask_prompts.py` (1 edge(s))
- `/home/smh/aider/tests/basic/test_coder.py::TestCoder.mock_send` (1 edge(s))
- `/home/smh/aider/tests/basic/test_coder.py::TestCoder.test_unknown_edit_format_exception` (1 edge(s))
- `/home/smh/aider/tests/basic/test_coder.py::TestCoder.test_unknown_edit_format_creation` (1 edge(s))
- `/home/smh/aider/aider/coders/base_prompts.py` (1 edge(s))
- `/home/smh/aider/aider/coders/chat_chunks.py` (1 edge(s))
