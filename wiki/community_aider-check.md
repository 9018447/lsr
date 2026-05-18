# Community: aider-check

- **Language:** python
- **Size:** 20
- **Cohesion:** 0.06
- **Description:** Directory-based community: main

## Members (20)

- `Function` check_config_files_for_yes((config_files)) — `aider/aider/main.py:43`
- `Function` get_git_root(()) — `aider/aider/main.py:64`
- `Function` guessed_wrong_repo((io, git_root, fnames, git_dname)) — `aider/aider/main.py:73`
- `Function` make_new_repo((git_root, io)) — `aider/aider/main.py:92`
- `Function` setup_git((git_root, io)) — `aider/aider/main.py:105`
- `Function` check_gitignore((git_root, io, ask=True)) — `aider/aider/main.py:161`
- `Function` check_streamlit_install((io)) — `aider/aider/main.py:216`
- `Function` write_streamlit_credentials(()) — `aider/aider/main.py:225`
- `Function` launch_gui((args)) — `aider/aider/main.py:241`
- `Function` parse_lint_cmds((lint_cmds, io)) — `aider/aider/main.py:286`
- `Function` generate_search_path_list((default_file, git_root, command_line_file)) — `aider/aider/main.py:313`
- `Function` register_models((git_root, model_settings_fname, io, verbose=False)) — `aider/aider/main.py:343`
- `Function` load_dotenv_files((git_root, dotenv_fname, encoding="utf-8")) — `aider/aider/main.py:369`
- `Function` register_litellm_models((git_root, model_metadata_fname, io, verbose=False)) — `aider/aider/main.py:398`
- `Function` sanity_check_repo((repo, io)) — `aider/aider/main.py:424`
- `Function` main((argv=None, input=None, output=None, force_git_root=None, return_coder=False)) — `aider/aider/main.py:465`
- `Function` get_io((pretty)) — `aider/aider/main.py:568`
- `Function` is_first_run_of_new_version((io, verbose=False)) — `aider/aider/main.py:1218`
- `Function` check_and_load_imports((io, is_first_run, verbose=False)) — `aider/aider/main.py:1261`
- `Function` load_slow_imports((swallow=True)) — `aider/aider/main.py:1295`

## Internal Call Graph

- `make_new_repo` -> `check_gitignore`
- `setup_git` -> `make_new_repo`
- `launch_gui` -> `write_streamlit_credentials`
- `launch_gui` -> `main`
- `register_models` -> `generate_search_path_list`
- `register_models` -> `register_models`
- `load_dotenv_files` -> `generate_search_path_list`
- `register_litellm_models` -> `generate_search_path_list`
- `register_litellm_models` -> `register_litellm_models`
- `main` -> `get_git_root`
- `main` -> `check_config_files_for_yes`
- `main` -> `load_dotenv_files`
- `main` -> `get_io`
- `main` -> `check_streamlit_install`
- `main` -> `launch_gui`
- `main` -> `guessed_wrong_repo`
- `main` -> `main`
- `main` -> `setup_git`
- `main` -> `check_gitignore`
- `main` -> `is_first_run_of_new_version`
- `main` -> `check_and_load_imports`
- `main` -> `register_models`
- `main` -> `register_litellm_models`
- `main` -> `parse_lint_cmds`
- `main` -> `sanity_check_repo`
- `check_and_load_imports` -> `load_slow_imports`
