# scrape-scrape

## Overview

Directory-based community: tests/scrape

- **Size**: 36 nodes
- **Cohesion**: 0.2448
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| DummyIO | Class | /home/smh/aider/tests/scrape/test_playwright_disable.py | 62-84 |
| __init__ | Function | /home/smh/aider/tests/scrape/test_playwright_disable.py | 63-66 |
| tool_output | Function | /home/smh/aider/tests/scrape/test_playwright_disable.py | 68-69 |
| confirm_ask | Function | /home/smh/aider/tests/scrape/test_playwright_disable.py | 80-81 |
| tool_error | Function | /home/smh/aider/tests/scrape/test_playwright_disable.py | 74-75 |
| test_scraper_disable_playwright_flag | Test | /home/smh/aider/tests/scrape/test_playwright_disable.py | 20-35 |
| fake_httpx | Function | /home/smh/aider/tests/scrape/test_playwright_disable.py | 28-30 |
| test_scraper_enable_playwright | Test | /home/smh/aider/tests/scrape/test_playwright_disable.py | 38-52 |
| fake_playwright | Function | /home/smh/aider/tests/scrape/test_playwright_disable.py | 45-47 |
| test_commands_web_disable_playwright | Test | /home/smh/aider/tests/scrape/test_playwright_disable.py | 55-139 |
| tool_warning | Function | /home/smh/aider/tests/scrape/test_playwright_disable.py | 71-72 |
| read_text | Function | /home/smh/aider/tests/scrape/test_playwright_disable.py | 77-78 |
| print | Function | /home/smh/aider/tests/scrape/test_playwright_disable.py | 83-84 |
| DummyCoder | Class | /home/smh/aider/tests/scrape/test_playwright_disable.py | 87-111 |
| __init__ | Function | /home/smh/aider/tests/scrape/test_playwright_disable.py | 88-90 |
| get_rel_fname | Function | /home/smh/aider/tests/scrape/test_playwright_disable.py | 92-93 |
| get_inchat_relative_files | Function | /home/smh/aider/tests/scrape/test_playwright_disable.py | 95-96 |
| abs_root_path | Function | /home/smh/aider/tests/scrape/test_playwright_disable.py | 98-99 |
| get_all_abs_files | Function | /home/smh/aider/tests/scrape/test_playwright_disable.py | 101-102 |
| get_announcements | Function | /home/smh/aider/tests/scrape/test_playwright_disable.py | 104-105 |
| format_chat_chunks | Function | /home/smh/aider/tests/scrape/test_playwright_disable.py | 107-108 |
| event | Function | /home/smh/aider/tests/scrape/test_playwright_disable.py | 110-111 |
| DummyScraper | Class | /home/smh/aider/tests/scrape/test_playwright_disable.py | 117-123 |
| __init__ | Function | /home/smh/aider/tests/scrape/test_playwright_disable.py | 118-119 |
| scrape | Function | /home/smh/aider/tests/scrape/test_playwright_disable.py | 121-123 |
| TestScrape | Class | /home/smh/aider/tests/scrape/test_scrape.py | 10-171 |
| test_scrape_self_signed_ssl | Test | /home/smh/aider/tests/scrape/test_scrape.py | 11-35 |
| scrape_with_retries | Function | /home/smh/aider/tests/scrape/test_scrape.py | 12-18 |
| setUp | Function | /home/smh/aider/tests/scrape/test_scrape.py | 37-39 |
| test_cmd_web_imports_playwright | Test | /home/smh/aider/tests/scrape/test_scrape.py | 41-67 |
| test_scrape_actual_url_with_playwright | Test | /home/smh/aider/tests/scrape/test_scrape.py | 69-82 |
| test_scraper_print_error_not_called | Test | /home/smh/aider/tests/scrape/test_scrape.py | 84-95 |
| test_scrape_with_playwright_error_handling | Test | /home/smh/aider/tests/scrape/test_scrape.py | 97-136 |
| mock_content | Function | /home/smh/aider/tests/scrape/test_scrape.py | 107-108 |
| test_scrape_text_plain | Test | /home/smh/aider/tests/scrape/test_scrape.py | 138-150 |
| test_scrape_text_html | Test | /home/smh/aider/tests/scrape/test_scrape.py | 152-171 |

## Execution Flows

No execution flows pass through this community.

## Dependencies

### Outgoing

- `MagicMock` (12 edge(s))
- `/home/smh/aider/aider/scrape.py::Scraper` (9 edge(s))
- `append` (6 edge(s))
- `scrape` (6 edge(s))
- `assert_not_called` (5 edge(s))
- `assertIsNotNone` (4 edge(s))
- `type` (3 edge(s))
- `setattr` (2 edge(s))
- `cmd_web` (2 edge(s))
- `any` (2 edge(s))
- `assertIn` (2 edge(s))
- `assertIsNone` (2 edge(s))
- `assertEqual` (2 edge(s))
- `assert_called_once_with` (2 edge(s))
- `Commands` (1 edge(s))

### Incoming

- `MagicMock` (12 edge(s))
- `/home/smh/aider/tests/scrape/test_playwright_disable.py` (9 edge(s))
- `/home/smh/aider/aider/scrape.py::Scraper` (9 edge(s))
- `assert_not_called` (5 edge(s))
- `scrape` (5 edge(s))
- `assertIsNotNone` (4 edge(s))
- `setattr` (2 edge(s))
- `cmd_web` (2 edge(s))
- `any` (2 edge(s))
- `assertIn` (2 edge(s))
- `assertIsNone` (2 edge(s))
- `assertEqual` (2 edge(s))
- `assert_called_once_with` (2 edge(s))
- `type` (1 edge(s))
- `Commands` (1 edge(s))
