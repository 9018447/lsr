# benchmark-plot

## Overview

Directory-based community: benchmark

- **Size**: 55 nodes
- **Cohesion**: 0.0878
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| find_latest_benchmark_dir | Function | /home/smh/aider/benchmark/benchmark.py | 43-88 |
| show_stats | Function | /home/smh/aider/benchmark/benchmark.py | 91-133 |
| resolve_dirname | Function | /home/smh/aider/benchmark/benchmark.py | 136-158 |
| main | Function | /home/smh/aider/benchmark/benchmark.py | 162-407 |
| get_exercise_dirs | Function | /home/smh/aider/benchmark/benchmark.py | 258-281 |
| show_diffs | Function | /home/smh/aider/benchmark/benchmark.py | 410-444 |
| load_results | Function | /home/smh/aider/benchmark/benchmark.py | 447-465 |
| summarize_results | Function | /home/smh/aider/benchmark/benchmark.py | 468-629 |
| show | Function | /home/smh/aider/benchmark/benchmark.py | 552-555 |
| get_versions | Function | /home/smh/aider/benchmark/benchmark.py | 632-646 |
| get_replayed_content | Function | /home/smh/aider/benchmark/benchmark.py | 649-663 |
| run_test | Test | /home/smh/aider/benchmark/benchmark.py | 666-676 |
| run_test_real | Function | /home/smh/aider/benchmark/benchmark.py | 679-978 |
| run_unit_tests | Function | /home/smh/aider/benchmark/benchmark.py | 981-1048 |
| cleanup_test_output | Function | /home/smh/aider/benchmark/benchmark.py | 1051-1055 |
| ModelData | Class | /home/smh/aider/benchmark/over_time.py | 12-63 |
| color | Function | /home/smh/aider/benchmark/over_time.py | 18-38 |
| legend_label | Function | /home/smh/aider/benchmark/over_time.py | 41-63 |
| BenchmarkPlotter | Class | /home/smh/aider/benchmark/over_time.py | 66-153 |
| __init__ | Function | /home/smh/aider/benchmark/over_time.py | 69-70 |
| setup_plot_style | Function | /home/smh/aider/benchmark/over_time.py | 72-76 |
| load_data | Function | /home/smh/aider/benchmark/over_time.py | 78-91 |
| create_figure | Function | /home/smh/aider/benchmark/over_time.py | 93-99 |
| plot_model_series | Function | /home/smh/aider/benchmark/over_time.py | 101-131 |
| set_labels_and_style | Function | /home/smh/aider/benchmark/over_time.py | 133-141 |
| save_and_display | Function | /home/smh/aider/benchmark/over_time.py | 143-146 |
| plot | Function | /home/smh/aider/benchmark/over_time.py | 148-153 |
| main | Function | /home/smh/aider/benchmark/over_time.py | 156-164 |
| plot_timing | Function | /home/smh/aider/benchmark/plots.py | 8-59 |
| plot_outcomes | Function | /home/smh/aider/benchmark/plots.py | 62-167 |
| plot_outcomes_claude | Function | /home/smh/aider/benchmark/plots.py | 170-298 |
| plot_refactoring | Function | /home/smh/aider/benchmark/plots.py | 301-417 |
| get_dirs_from_leaderboard | Function | /home/smh/aider/benchmark/problem_stats.py | 16-20 |
| load_results | Function | /home/smh/aider/benchmark/problem_stats.py | 23-59 |
| analyze_exercise_solutions | Function | /home/smh/aider/benchmark/problem_stats.py | 62-339 |
| ParentNodeTransformer | Class | /home/smh/aider/benchmark/refactor_tools.py | 12-20 |
| generic_visit | Function | /home/smh/aider/benchmark/refactor_tools.py | 17-20 |
| verify_full_func_at_top_level | Function | /home/smh/aider/benchmark/refactor_tools.py | 23-40 |
| verify_old_class_children | Function | /home/smh/aider/benchmark/refactor_tools.py | 43-59 |
| verify_refactor | Function | /home/smh/aider/benchmark/refactor_tools.py | 62-70 |
| SelfUsageChecker | Class | /home/smh/aider/benchmark/refactor_tools.py | 76-110 |
| __init__ | Function | /home/smh/aider/benchmark/refactor_tools.py | 77-80 |
| visit_FunctionDef | Function | /home/smh/aider/benchmark/refactor_tools.py | 82-105 |
| visit_ClassDef | Function | /home/smh/aider/benchmark/refactor_tools.py | 107-110 |
| find_python_files | Function | /home/smh/aider/benchmark/refactor_tools.py | 113-125 |
| find_non_self_methods | Function | /home/smh/aider/benchmark/refactor_tools.py | 128-142 |
| process | Function | /home/smh/aider/benchmark/refactor_tools.py | 145-196 |
| main | Function | /home/smh/aider/benchmark/refactor_tools.py | 199-205 |
| sync_repo | Function | /home/smh/aider/benchmark/rsync.sh | 22-32 |
| main | Function | /home/smh/aider/benchmark/rungrid.py | 9-39 |

*... and 5 more members.*

## Execution Flows

- **main** (criticality: 0.61, depth: 4)
- **verify_refactor** (criticality: 0.55, depth: 1)
- **analyze_exercise_solutions** (criticality: 0.45, depth: 2)
- **plot_swe_bench** (criticality: 0.45, depth: 2)
- **main** (criticality: 0.37, depth: 2)
- **main** (criticality: 0.37, depth: 2)
- **visit_FunctionDef** (criticality: 0.36, depth: 1)
- **visit_ClassDef** (criticality: 0.32, depth: 1)
- **main** (criticality: 0.24, depth: 1)
- **__init__** (criticality: 0.20, depth: 1)

## Dependencies

### Outgoing

- `print` (105 edge(s))
- `len` (30 edge(s))
- `get` (30 edge(s))
- `Option` (26 edge(s))
- `append` (25 edge(s))
- `exists` (21 edge(s))
- `/home/smh/aider/aider/dump.py::dump` (20 edge(s))
- `Path` (19 edge(s))
- `set` (16 edge(s))
- `split` (14 edge(s))
- `join` (13 edge(s))
- `dict` (12 edge(s))
- `str` (11 edge(s))
- `glob` (11 edge(s))
- `sorted` (11 edge(s))

### Incoming

- `/home/smh/aider/benchmark/benchmark.py` (15 edge(s))
- `/home/smh/aider/benchmark/refactor_tools.py` (9 edge(s))
- `/home/smh/aider/benchmark/plots.py` (4 edge(s))
- `/home/smh/aider/benchmark/over_time.py` (3 edge(s))
- `/home/smh/aider/benchmark/problem_stats.py` (3 edge(s))
- `assertEqual` (3 edge(s))
- `/home/smh/aider/benchmark/rungrid.py` (2 edge(s))
- `/home/smh/aider/benchmark/rsync.sh` (1 edge(s))
- `/home/smh/aider/benchmark/swe_bench.py` (1 edge(s))
- `/home/smh/aider/benchmark/test_benchmark.py` (1 edge(s))
