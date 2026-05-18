# Community: aider-sample

- **Language:** python
- **Size:** 7
- **Cohesion:** 0.05
- **Description:** Directory-based community: args

## Members (7)

- `Function` resolve_aiderignore_path((path_str, git_root=None)) — `aider/aider/args.py:22`
- `Function` default_env_file((git_root)) — `aider/aider/args.py:31`
- `Function` get_parser((default_config_files, git_root)) — `aider/aider/args.py:35`
- `Function` get_md_help(()) — `aider/aider/args.py:882`
- `Function` get_sample_yaml(()) — `aider/aider/args.py:895`
- `Function` get_sample_dotenv(()) — `aider/aider/args.py:908`
- `Function` main(()) — `aider/aider/args.py:921`

## Internal Call Graph

- `get_parser` -> `resolve_aiderignore_path`
- `get_parser` -> `default_env_file`
- `get_md_help` -> `get_parser`
- `get_sample_yaml` -> `get_parser`
- `get_sample_dotenv` -> `get_parser`
- `main` -> `get_md_help`
- `main` -> `get_sample_dotenv`
- `main` -> `get_sample_yaml`
- `main` -> `get_parser`
