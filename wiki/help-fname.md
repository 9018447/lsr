# help-fname

## Overview

Directory-based community: tests/help

- **Size**: 9 nodes
- **Cohesion**: 0.0738
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| TestHelp | Class | /home/smh/aider/tests/help/test_help.py | 15-143 |
| retry_with_backoff | Function | /home/smh/aider/tests/help/test_help.py | 17-48 |
| setUpClass | Function | /home/smh/aider/tests/help/test_help.py | 51-74 |
| run_help_command | Function | /home/smh/aider/tests/help/test_help.py | 62-69 |
| test_init | Test | /home/smh/aider/tests/help/test_help.py | 76-78 |
| test_ask_without_mock | Test | /home/smh/aider/tests/help/test_help.py | 80-96 |
| test_fname_to_url_unix | Test | /home/smh/aider/tests/help/test_help.py | 98-114 |
| test_fname_to_url_windows | Test | /home/smh/aider/tests/help/test_help.py | 116-132 |
| test_fname_to_url_edge_cases | Test | /home/smh/aider/tests/help/test_help.py | 134-143 |

## Execution Flows

No execution flows pass through this community.

## Dependencies

### Outgoing

- `assertEqual` (16 edge(s))
- `/home/smh/aider/aider/help.py::fname_to_url` (16 edge(s))
- `assertIn` (6 edge(s))
- `lower` (3 edge(s))
- `time` (2 edge(s))
- `/home/smh/aider/aider/help.py::Help` (2 edge(s))
- `assertGreater` (2 edge(s))
- `unittest.TestCase` (1 edge(s))
- `func` (1 edge(s))
- `sleep` (1 edge(s))
- `min` (1 edge(s))
- `Exception` (1 edge(s))
- `cmd_help` (1 edge(s))
- `/home/smh/aider/aider/io.py::InputOutput` (1 edge(s))
- `/home/smh/aider/aider/models.py::Model` (1 edge(s))

### Incoming

- `assertEqual` (16 edge(s))
- `/home/smh/aider/aider/help.py::fname_to_url` (16 edge(s))
- `assertIn` (6 edge(s))
- `lower` (3 edge(s))
- `/home/smh/aider/aider/help.py::Help` (2 edge(s))
- `assertGreater` (2 edge(s))
- `/home/smh/aider/tests/help/test_help.py` (1 edge(s))
- `ask` (1 edge(s))
- `len` (1 edge(s))
- `count` (1 edge(s))
- `assertIsNotNone` (1 edge(s))
