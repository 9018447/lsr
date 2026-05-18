# Community: aider-commit

- **Language:** python
- **Size:** 21
- **Cohesion:** 0.27
- **Description:** Directory-based community: repo

## Members (21)

- `Function` set_git_env((var_name, value, original_value)) — `aider/aider/repo.py:40`
- `Class` GitRepo() — `aider/aider/repo.py:52`
- `Function` __init__((
        self,
        io,
        fnames,
        git_dname,
        aider_ignore_file=None,
        models=None,
        attribute_author=True,
        attribute_committer=True,
        attribute_commit_message_author=False,
        attribute_commit_message_committer=False,
        commit_prompt=None,
        subtree_only=False,
        git_commit_verify=True,
        attribute_co_authored_by=False,  # Added parameter
        use_cwd=True,  # 新增参数：是否使用当前工作目录作为路径参考点
    )) — `aider/aider/repo.py:62`
- `Function` commit((
        self, fnames=None, context=None, message=None, aider_edits=False, coder=None
    )) — `aider/aider/repo.py:135`
- `Function` get_rel_repo_dir((self)) — `aider/aider/repo.py:338`
- `Function` get_commit_message((self, diffs, context, user_language=None)) — `aider/aider/repo.py:344`
- `Function` get_diffs((self, fnames=None)) — `aider/aider/repo.py:397`
- `Function` diff_commits((self, pretty, from_commit, to_commit)) — `aider/aider/repo.py:441`
- `Function` get_tracked_files((self)) — `aider/aider/repo.py:455`
- `Function` normalize_path((self, path)) — `aider/aider/repo.py:512`
- `Function` refresh_aider_ignore((self)) — `aider/aider/repo.py:542`
- `Function` git_ignored_file((self, path)) — `aider/aider/repo.py:565`
- `Function` ignored_file((self, fname)) — `aider/aider/repo.py:574`
- `Function` ignored_file_raw((self, fname)) — `aider/aider/repo.py:584`
- `Function` path_in_repo((self, path)) — `aider/aider/repo.py:609`
- `Function` abs_root_path((self, path)) — `aider/aider/repo.py:619`
- `Function` get_dirty_files((self)) — `aider/aider/repo.py:628`
- `Function` is_dirty((self, path=None)) — `aider/aider/repo.py:645`
- `Function` get_head_commit((self)) — `aider/aider/repo.py:651`
- `Function` get_head_commit_sha((self, short=False)) — `aider/aider/repo.py:657`
- `Function` get_head_commit_message((self, default=None)) — `aider/aider/repo.py:665`

## Internal Call Graph

- `commit` -> `is_dirty`
- `commit` -> `get_diffs`
- `commit` -> `get_commit_message`
- `commit` -> `abs_root_path`
- `commit` -> `set_git_env`
- `commit` -> `commit`
- `commit` -> `get_head_commit_sha`
- `get_diffs` -> `path_in_repo`
- `get_tracked_files` -> `normalize_path`
- `get_tracked_files` -> `ignored_file`
- `ignored_file` -> `refresh_aider_ignore`
- `ignored_file` -> `ignored_file_raw`
- `ignored_file_raw` -> `normalize_path`
- `path_in_repo` -> `get_tracked_files`
- `path_in_repo` -> `normalize_path`
- `is_dirty` -> `path_in_repo`
- `is_dirty` -> `is_dirty`
- `get_head_commit_sha` -> `get_head_commit`
- `get_head_commit_message` -> `get_head_commit`
