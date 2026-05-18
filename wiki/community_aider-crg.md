# Community: aider-crg

- **Language:** python
- **Size:** 5
- **Cohesion:** 0.07
- **Description:** Directory-based community: crg_tool_adapter

## Members (5)

- `Function` get_crg_prompt_for_mode((mode: str)) — `aider/aider/crg_tool_adapter.py:77`
- `Function` ensure_graph_db((root: str | Path)) — `aider/aider/crg_tool_adapter.py:114`
- `Function` parse_crg_tags((content: str)) — `aider/aider/crg_tool_adapter.py:140`
- `Function` run_crg_tool((subcommand: str, args_str: str, root: str | Path)) — `aider/aider/crg_tool_adapter.py:158`
- `Function` execute_crg_tools((content: str, root: str | Path)) — `aider/aider/crg_tool_adapter.py:221`

## Internal Call Graph

- `execute_crg_tools` -> `parse_crg_tags`
- `execute_crg_tools` -> `ensure_graph_db`
- `execute_crg_tools` -> `run_crg_tool`
