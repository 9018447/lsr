# Community: aider-node

- **Language:** python
- **Size:** 16
- **Cohesion:** 0.09
- **Description:** Directory-based community: crg_common

## Members (16)

- `Class` Node() — `aider/aider/crg_common.py:21`
- `Function` display_name((self)) — `aider/aider/crg_common.py:40`
- `Function` short_path((self)) — `aider/aider/crg_common.py:44`
- `Class` Edge() — `aider/aider/crg_common.py:53`
- `Class` Community() — `aider/aider/crg_common.py:65`
- `Class` Flow() — `aider/aider/crg_common.py:80`
- `Class` RiskItem() — `aider/aider/crg_common.py:91`
- `Class` CodeMap() — `aider/aider/crg_common.py:101`
- `Function` resolve_db_path((db_path: str | None = None)) — `aider/aider/crg_common.py:116`
- `Function` load_code_map((db_path: str | None = None)) — `aider/aider/crg_common.py:125`
- `Function` fuzzy_find_node((cm: CodeMap, pattern: str)) — `aider/aider/crg_common.py:318`
- `Function` get_callers((cm: CodeMap, qn: str)) — `aider/aider/crg_common.py:339`
- `Function` get_callees((cm: CodeMap, qn: str)) — `aider/aider/crg_common.py:343`
- `Function` get_tests_for_node((cm: CodeMap, qn: str)) — `aider/aider/crg_common.py:347`
- `Function` get_imports((cm: CodeMap, qn: str)) — `aider/aider/crg_common.py:351`
- `Function` get_impacted_nodes((cm: CodeMap, file_paths: list[str])) — `aider/aider/crg_common.py:355`

## Internal Call Graph

- `load_code_map` -> `resolve_db_path`
- `load_code_map` -> `Node`
- `load_code_map` -> `Edge`
- `load_code_map` -> `Community`
- `load_code_map` -> `Flow`
- `load_code_map` -> `RiskItem`
- `load_code_map` -> `CodeMap`
