# Community: aider-plan

- **Language:** python
- **Size:** 14
- **Cohesion:** 0.23
- **Description:** Directory-based community: plan_manager

## Members (14)

- `Class` Plan() — `aider/aider/plan_manager.py:22`
- `Function` short_id((self)) — `aider/aider/plan_manager.py:31`
- `Function` filename((self)) — `aider/aider/plan_manager.py:36`
- `Function` _plans_dir((root: str | Path)) — `aider/aider/plan_manager.py:41`
- `Function` _now_id(()) — `aider/aider/plan_manager.py:47`
- `Function` _now_iso(()) — `aider/aider/plan_manager.py:51`
- `Function` save_plan((content: str, title: str, root: str | Path, status: str = "draft")) — `aider/aider/plan_manager.py:55`
- `Function` update_plan((plan: Plan, root: str | Path)) — `aider/aider/plan_manager.py:92`
- `Function` load_plan((plan_id: str, root: str | Path)) — `aider/aider/plan_manager.py:108`
- `Function` _parse_plan_file((filepath: Path)) — `aider/aider/plan_manager.py:129`
- `Function` list_plans((root: str | Path)) — `aider/aider/plan_manager.py:157`
- `Function` delete_plan((plan_id: str, root: str | Path)) — `aider/aider/plan_manager.py:164`
- `Function` get_latest_plan((root: str | Path)) — `aider/aider/plan_manager.py:179`
- `Function` find_plan_by_id_or_latest((plan_id: str | None, root: str | Path)) — `aider/aider/plan_manager.py:185`

## Internal Call Graph

- `save_plan` -> `_now_id`
- `save_plan` -> `Plan`
- `save_plan` -> `_now_iso`
- `save_plan` -> `_plans_dir`
- `update_plan` -> `_plans_dir`
- `load_plan` -> `_plans_dir`
- `load_plan` -> `_parse_plan_file`
- `_parse_plan_file` -> `Plan`
- `list_plans` -> `_plans_dir`
- `list_plans` -> `_parse_plan_file`
- `delete_plan` -> `_plans_dir`
- `get_latest_plan` -> `list_plans`
- `find_plan_by_id_or_latest` -> `load_plan`
- `find_plan_by_id_or_latest` -> `get_latest_plan`
