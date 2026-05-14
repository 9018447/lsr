# aider-cmd

## Overview

Directory-based community: aider

- **Size**: 521 nodes
- **Cohesion**: 0.1623
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| compute_hex_threshold | Function | /home/smh/aider/aider/analytics.py | 18-27 |
| is_uuid_in_percentage | Function | /home/smh/aider/aider/analytics.py | 30-52 |
| Analytics | Class | /home/smh/aider/aider/analytics.py | 60-254 |
| __init__ | Function | /home/smh/aider/aider/analytics.py | 73-86 |
| enable | Function | /home/smh/aider/aider/analytics.py | 88-108 |
| disable | Function | /home/smh/aider/aider/analytics.py | 110-117 |
| need_to_ask | Function | /home/smh/aider/aider/analytics.py | 119-135 |
| get_data_file_path | Function | /home/smh/aider/aider/analytics.py | 137-145 |
| get_or_create_uuid | Function | /home/smh/aider/aider/analytics.py | 147-153 |
| load_data | Function | /home/smh/aider/aider/analytics.py | 155-167 |
| save_data | Function | /home/smh/aider/aider/analytics.py | 169-184 |
| get_system_info | Function | /home/smh/aider/aider/analytics.py | 186-193 |
| _redact_model_name | Function | /home/smh/aider/aider/analytics.py | 195-204 |
| posthog_error | Function | /home/smh/aider/aider/analytics.py | 206-211 |
| event | Function | /home/smh/aider/aider/analytics.py | 213-254 |
| resolve_aiderignore_path | Function | /home/smh/aider/aider/args.py | 22-28 |
| default_env_file | Function | /home/smh/aider/aider/args.py | 31-32 |
| get_parser | Function | /home/smh/aider/aider/args.py | 35-869 |
| get_md_help | Function | /home/smh/aider/aider/args.py | 872-882 |
| get_sample_yaml | Function | /home/smh/aider/aider/args.py | 885-895 |
| get_sample_dotenv | Function | /home/smh/aider/aider/args.py | 898-908 |
| main | Function | /home/smh/aider/aider/args.py | 911-940 |
| DotEnvFormatter | Class | /home/smh/aider/aider/args_formatter.py | 8-78 |
| start_section | Function | /home/smh/aider/aider/args_formatter.py | 9-13 |
| _format_usage | Function | /home/smh/aider/aider/args_formatter.py | 15-16 |
| _format_text | Function | /home/smh/aider/aider/args_formatter.py | 18-39 |
| _format_action | Function | /home/smh/aider/aider/args_formatter.py | 41-72 |
| _format_action_invocation | Function | /home/smh/aider/aider/args_formatter.py | 74-75 |
| _format_args | Function | /home/smh/aider/aider/args_formatter.py | 77-78 |
| YamlHelpFormatter | Class | /home/smh/aider/aider/args_formatter.py | 81-172 |
| start_section | Function | /home/smh/aider/aider/args_formatter.py | 82-86 |
| _format_usage | Function | /home/smh/aider/aider/args_formatter.py | 88-89 |
| _format_text | Function | /home/smh/aider/aider/args_formatter.py | 91-103 |
| _format_action | Function | /home/smh/aider/aider/args_formatter.py | 105-166 |
| _format_action_invocation | Function | /home/smh/aider/aider/args_formatter.py | 168-169 |
| _format_args | Function | /home/smh/aider/aider/args_formatter.py | 171-172 |
| MarkdownHelpFormatter | Class | /home/smh/aider/aider/args_formatter.py | 175-228 |
| start_section | Function | /home/smh/aider/aider/args_formatter.py | 176-177 |
| _format_usage | Function | /home/smh/aider/aider/args_formatter.py | 179-182 |
| _format_text | Function | /home/smh/aider/aider/args_formatter.py | 184-185 |
| _format_action | Function | /home/smh/aider/aider/args_formatter.py | 187-222 |
| _format_action_invocation | Function | /home/smh/aider/aider/args_formatter.py | 224-225 |
| _format_args | Function | /home/smh/aider/aider/args_formatter.py | 227-228 |
| SwitchCoder | Class | /home/smh/aider/aider/commands.py | 30-33 |
| __init__ | Function | /home/smh/aider/aider/commands.py | 31-33 |
| Commands | Class | /home/smh/aider/aider/commands.py | 36-1680 |
| clone | Function | /home/smh/aider/aider/commands.py | 40-51 |
| __init__ | Function | /home/smh/aider/aider/commands.py | 53-85 |
| cmd_model | Function | /home/smh/aider/aider/commands.py | 87-112 |
| cmd_editor_model | Function | /home/smh/aider/aider/commands.py | 114-124 |

*... and 471 more members.*

## Execution Flows

- **run_stream** (criticality: 0.73, depth: 6)
- **main** (criticality: 0.70, depth: 3)
- **simple_send_with_retries** (criticality: 0.69, depth: 4)
- **__init__** (criticality: 0.67, depth: 2)
- **main** (criticality: 0.61, depth: 4)
- **set_thinking_tokens** (criticality: 0.61, depth: 1)
- **get_thinking_tokens** (criticality: 0.61, depth: 1)
- **get_repo_map** (criticality: 0.57, depth: 6)
- **warm_cache_worker** (criticality: 0.56, depth: 1)
- **cmd_tokens** (criticality: 0.52, depth: 1)
- *... and 112 more flows.*

## Dependencies

### Outgoing

- `tool_output` (170 edge(s))
- `add_argument` (134 edge(s))
- `print` (122 edge(s))
- `append` (122 edge(s))
- `tool_error` (107 edge(s))
- `len` (84 edge(s))
- `str` (79 edge(s))
- `get` (75 edge(s))
- `strip` (75 edge(s))
- `join` (70 edge(s))
- `Path` (61 edge(s))
- `set` (56 edge(s))
- `dict` (52 edge(s))
- `event` (45 edge(s))
- `startswith` (43 edge(s))

### Incoming

- `/home/smh/aider/aider/main.py` (20 edge(s))
- `/home/smh/aider/aider/utils.py` (20 edge(s))
- `/home/smh/aider/aider/models.py` (15 edge(s))
- `/home/smh/aider/tests/basic/test_models.py::TestModels.test_configure_model_settings` (14 edge(s))
- `/home/smh/aider/aider/onboarding.py` (12 edge(s))
- `/home/smh/aider/aider/report.py` (10 edge(s))
- `/home/smh/aider/tests/basic/test_models.py::TestModels.test_model_aliases` (9 edge(s))
- `/home/smh/aider/tests/basic/test_special.py::test_is_important` (9 edge(s))
- `/home/smh/aider/benchmark/benchmark.py::run_test_real` (8 edge(s))
- `/home/smh/aider/aider/gui.py` (8 edge(s))
- `/home/smh/aider/aider/io.py` (8 edge(s))
- `/home/smh/aider/aider/linter.py` (8 edge(s))
- `/home/smh/aider/aider/coders/base_coder.py::Coder.__init__` (7 edge(s))
- `/home/smh/aider/aider/args.py` (7 edge(s))
- `/home/smh/aider/tests/basic/test_main.py::TestMain.test_default_model_selection` (7 edge(s))
