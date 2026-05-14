# basic-cmd

## Overview

Directory-based community: tests/basic

- **Size**: 562 nodes
- **Cohesion**: 0.0629
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| temp_analytics_file | Function | /home/smh/aider/tests/basic/test_analytics.py | 13-16 |
| temp_data_dir | Function | /home/smh/aider/tests/basic/test_analytics.py | 20-24 |
| test_analytics_initialization | Test | /home/smh/aider/tests/basic/test_analytics.py | 27-32 |
| test_analytics_enable_disable | Test | /home/smh/aider/tests/basic/test_analytics.py | 35-49 |
| test_analytics_data_persistence | Test | /home/smh/aider/tests/basic/test_analytics.py | 52-57 |
| test_analytics_event_logging | Test | /home/smh/aider/tests/basic/test_analytics.py | 60-79 |
| test_system_info | Test | /home/smh/aider/tests/basic/test_analytics.py | 82-89 |
| test_need_to_ask | Test | /home/smh/aider/tests/basic/test_analytics.py | 92-104 |
| test_is_uuid_in_percentage | Test | /home/smh/aider/tests/basic/test_analytics.py | 107-136 |
| TestAWSCredentials | Class | /home/smh/aider/tests/basic/test_aws_credentials.py | 7-169 |
| test_bedrock_model_with_aws_profile | Test | /home/smh/aider/tests/basic/test_aws_credentials.py | 10-40 |
| test_us_anthropic_model_with_aws_profile | Test | /home/smh/aider/tests/basic/test_aws_credentials.py | 42-72 |
| test_non_bedrock_model_with_aws_profile | Test | /home/smh/aider/tests/basic/test_aws_credentials.py | 74-104 |
| test_bedrock_model_without_aws_profile | Test | /home/smh/aider/tests/basic/test_aws_credentials.py | 106-135 |
| test_mixed_missing_keys_with_aws_profile | Test | /home/smh/aider/tests/basic/test_aws_credentials.py | 137-169 |
| TestCoder | Class | /home/smh/aider/tests/basic/test_coder.py | 19-1434 |
| setUp | Function | /home/smh/aider/tests/basic/test_coder.py | 20-23 |
| test_allowed_to_edit | Test | /home/smh/aider/tests/basic/test_coder.py | 25-52 |
| test_allowed_to_edit_no | Test | /home/smh/aider/tests/basic/test_coder.py | 54-80 |
| test_allowed_to_edit_dirty | Test | /home/smh/aider/tests/basic/test_coder.py | 82-102 |
| test_get_files_content | Test | /home/smh/aider/tests/basic/test_coder.py | 104-120 |
| test_check_for_filename_mentions | Test | /home/smh/aider/tests/basic/test_coder.py | 122-152 |
| test_check_for_ambiguous_filename_mentions_of_longer_paths | Test | /home/smh/aider/tests/basic/test_coder.py | 154-173 |
| test_skip_duplicate_basename_mentions | Test | /home/smh/aider/tests/basic/test_coder.py | 175-204 |
| test_check_for_file_mentions_read_only | Test | /home/smh/aider/tests/basic/test_coder.py | 206-231 |
| test_check_for_file_mentions_with_mocked_confirm | Test | /home/smh/aider/tests/basic/test_coder.py | 233-268 |
| test_check_for_subdir_mention | Test | /home/smh/aider/tests/basic/test_coder.py | 270-286 |
| test_get_file_mentions_various_formats | Test | /home/smh/aider/tests/basic/test_coder.py | 288-367 |
| test_get_file_mentions_multiline_backticks | Test | /home/smh/aider/tests/basic/test_coder.py | 369-406 |
| test_get_file_mentions_path_formats | Test | /home/smh/aider/tests/basic/test_coder.py | 408-444 |
| test_run_with_file_deletion | Test | /home/smh/aider/tests/basic/test_coder.py | 446-477 |
| mock_send | Function | /home/smh/aider/tests/basic/test_coder.py | 1201-1204 |
| test_run_with_file_unicode_error | Test | /home/smh/aider/tests/basic/test_coder.py | 479-506 |
| test_choose_fence | Test | /home/smh/aider/tests/basic/test_coder.py | 508-530 |
| test_run_with_file_utf_unicode_error | Test | /home/smh/aider/tests/basic/test_coder.py | 532-568 |
| test_new_file_edit_one_commit | Test | /home/smh/aider/tests/basic/test_coder.py | 570-610 |
| test_only_commit_gpt_edited_file | Test | /home/smh/aider/tests/basic/test_coder.py | 612-665 |
| mock_get_commit_message | Function | /home/smh/aider/tests/basic/test_coder.py | 785-787 |
| test_gpt_edit_to_dirty_file | Test | /home/smh/aider/tests/basic/test_coder.py | 667-750 |
| test_gpt_edit_to_existing_file_not_in_repo | Test | /home/smh/aider/tests/basic/test_coder.py | 752-798 |
| test_skip_aiderignored_files | Test | /home/smh/aider/tests/basic/test_coder.py | 800-835 |
| test_skip_gitignored_files_on_init | Test | /home/smh/aider/tests/basic/test_coder.py | 837-865 |
| test_check_for_urls | Test | /home/smh/aider/tests/basic/test_coder.py | 867-937 |
| test_coder_from_coder_with_subdir | Test | /home/smh/aider/tests/basic/test_coder.py | 939-973 |
| test_suggest_shell_commands | Test | /home/smh/aider/tests/basic/test_coder.py | 975-1004 |
| test_no_suggest_shell_commands | Test | /home/smh/aider/tests/basic/test_coder.py | 1006-1010 |
| test_detect_urls_enabled | Test | /home/smh/aider/tests/basic/test_coder.py | 1012-1022 |
| test_detect_urls_disabled | Test | /home/smh/aider/tests/basic/test_coder.py | 1024-1035 |
| test_unknown_edit_format_exception | Test | /home/smh/aider/tests/basic/test_coder.py | 1037-1045 |
| test_unknown_edit_format_creation | Test | /home/smh/aider/tests/basic/test_coder.py | 1047-1058 |

*... and 512 more members.*

## Execution Flows

No execution flows pass through this community.

## Dependencies

### Outgoing

- `assertEqual` (471 edge(s))
- `str` (284 edge(s))
- `Path` (239 edge(s))
- `assertIn` (190 edge(s))
- `/home/smh/aider/aider/io.py::InputOutput` (187 edge(s))
- `/home/smh/aider/aider/utils.py::GitTemporaryDirectory` (139 edge(s))
- `MagicMock` (135 edge(s))
- `write_text` (134 edge(s))
- `create` (124 edge(s))
- `assertTrue` (124 edge(s))
- `len` (124 edge(s))
- `patch` (105 edge(s))
- `/home/smh/aider/aider/main.py::main` (97 edge(s))
- `DummyInput` (85 edge(s))
- `/home/smh/aider/aider/models.py::Model` (84 edge(s))

### Incoming

- `assertEqual` (468 edge(s))
- `str` (277 edge(s))
- `Path` (230 edge(s))
- `assertIn` (188 edge(s))
- `/home/smh/aider/aider/io.py::InputOutput` (185 edge(s))
- `/home/smh/aider/aider/utils.py::GitTemporaryDirectory` (138 edge(s))
- `write_text` (132 edge(s))
- `create` (124 edge(s))
- `MagicMock` (123 edge(s))
- `assertTrue` (123 edge(s))
- `len` (122 edge(s))
- `patch` (101 edge(s))
- `/home/smh/aider/aider/main.py::main` (97 edge(s))
- `DummyInput` (85 edge(s))
- `DummyOutput` (80 edge(s))
