# Community: aider-cmd

- **Language:** python
- **Size:** 14
- **Cohesion:** 0.07
- **Description:** Directory-based community: crg_toolkit

## Members (14)

- `Function` fmt_qn((qn: str, max_len: int = 60)) — `aider/aider/crg_toolkit.py:49`
- `Function` fmt_node((n)) — `aider/aider/crg_toolkit.py:54`
- `Function` cmd_status((cm: CodeMap, args: argparse.Namespace)) — `aider/aider/crg_toolkit.py:64`
- `Function` cmd_query((cm: CodeMap, args: argparse.Namespace)) — `aider/aider/crg_toolkit.py:97`
- `Function` cmd_search((cm: CodeMap, args: argparse.Namespace)) — `aider/aider/crg_toolkit.py:155`
- `Function` cmd_flows((cm: CodeMap, args: argparse.Namespace)) — `aider/aider/crg_toolkit.py:184`
- `Function` cmd_communities((cm: CodeMap, args: argparse.Namespace)) — `aider/aider/crg_toolkit.py:208`
- `Function` cmd_risk((cm: CodeMap, args: argparse.Namespace)) — `aider/aider/crg_toolkit.py:249`
- `Function` _resolve_impact_files((cm: CodeMap, patterns: list[str])) — `aider/aider/crg_toolkit.py:269`
- `Function` cmd_impact((cm: CodeMap, args: argparse.Namespace)) — `aider/aider/crg_toolkit.py:281`
- `Function` cmd_export((cm: CodeMap, args: argparse.Namespace)) — `aider/aider/crg_toolkit.py:326`
- `Function` cmd_wiki((cm: CodeMap, args: argparse.Namespace)) — `aider/aider/crg_toolkit.py:345`
- `Function` _build_parser(()) — `aider/aider/crg_toolkit.py:407`
- `Function` main(()) — `aider/aider/crg_toolkit.py:468`

## Internal Call Graph

- `cmd_query` -> `fmt_qn`
- `cmd_flows` -> `fmt_qn`
- `cmd_communities` -> `fmt_node`
- `cmd_risk` -> `fmt_qn`
- `cmd_impact` -> `_resolve_impact_files`
- `cmd_impact` -> `fmt_node`
- `cmd_impact` -> `fmt_qn`
- `main` -> `_build_parser`
