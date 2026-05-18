# Community: coders-show

- **Language:** python
- **Size:** 103
- **Cohesion:** 0.28
- **Description:** Directory-based community: coders

## Members (103)

- `Class` AskPrompts() — `aider/coders/ask_prompts.py:6`
- `Function` compute_line_hash((line_num, line_content)) — `aider/coders/base_coder.py:57`
- `Function` add_line_hashes((content)) — `aider/coders/base_coder.py:63`
- `Function` batch_add_line_hashes((contents, max_workers=0)) — `aider/coders/base_coder.py:79`
- `Function` strip_line_hashes((text)) — `aider/coders/base_coder.py:120`
- `Class` UnknownEditFormat() — `aider/coders/base_coder.py:130`
- `Function` __init__((self, edit_format, valid_formats)) — `aider/coders/base_coder.py:131`
- `Class` MissingAPIKeyError() — `aider/coders/base_coder.py:139`
- `Class` FinishReasonLength() — `aider/coders/base_coder.py:143`
- `Function` wrap_fence((name)) — `aider/coders/base_coder.py:147`
- `Class` Coder() — `aider/coders/base_coder.py:162`
- `Function` create((
        self,
        main_model=None,
        edit_format=None,
        io=None,
        from_coder=None,
        summarize_from_coder=True,
        **kwargs,
    )) — `aider/coders/base_coder.py:201`
- `Function` clone((self, **kwargs)) — `aider/coders/base_coder.py:286`
- `Function` get_announcements((self)) — `aider/coders/base_coder.py:290`
- `Function` __init__((
        self,
        main_model,
        io,
        repo=None,
        fnames=None,
        add_gitignore_files=False,
        read_only_fnames=None,
        show_diffs=False,
        auto_commits=True,
        dirty_commits=True,
        dry_run=False,
        map_tokens=1024,
        verbose=False,
        stream=True,
        use_git=True,
        cur_messages=None,
        done_messages=None,
        restore_chat_history=False,
        auto_lint=True,
        auto_test=False,
        lint_cmds=None,
        test_cmd=None,
        aider_commit_hashes=None,
        map_mul_no_files=8,
        commands=None,
        summarizer=None,
        total_cost=0.0,
        analytics=None,
        map_refresh="auto",
        cache_prompts=False,
        num_cache_warming_pings=0,
        suggest_shell_commands=True,
        chat_language=None,
        commit_language=None,
        detect_urls=True,
        ignore_mentions=None,
        total_tokens_sent=0,
        total_tokens_received=0,
        file_watcher=None,
        auto_copy_context=False,
        auto_accept_architect=True,
        use_cwd=True,  # 新增参数：是否使用当前工作目录作为路径参考点
        current_plan=None,
        parallel_hashline=None,
    )) — `aider/coders/base_coder.py:384`
- `Function` setup_lint_cmds((self, lint_cmds)) — `aider/coders/base_coder.py:663`
- `Function` show_announcements((self)) — `aider/coders/base_coder.py:669`
- `Function` add_rel_fname((self, rel_fname)) — `aider/coders/base_coder.py:675`
- `Function` drop_rel_fname((self, fname)) — `aider/coders/base_coder.py:679`
- `Function` abs_root_path((self, path)) — `aider/coders/base_coder.py:685`
- `Function` show_pretty((self)) — `aider/coders/base_coder.py:704`
- `Function` _stop_waiting_spinner((self)) — `aider/coders/base_coder.py:714`
- `Function` get_abs_fnames_content((self)) — `aider/coders/base_coder.py:723`
- `Function` choose_fence((self)) — `aider/coders/base_coder.py:734`
- `Function` get_files_content((self, fnames=None)) — `aider/coders/base_coder.py:766`
- `Function` get_read_only_files_content((self)) — `aider/coders/base_coder.py:792`
- `Function` get_cur_message_text((self)) — `aider/coders/base_coder.py:816`
- `Function` get_ident_mentions((self, text)) — `aider/coders/base_coder.py:821`
- `Function` get_ident_filename_matches((self, idents)) — `aider/coders/base_coder.py:827`
- `Function` get_repo_map((self, force_refresh=False)) — `aider/coders/base_coder.py:852`
- `Function` get_repo_messages((self)) — `aider/coders/base_coder.py:893`
- `Function` get_readonly_files_messages((self)) — `aider/coders/base_coder.py:906`
- `Function` get_chat_files_messages((self)) — `aider/coders/base_coder.py:936`
- `Function` get_images_message((self, fnames)) — `aider/coders/base_coder.py:964`
- `Function` run_stream((self, user_message)) — `aider/coders/base_coder.py:1011`
- `Function` init_before_message((self)) — `aider/coders/base_coder.py:1016`
- `Function` run((self, with_message=None, preproc=True)) — `aider/coders/base_coder.py:1028`
- `Function` copy_context((self)) — `aider/coders/base_coder.py:1046`
- `Function` get_input((self)) — `aider/coders/base_coder.py:1050`
- `Function` preproc_user_input((self, inp)) — `aider/coders/base_coder.py:1068`
- `Function` run_one((self, user_message, preproc)) — `aider/coders/base_coder.py:1080`
- `Function` check_and_open_urls((self, exc, friendly_msg=None)) — `aider/coders/base_coder.py:1128`
- `Function` check_for_urls((self, inp: str)) — `aider/coders/base_coder.py:1145`
- `Function` keyboard_interrupt((self)) — `aider/coders/base_coder.py:1166`
- `Function` summarize_start((self)) — `aider/coders/base_coder.py:1182`
- `Function` summarize_worker((self)) — `aider/coders/base_coder.py:1194`
- `Function` summarize_end((self)) — `aider/coders/base_coder.py:1206`
- `Function` move_back_cur_messages((self, message)) — `aider/coders/base_coder.py:1218`
- `Function` normalize_language((self, lang_code)) — `aider/coders/base_coder.py:1230`
- `Function` get_user_language((self)) — `aider/coders/base_coder.py:1276`
- `Function` get_platform_info((self)) — `aider/coders/base_coder.py:1309`
- `Function` fmt_system_prompt((self, prompt)) — `aider/coders/base_coder.py:1354`
- `Function` format_chat_chunks((self)) — `aider/coders/base_coder.py:1410`
- `Function` format_messages((self)) — `aider/coders/base_coder.py:1539`
- `Function` warm_cache((self, chunks)) — `aider/coders/base_coder.py:1546`
- `Function` warm_cache_worker(()) — `aider/coders/base_coder.py:1563`
- `Function` check_tokens((self, messages)) — `aider/coders/base_coder.py:1604`
- `Function` send_message((self, inp)) — `aider/coders/base_coder.py:1627`
- `Function` reply_completed((self)) — `aider/coders/base_coder.py:1855`
- `Function` show_exhausted_error((self)) — `aider/coders/base_coder.py:1858`
- `Function` lint_edited((self, fnames)) — `aider/coders/base_coder.py:1915`
- `Function` __del__((self)) — `aider/coders/base_coder.py:1931`
- `Function` add_assistant_reply_to_cur_messages((self)) — `aider/coders/base_coder.py:1935`
- `Function` get_file_mentions((self, content, ignore_current=False)) — `aider/coders/base_coder.py:1949`
- `Function` check_for_file_mentions((self, content)) — `aider/coders/base_coder.py:2005`
- `Function` send((self, messages, model=None, functions=None)) — `aider/coders/base_coder.py:2030`
- `Function` show_send_output((self, completion)) — `aider/coders/base_coder.py:2083`
- `Function` show_send_output_stream((self, completion)) — `aider/coders/base_coder.py:2147`
- `Function` live_incremental_response((self, final)) — `aider/coders/base_coder.py:2226`
- `Function` render_incremental_response((self, final)) — `aider/coders/base_coder.py:2232`
- `Function` remove_reasoning_content((self)) — `aider/coders/base_coder.py:2235`
- `Function` calculate_and_show_tokens_and_cost((self, messages, completion=None)) — `aider/coders/base_coder.py:2243`
- `Function` format_cost((value)) — `aider/coders/base_coder.py:2302`
- `Function` compute_costs_from_tokens((
        self, prompt_tokens, completion_tokens, cache_write_tokens, cache_hit_tokens
    )) — `aider/coders/base_coder.py:2323`
- `Function` show_usage_report((self)) — `aider/coders/base_coder.py:2355`
- `Function` get_multi_response_content_in_progress((self, final=False)) — `aider/coders/base_coder.py:2381`
- `Function` get_rel_fname((self, fname)) — `aider/coders/base_coder.py:2390`
- `Function` get_inchat_relative_files((self)) — `aider/coders/base_coder.py:2401`
- `Function` is_file_safe((self, fname)) — `aider/coders/base_coder.py:2405`
- `Function` get_all_relative_files((self)) — `aider/coders/base_coder.py:2411`
- `Function` get_all_abs_files((self)) — `aider/coders/base_coder.py:2422`
- `Function` get_addable_relative_files((self)) — `aider/coders/base_coder.py:2427`
- `Function` check_for_dirty_commit((self, path)) — `aider/coders/base_coder.py:2435`
- `Function` allowed_to_edit((self, path)) — `aider/coders/base_coder.py:2451`
- `Function` check_added_files((self)) — `aider/coders/base_coder.py:2506`
- `Function` prepare_to_edit((self, edits)) — `aider/coders/base_coder.py:2533`
- `Function` apply_updates((self)) — `aider/coders/base_coder.py:2560`
- `Function` parse_partial_args((self)) — `aider/coders/base_coder.py:2602`
- `Function` get_context_from_history((self, history)) — `aider/coders/base_coder.py:2631`
- `Function` auto_commit((self, edited, context=None)) — `aider/coders/base_coder.py:2639`
- `Function` show_auto_commit_outcome((self, res)) — `aider/coders/base_coder.py:2663`
- `Function` show_undo_hint((self)) — `aider/coders/base_coder.py:2671`
- `Function` dirty_commit((self)) — `aider/coders/base_coder.py:2679`
- `Function` get_edits((self, mode="update")) — `aider/coders/base_coder.py:2693`
- `Function` apply_edits((self, edits)) — `aider/coders/base_coder.py:2696`
- `Function` apply_edits_dry_run((self, edits)) — `aider/coders/base_coder.py:2699`
- `Function` run_shell_commands((self)) — `aider/coders/base_coder.py:2702`
- `Function` handle_shell_commands((self, commands_str, group)) — `aider/coders/base_coder.py:2718`
- `Class` EditBlockPrompts() — `aider/coders/editblock_prompts.py:7`
- `Class` PlanCoder() — `aider/coders/plan_coder.py:12`
- `Function` get_edits((self)) — `aider/coders/plan_coder.py:16`
- `Function` apply_edits((self, edits)) — `aider/coders/plan_coder.py:20`
- `Class` PlanPrompts() — `aider/coders/plan_prompts.py:11`

## Internal Call Graph

- `add_line_hashes` -> `compute_line_hash`
- `batch_add_line_hashes` -> `add_line_hashes`
- `__init__` -> `__init__`
- `create` -> `clone`
- `create` -> `UnknownEditFormat`
- `clone` -> `create`
- `get_announcements` -> `get_inchat_relative_files`
- `get_announcements` -> `get_rel_fname`
- `__init__` -> `check_added_files`
- `__init__` -> `abs_root_path`
- `__init__` -> `summarize_start`
- `__init__` -> `setup_lint_cmds`
- `show_announcements` -> `get_announcements`
- `add_rel_fname` -> `abs_root_path`
- `add_rel_fname` -> `check_added_files`
- `drop_rel_fname` -> `abs_root_path`
- `get_abs_fnames_content` -> `get_rel_fname`
- `choose_fence` -> `get_abs_fnames_content`
- `get_files_content` -> `get_abs_fnames_content`
- `get_files_content` -> `get_rel_fname`
- `get_files_content` -> `batch_add_line_hashes`
- `get_read_only_files_content` -> `get_rel_fname`
- `get_read_only_files_content` -> `batch_add_line_hashes`
- `get_ident_filename_matches` -> `get_all_relative_files`
- `get_repo_map` -> `get_cur_message_text`
- `get_repo_map` -> `get_file_mentions`
- `get_repo_map` -> `get_ident_mentions`
- `get_repo_map` -> `get_ident_filename_matches`
- `get_repo_map` -> `get_all_abs_files`
- `get_repo_map` -> `get_repo_map`
- `get_repo_messages` -> `get_repo_map`
- `get_readonly_files_messages` -> `get_read_only_files_content`
- `get_readonly_files_messages` -> `get_images_message`
- `get_chat_files_messages` -> `get_files_content`
- `get_chat_files_messages` -> `get_repo_map`
- `get_chat_files_messages` -> `get_images_message`
- `get_images_message` -> `get_rel_fname`
- `run_stream` -> `init_before_message`
- `run_stream` -> `send_message`
- `run` -> `run_one`
- `run` -> `copy_context`
- `run` -> `get_input`
- `run` -> `show_undo_hint`
- `run` -> `keyboard_interrupt`
- `get_input` -> `get_inchat_relative_files`
- `get_input` -> `get_rel_fname`
- `get_input` -> `get_input`
- `get_input` -> `get_addable_relative_files`
- `preproc_user_input` -> `run`
- `preproc_user_input` -> `check_for_file_mentions`
- `preproc_user_input` -> `check_for_urls`
- `run_one` -> `init_before_message`
- `run_one` -> `preproc_user_input`
- `run_one` -> `send_message`
- `summarize_start` -> `summarize_end`
- `move_back_cur_messages` -> `summarize_start`
- `get_user_language` -> `normalize_language`
- `get_platform_info` -> `get_user_language`
- `fmt_system_prompt` -> `get_user_language`
- `fmt_system_prompt` -> `get_platform_info`
- `format_chat_chunks` -> `choose_fence`
- `format_chat_chunks` -> `fmt_system_prompt`
- `format_chat_chunks` -> `summarize_end`
- `format_chat_chunks` -> `get_repo_messages`
- `format_chat_chunks` -> `get_readonly_files_messages`
- `format_chat_chunks` -> `get_chat_files_messages`
- `format_messages` -> `format_chat_chunks`
- `send_message` -> `check_tokens`
- `send_message` -> `warm_cache`
- `send_message` -> `show_pretty`
- `send_message` -> `send`
- `send_message` -> `check_and_open_urls`
- `send_message` -> `get_multi_response_content_in_progress`
- `send_message` -> `live_incremental_response`
- `send_message` -> `_stop_waiting_spinner`
- `send_message` -> `show_usage_report`
- `send_message` -> `add_assistant_reply_to_cur_messages`
- `send_message` -> `show_exhausted_error`
- `send_message` -> `parse_partial_args`
- `send_message` -> `check_for_file_mentions`
- `send_message` -> `reply_completed`
- `send_message` -> `apply_updates`
- `send_message` -> `auto_commit`
- `send_message` -> `move_back_cur_messages`
- `send_message` -> `lint_edited`
- `send_message` -> `run_shell_commands`
- `lint_edited` -> `abs_root_path`
- `get_file_mentions` -> `get_all_relative_files`
- `get_file_mentions` -> `get_addable_relative_files`
- `get_file_mentions` -> `get_inchat_relative_files`
- `get_file_mentions` -> `get_rel_fname`
- `check_for_file_mentions` -> `get_file_mentions`
- `check_for_file_mentions` -> `add_rel_fname`
- `send` -> `show_send_output_stream`
- `send` -> `show_send_output`
- `send` -> `calculate_and_show_tokens_and_cost`
- `send` -> `keyboard_interrupt`
- `send` -> `parse_partial_args`
- `show_send_output` -> `_stop_waiting_spinner`
- `show_send_output` -> `render_incremental_response`
- `show_send_output` -> `show_pretty`
- `show_send_output` -> `FinishReasonLength`
- `show_send_output_stream` -> `FinishReasonLength`
- `show_send_output_stream` -> `_stop_waiting_spinner`
- `show_send_output_stream` -> `show_pretty`
- `show_send_output_stream` -> `live_incremental_response`
- `live_incremental_response` -> `render_incremental_response`
- `render_incremental_response` -> `get_multi_response_content_in_progress`
- `calculate_and_show_tokens_and_cost` -> `compute_costs_from_tokens`
- `calculate_and_show_tokens_and_cost` -> `format_cost`
- `get_inchat_relative_files` -> `get_rel_fname`
- `is_file_safe` -> `abs_root_path`
- `get_all_relative_files` -> `get_inchat_relative_files`
- `get_all_abs_files` -> `get_all_relative_files`
- `get_all_abs_files` -> `abs_root_path`
- `get_addable_relative_files` -> `get_all_relative_files`
- `get_addable_relative_files` -> `get_inchat_relative_files`
- `get_addable_relative_files` -> `get_rel_fname`
- `allowed_to_edit` -> `abs_root_path`
- `allowed_to_edit` -> `check_for_dirty_commit`
- `allowed_to_edit` -> `check_added_files`
- `prepare_to_edit` -> `allowed_to_edit`
- `prepare_to_edit` -> `dirty_commit`
- `apply_updates` -> `get_edits`
- `apply_updates` -> `apply_edits_dry_run`
- `apply_updates` -> `prepare_to_edit`
- `apply_updates` -> `apply_edits`
- `auto_commit` -> `get_context_from_history`
- `auto_commit` -> `show_auto_commit_outcome`
- `run_shell_commands` -> `handle_shell_commands`
