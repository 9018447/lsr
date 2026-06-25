import json
import os
import re
import subprocess
import sys
import threading
import traceback
import webbrowser
from dataclasses import fields
from pathlib import Path

try:
    import git
except ImportError:
    git = None

import importlib_resources
import shtab
from dotenv import load_dotenv

from lsr import __version__, models, urls, utils
from lsr.args import get_parser
from lsr.coders import Coder
from lsr.coders.base_coder import UnknownEditFormat
from lsr.format_settings import format_settings, scrub_sensitive_info
from lsr.history import ChatSummary
from lsr.io import InputOutput
from lsr.llm import litellm  # noqa: F401; properly init litellm on launch
from lsr.models import ModelSettings
from lsr.onboarding import offer_openrouter_oauth, select_default_model
from lsr.repo import ANY_GIT_ERROR, ANY_VCS_ERROR, Repo
from lsr.report import report_uncaught_exceptions
from lsr.versioncheck import check_version, install_from_main_branch, install_upgrade
from lsr.watch import FileWatcher

from .dump import dump  # noqa: F401


def check_config_files_for_yes(config_files):
    found = False
    for config_file in config_files:
        if Path(config_file).exists():
            try:
                with open(config_file, "r") as f:
                    for line in f:
                        if line.strip().startswith("yes:"):
                            print("Configuration error detected.")
                            print(f"The file {config_file} contains a line starting with 'yes:'")
                            print("Please replace 'yes:' with 'yes-always:' in this file.")
                            found = True
            except Exception:
                pass
    return found


def get_vcs_root():
    """Try and guess the repo root, preferring jj over git."""
    try:
        cwd = Path.cwd()
    except OSError:
        cwd = Path(".")

    # Prefer jj when a colocated .jj directory exists.
    try:
        result = subprocess.run(
            ["jj", "root"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
            errors="replace",
        )
        return result.stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError, OSError):
        pass

    try:
        repo = git.Repo(search_parent_directories=True)
        return repo.working_tree_dir
    except (git.InvalidGitRepositoryError, FileNotFoundError):
        return None


def guessed_wrong_repo(io, vcs_root, fnames, git_dname):
    """After we parse the args, we can determine the real repo. Did we guess wrong?"""

    try:
        check_repo = Path(Repo.create(io, fnames, git_dname).root).resolve()
    except (OSError,) + ANY_VCS_ERROR:
        return

    # we had no guess, rely on the "true" repo result
    if not vcs_root:
        return str(check_repo)

    vcs_root = Path(vcs_root).resolve()
    if check_repo == vcs_root:
        return

    return str(check_repo)


def make_new_repo(vcs_root, io):
    try:
        git.Repo.init(vcs_root)
        subprocess.run(
            ["jj", "git", "init", "--colocate"],
            cwd=vcs_root,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        check_gitignore(vcs_root, io, False)
    except ANY_VCS_ERROR as err:  # issue #1233
        io.tool_error(f"Unable to create VCS repo in {vcs_root}")
        io.tool_output(str(err))
        return

    io.tool_output(f"VCS repository created in {vcs_root}")


def setup_vcs(vcs_root, io):
    try:
        cwd = Path.cwd()
    except OSError:
        cwd = None

    repo = None

    if vcs_root:
        try:
            repo = git.Repo(vcs_root)
        except ANY_VCS_ERROR:
            pass
    elif cwd == Path.home():
        io.tool_warning(
            "You should probably run lsr in your project's directory, not your home dir."
        )
        return
    elif cwd and io.confirm_ask(
        "No repo found, create one to track lsr's changes (recommended)?"
    ):
        vcs_root = str(cwd.resolve())
        make_new_repo(vcs_root, io)
        try:
            repo = git.Repo(vcs_root)
        except ANY_VCS_ERROR:
            pass

    if not repo:
        return

    try:
        user_name = repo.git.config("--get", "user.name") or None
    except git.exc.GitCommandError:
        user_name = None

    try:
        user_email = repo.git.config("--get", "user.email") or None
    except git.exc.GitCommandError:
        user_email = None

    if user_name and user_email:
        return repo.working_tree_dir

    with repo.config_writer() as git_config:
        if not user_name:
            git_config.set_value("user", "name", "Your Name")
            io.tool_warning('Update git name with: git config user.name "Your Name"')
        if not user_email:
            git_config.set_value("user", "email", "you@example.com")
            io.tool_warning('Update git email with: git config user.email "you@example.com"')

    return repo.working_tree_dir


def check_gitignore(vcs_root, io, ask=True):
    if not vcs_root:
        return

    try:
        repo = git.Repo(vcs_root)
        patterns_to_add = []

        if not repo.ignored(".lsr"):
            patterns_to_add.append(".lsr*")

        env_path = Path(vcs_root) / ".env"
        if env_path.exists() and not repo.ignored(".env"):
            patterns_to_add.append(".env")

        if not patterns_to_add:
            return

        gitignore_file = Path(vcs_root) / ".gitignore"
        if gitignore_file.exists():
            try:
                content = io.read_text(gitignore_file)
                if content is None:
                    return
                if not content.endswith("\n"):
                    content += "\n"
            except OSError as e:
                io.tool_error(f"Error when trying to read {gitignore_file}: {e}")
                return
        else:
            content = ""
    except ANY_VCS_ERROR:
        return

    if ask:
        io.tool_output("You can skip this check with --no-gitignore")
        if not io.confirm_ask(f"Add {', '.join(patterns_to_add)} to .gitignore (recommended)?"):
            return

    content += "\n".join(patterns_to_add) + "\n"

    try:
        io.write_text(gitignore_file, content)
        io.tool_output(f"Added {', '.join(patterns_to_add)} to .gitignore")
    except OSError as e:
        io.tool_error(f"Error when trying to write to {gitignore_file}: {e}")
        io.tool_output(
            "Try running with appropriate permissions or manually add these patterns to .gitignore:"
        )
        for pattern in patterns_to_add:
            io.tool_output(f"  {pattern}")


def check_streamlit_install(io):
    return utils.check_pip_install_extra(
        io,
        "streamlit",
        "You need to install the lsr browser feature",
        ["lsr[help]"],
    )


def parse_lint_cmds(lint_cmds, io):
    err = False
    res = dict()
    for lint_cmd in lint_cmds:
        if re.match(r"^[a-z]+:.*", lint_cmd):
            pieces = lint_cmd.split(":")
            lang = pieces[0]
            cmd = lint_cmd[len(lang) + 1 :]
            lang = lang.strip()
        else:
            lang = None
            cmd = lint_cmd

        cmd = cmd.strip()

        if cmd:
            res[lang] = cmd
        else:
            io.tool_error(f'Unable to parse --lint-cmd "{lint_cmd}"')
            io.tool_output('The arg should be "language: cmd --args ..."')
            io.tool_output('For example: --lint-cmd "python: flake8 --select=E9"')
            err = True
    if err:
        return
    return res


def generate_search_path_list(default_file, vcs_root, command_line_file):
    files = []
    files.append(Path.home() / default_file)  # homedir
    if vcs_root:
        files.append(Path(vcs_root) / default_file)  # git root
    files.append(default_file)
    if command_line_file:
        files.append(command_line_file)

    resolved_files = []
    for fn in files:
        try:
            resolved_files.append(Path(fn).resolve())
        except OSError:
            pass

    files = resolved_files
    files.reverse()
    uniq = []
    for fn in files:
        if fn not in uniq:
            uniq.append(fn)
    uniq.reverse()
    files = uniq
    files = list(map(str, files))
    files = list(dict.fromkeys(files))

    return files


def register_models(vcs_root, model_settings_fname, io, verbose=False):
    model_settings_files = generate_search_path_list(
        ".lsr.model.settings.yml", vcs_root, model_settings_fname
    )

    try:
        files_loaded = models.register_models(model_settings_files)
        if len(files_loaded) > 0:
            if verbose:
                io.tool_output("Loaded model settings from:")
                for file_loaded in files_loaded:
                    io.tool_output(f"  - {file_loaded}")  # noqa: E221
        elif verbose:
            io.tool_output("No model settings files loaded")
    except Exception as e:
        io.tool_error(f"Error loading lsr model settings: {e}")
        return 1

    if verbose:
        io.tool_output("Searched for model settings files:")
        for file in model_settings_files:
            io.tool_output(f"  - {file}")

    return None


def load_dotenv_files(vcs_root, dotenv_fname, encoding="utf-8"):
    # Standard .env file search path
    dotenv_files = generate_search_path_list(
        ".env",
        vcs_root,
        dotenv_fname,
    )

    # Explicitly add the OAuth keys file to the beginning of the list
    oauth_keys_file = Path.home() / ".lsr" / "oauth-keys.env"
    if oauth_keys_file.exists():
        # Insert at the beginning so it's loaded first (and potentially overridden)
        dotenv_files.insert(0, str(oauth_keys_file.resolve()))
        # Remove duplicates if it somehow got included by generate_search_path_list
        dotenv_files = list(dict.fromkeys(dotenv_files))

    loaded = []
    for fname in dotenv_files:
        try:
            if Path(fname).exists():
                load_dotenv(fname, override=True, encoding=encoding)
                loaded.append(fname)
        except OSError as e:
            print(f"OSError loading {fname}: {e}")
        except Exception as e:
            print(f"Error loading {fname}: {e}")
    return loaded


def register_litellm_models(vcs_root, model_metadata_fname, io, verbose=False):
    model_metadata_files = []

    # Add the resource file path
    resource_metadata = importlib_resources.files("lsr.resources").joinpath("model-metadata.json")
    model_metadata_files.append(str(resource_metadata))

    model_metadata_files += generate_search_path_list(
        ".lsr.model.metadata.json", vcs_root, model_metadata_fname
    )

    try:
        model_metadata_files_loaded = models.register_litellm_models(model_metadata_files)
        if len(model_metadata_files_loaded) > 0 and verbose:
            io.tool_output("Loaded model metadata from:")
            for model_metadata_file in model_metadata_files_loaded:
                io.tool_output(f"  - {model_metadata_file}")  # noqa: E221
    except Exception as e:
        io.tool_error(f"Error loading model metadata models: {e}")
        return 1


def sanity_check_repo(repo, io):
    if not repo:
        return True

    if repo.vcs == "git" and (not repo.repo or not repo.repo.working_tree_dir):
        io.tool_error("The git repo does not seem to have a working tree?")
        return False

    bad_ver = False
    try:
        repo.get_tracked_files()
        if not repo.vcs_error:
            return True
        error_msg = str(repo.vcs_error)
    except UnicodeDecodeError as exc:
        error_msg = (
            "Failed to read the repository. This issue is likely caused by a path encoded "
            f'in a format different from the expected encoding "{sys.getfilesystemencoding()}".\n'
            f"Internal error: {str(exc)}"
        )
    except ANY_VCS_ERROR as exc:
        error_msg = str(exc)
        bad_ver = "version in (1, 2)" in error_msg
    except AssertionError as exc:
        error_msg = str(exc)
        bad_ver = True

    if bad_ver:
        io.tool_error("Aider only works with git repos with version number 1 or 2.")
        io.tool_output("You may be able to convert your repo: git update-index --index-version=2")
        io.tool_output("Or run lsr --no-git to proceed without using git.")
        io.offer_url(urls.git_index_version, "Open documentation url for more info?")
        return False

    io.tool_error("Unable to read repository, it may be corrupt?")
    io.tool_output(error_msg)
    return False


def main(argv=None, input=None, output=None, force_vcs_root=None, return_coder=False):
    report_uncaught_exceptions()

    if argv is None:
        argv = sys.argv[1:]

    if git is None:
        vcs_root = None
    elif force_vcs_root:
        vcs_root = force_vcs_root
    else:
        vcs_root = get_vcs_root()

    conf_fname = Path(".lsr.conf.yml")

    default_config_files = []
    try:
        default_config_files += [conf_fname.resolve()]  # CWD
    except OSError:
        pass

    if vcs_root:
        git_conf = Path(vcs_root) / conf_fname  # git root
        if git_conf not in default_config_files:
            default_config_files.append(git_conf)
    default_config_files.append(Path.home() / conf_fname)  # homedir
    default_config_files = list(map(str, default_config_files))

    parser = get_parser(default_config_files, vcs_root)
    try:
        args, unknown = parser.parse_known_args(argv)
    except AttributeError as e:
        if all(word in str(e) for word in ["bool", "object", "has", "no", "attribute", "strip"]):
            if check_config_files_for_yes(default_config_files):
                return 1
        raise e

    if args.verbose:
        print("Config files search order, if no --config:")
        for file in default_config_files:
            exists = "(exists)" if Path(file).exists() else ""
            print(f"  - {file} {exists}")

    default_config_files.reverse()

    parser = get_parser(default_config_files, vcs_root)

    args, unknown = parser.parse_known_args(argv)

    # Load the .env file specified in the arguments
    loaded_dotenvs = load_dotenv_files(vcs_root, args.env_file, args.encoding)

    # Parse again to include any arguments that might have been defined in .env
    args = parser.parse_args(argv)

    if args.shell_completions:
        # Ensure parser.prog is set for shtab, though it should be by default
        parser.prog = "lsr"
        print(shtab.complete(parser, shell=args.shell_completions))
        sys.exit(0)

    if git is None:
        args.git = False

    if not args.verify_ssl:
        import httpx

        os.environ["SSL_VERIFY"] = ""
        litellm._load_litellm()
        litellm._lazy_module.client_session = httpx.Client(verify=False)
        litellm._lazy_module.aclient_session = httpx.AsyncClient(verify=False)
        # Set verify_ssl on the model_info_manager
        models.model_info_manager.set_verify_ssl(False)

    if args.timeout:
        models.request_timeout = args.timeout

    if args.dark_mode:
        args.user_input_color = "#89b4fa"
        args.tool_error_color = "#f38ba8"
        args.tool_warning_color = "#fab387"
        args.assistant_output_color = "#b4befe"
        args.code_theme = "monokai"
        args.completion_menu_color = "#cdd6f4"
        args.completion_menu_bg_color = "#313244"
        args.completion_menu_current_color = "#1e1e2e"
        args.completion_menu_current_bg_color = "#cba6f7"

    if args.light_mode:
        args.user_input_color = "#1e66f5"
        args.tool_error_color = "#d20f39"
        args.tool_warning_color = "#fe640b"
        args.assistant_output_color = "#7287fd"
        args.code_theme = "default"
        args.completion_menu_color = "#4c4f69"
        args.completion_menu_bg_color = "#ccd0da"
        args.completion_menu_current_color = "#dce0e8"
        args.completion_menu_current_bg_color = "#8839ef"

    if return_coder and args.yes_always is None:
        args.yes_always = True

    from prompt_toolkit.enums import EditingMode

    editing_mode = EditingMode.VI if args.vim else EditingMode.EMACS

    def get_io(pretty):
        return InputOutput(
            pretty,
            args.yes_always,
            args.input_history_file,
            args.chat_history_file,
            input=input,
            output=output,
            user_input_color=args.user_input_color,
            tool_output_color=args.tool_output_color,
            tool_warning_color=args.tool_warning_color,
            tool_error_color=args.tool_error_color,
            completion_menu_color=args.completion_menu_color,
            completion_menu_bg_color=args.completion_menu_bg_color,
            completion_menu_current_color=args.completion_menu_current_color,
            completion_menu_current_bg_color=args.completion_menu_current_bg_color,
            assistant_output_color=args.assistant_output_color,
            code_theme=args.code_theme,
            dry_run=args.dry_run,
            encoding=args.encoding,
            line_endings=args.line_endings,
            llm_history_file=args.llm_history_file,
            editingmode=editing_mode,
            fancy_input=args.fancy_input,
            multiline_mode=args.multiline,
            notifications=args.notifications,
            notifications_command=args.notifications_command,
        )

    io = get_io(args.pretty)
    try:
        io.rule()
    except UnicodeEncodeError as err:
        if not io.pretty:
            raise err
        io = get_io(False)
        io.tool_warning("Terminal does not support pretty output (UnicodeDecodeError)")

    # Process any environment variables set via --set-env
    if args.set_env:
        for env_setting in args.set_env:
            try:
                name, value = env_setting.split("=", 1)
                os.environ[name.strip()] = value.strip()
            except ValueError:
                io.tool_error(f"Invalid --set-env format: {env_setting}")
                io.tool_output("Format should be: ENV_VAR_NAME=value")
                return 1

    # Process any API keys set via --api-key
    if args.api_key:
        for api_setting in args.api_key:
            try:
                provider, key = api_setting.split("=", 1)
                env_var = f"{provider.strip().upper()}_API_KEY"
                os.environ[env_var] = key.strip()
            except ValueError:
                io.tool_error(f"Invalid --api-key format: {api_setting}")
                io.tool_output("Format should be: provider=key")
                return 1

    if args.anthropic_api_key:
        os.environ["ANTHROPIC_API_KEY"] = args.anthropic_api_key

    if args.openai_api_key:
        os.environ["OPENAI_API_KEY"] = args.openai_api_key

    if args.openai_api_base:
        os.environ["OPENAI_API_BASE"] = args.openai_api_base
    if args.openai_api_version:
        io.tool_warning(
            "--openai-api-version is deprecated, use --set-env OPENAI_API_VERSION=<value>"
        )
        os.environ["OPENAI_API_VERSION"] = args.openai_api_version
    if args.openai_api_type:
        io.tool_warning("--openai-api-type is deprecated, use --set-env OPENAI_API_TYPE=<value>")
        os.environ["OPENAI_API_TYPE"] = args.openai_api_type
    if args.openai_organization_id:
        io.tool_warning(
            "--openai-organization-id is deprecated, use --set-env OPENAI_ORGANIZATION=<value>"
        )
        os.environ["OPENAI_ORGANIZATION"] = args.openai_organization_id

    if args.verbose:
        for fname in loaded_dotenvs:
            io.tool_output(f"Loaded {fname}")

    all_files = args.files + (args.file or [])
    fnames = [str(Path(fn).resolve()) for fn in all_files]
    read_only_fnames = []

    # Auto-load .lsr-template.md as read-only context
    lsr_template = Path(".lsr-template.md").resolve()
    if lsr_template.exists():
        read_only_fnames.append(str(lsr_template))
        io.tool_output(f"Loaded template context: {lsr_template.name}")

    for fn in args.read or []:
        path = Path(fn).expanduser().resolve()
        if path.is_dir():
            read_only_fnames.extend(str(f) for f in path.rglob("*") if f.is_file())
        else:
            read_only_fnames.append(str(path))

    if len(all_files) > 1:
        good = True
        for fname in all_files:
            if Path(fname).is_dir():
                io.tool_error(f"{fname} is a directory, not provided alone.")
                good = False
        if not good:
            io.tool_output(
                "Provide either a single directory of a repo, or a list of one or more files."
            )
            return 1

    git_dname = None
    if len(all_files) == 1:
        if Path(all_files[0]).is_dir():
            if args.git:
                git_dname = str(Path(all_files[0]).resolve())
                fnames = []
            else:
                io.tool_error(f"{all_files[0]} is a directory, but --no-git selected.")
                return 1

    # We can't know the git repo for sure until after parsing the args.
    # If we guessed wrong, reparse because that changes things like
    # the location of the config.yml and history files.
    if args.git and not force_vcs_root and git is not None:
        right_repo_root = guessed_wrong_repo(io, vcs_root, fnames, git_dname)
        if right_repo_root:
            return main(argv, input, output, right_repo_root, return_coder=return_coder)

    if args.just_check_update:
        update_available = check_version(io, just_check=True, verbose=args.verbose)
        return 0 if not update_available else 1

    if args.install_main_branch:
        success = install_from_main_branch(io)
        return 0 if success else 1

    if args.upgrade:
        success = install_upgrade(io)
        return 0 if success else 1

    if args.check_update:
        check_version(io, verbose=args.verbose)

    if args.git:
        vcs_root = setup_vcs(vcs_root, io)
        if args.gitignore:
            check_gitignore(vcs_root, io)

    if args.verbose:
        show = format_settings(parser, args)
        io.tool_output(show)

    cmd_line = " ".join(sys.argv)
    cmd_line = scrub_sensitive_info(args, cmd_line)
    io.tool_output(cmd_line, log_only=True)

    is_first_run = is_first_run_of_new_version(io, verbose=args.verbose)
    check_and_load_imports(io, is_first_run, verbose=args.verbose)

    register_models(vcs_root, args.model_settings_file, io, verbose=args.verbose)
    register_litellm_models(vcs_root, args.model_metadata_file, io, verbose=args.verbose)

    if args.list_models:
        models.print_matching_models(io, args.list_models)
        return 0

    # Process any command line aliases
    if args.alias:
        for alias_def in args.alias:
            # Split on first colon only
            parts = alias_def.split(":", 1)
            if len(parts) != 2:
                io.tool_error(f"Invalid alias format: {alias_def}")
                io.tool_output("Format should be: alias:model-name")
                return 1
            alias, model = parts
            models.MODEL_ALIASES[alias.strip()] = model.strip()

    selected_model_name = select_default_model(args, io)
    if not selected_model_name:
        # Error message is handled within select_default_model
        # It might have already offered OAuth if no model/keys were found.
        # If it failed here, we exit.
        return 1
    args.model = selected_model_name  # Update args with the selected model

    # Check if an OpenRouter model was selected/specified but the key is missing
    if args.model.startswith("openrouter/") and not os.environ.get("OPENROUTER_API_KEY"):
        io.tool_warning(
            f"The specified model '{args.model}' requires an OpenRouter API key, which was not"
            " found."
        )
        # Attempt OAuth flow because the specific model needs it
        if offer_openrouter_oauth(io):
            # OAuth succeeded, the key should now be in os.environ.
            # Check if the key is now present after the flow.
            if os.environ.get("OPENROUTER_API_KEY"):
                io.tool_output(
                    "OpenRouter successfully connected."
                )  # Inform user connection worked
            else:
                # This case should ideally not happen if offer_openrouter_oauth succeeded
                # but check defensively.
                io.tool_error(
                    "OpenRouter authentication seemed successful, but the key is still missing."
                )
                return 1
        else:
            # OAuth failed or was declined by the user
            io.tool_error(
                f"Unable to proceed without an OpenRouter API key for model '{args.model}'."
            )
            io.offer_url(urls.models_and_keys, "Open documentation URL for more info?")
            return 1

    main_model = models.Model(
        args.model,
        weak_model=args.weak_model,
        editor_model=args.editor_model,
        editor_edit_format=args.editor_edit_format,
        verbose=args.verbose,
    )

    # Check if deprecated remove_reasoning is set
    if main_model.remove_reasoning is not None:
        io.tool_warning(
            "Model setting 'remove_reasoning' is deprecated, please use 'reasoning_tag' instead."
        )

    # Default reasoning controls to avoid unconstrained thinking loops.
    # These are applied to every model that declares support; unsupported models skip them.
    DEFAULT_THINKING_BUDGET = "2000"
    DEFAULT_REASONING_EFFORT = "medium"

    reasoning_effort = (
        args.reasoning_effort if args.reasoning_effort is not None else DEFAULT_REASONING_EFFORT
    )
    thinking_budget = (
        args.thinking_budget
        if args.thinking_budget is not None
        else (args.thinking_tokens if args.thinking_tokens is not None else DEFAULT_THINKING_BUDGET)
    )
    reasoning_effort_explicit = args.reasoning_effort is not None
    thinking_budget_explicit = args.thinking_budget is not None or args.thinking_tokens is not None

    # Apply reasoning effort and thinking budget to all models that support them
    # (or when the user has disabled the compatibility check).
    if not args.check_model_accepts_settings or (
        main_model.accepts_settings and "reasoning_effort" in main_model.accepts_settings
    ):
        main_model.set_reasoning_effort(reasoning_effort)

    if not args.check_model_accepts_settings or (
        main_model.accepts_settings and "thinking_budget" in main_model.accepts_settings
    ):
        main_model.set_thinking_budget(thinking_budget)
    elif not args.check_model_accepts_settings or (
        main_model.accepts_settings and "thinking_tokens" in main_model.accepts_settings
    ):
        main_model.set_thinking_tokens(thinking_budget)

    # Show warnings about unsupported settings that are being ignored.
    # Only warn when the user explicitly asked for a setting the model doesn't accept;
    # defaults are applied silently if supported and skipped silently if not.
    if args.check_model_accepts_settings:
        settings_to_check = [
            {
                "value": reasoning_effort,
                "name": "reasoning_effort",
                "explicit": reasoning_effort_explicit,
            },
            {
                "value": thinking_budget,
                "name": "thinking_budget",
                "explicit": thinking_budget_explicit,
                # Some providers expose the same concept under a different key.
                "aliases": ["thinking_tokens"],
            },
        ]

        for setting in settings_to_check:
            accepted = main_model.accepts_settings or []
            names = [setting["name"]] + setting.get("aliases", [])
            if setting["explicit"] and not any(name in accepted for name in names):
                io.tool_warning(
                    f"Warning: {main_model.name} does not support '{setting['name']}', ignoring."
                )
                io.tool_output(
                    f"Use --no-check-model-accepts-settings to force the '{setting['name']}'"
                    " setting."
                )

    if args.verbose:
        io.tool_output("Model metadata:")
        io.tool_output(json.dumps(main_model.info, indent=4))

        io.tool_output("Model settings:")
        for attr in sorted(fields(ModelSettings), key=lambda x: x.name):
            val = getattr(main_model, attr.name)
            val = json.dumps(val, indent=4)
            io.tool_output(f"{attr.name}: {val}")

    lint_cmds = parse_lint_cmds(args.lint_cmd, io)
    if lint_cmds is None:
        return 1

    if args.show_model_warnings:
        problem = models.sanity_check_models(io, main_model)
        if problem:
            io.tool_output("You can skip this check with --no-show-model-warnings")

            try:
                io.offer_url(urls.model_warnings, "Open documentation url for more info?")
                io.tool_output()
            except KeyboardInterrupt:
                return 1

    repo = None
    if args.git:
        try:
            repo = Repo.create(
                io,
                fnames,
                git_dname,
                args.lsrignore,
                models=main_model.commit_message_models(),
                attribute_author=args.attribute_author,
                attribute_committer=args.attribute_committer,
                attribute_commit_message_author=args.attribute_commit_message_author,
                attribute_commit_message_committer=args.attribute_commit_message_committer,
                commit_prompt=args.commit_prompt,
                subtree_only=args.subtree_only,
                git_commit_verify=args.git_commit_verify,
                attribute_co_authored_by=args.attribute_co_authored_by,
                use_cwd=args.cwd_relative,
            )
        except FileNotFoundError:
            pass

    if not args.skip_sanity_check_repo:
        if not sanity_check_repo(repo, io):
            return 1

    if repo and not args.skip_sanity_check_repo:
        num_files = len(repo.get_tracked_files())

    from lsr.commands import Commands, SwitchCoder

    commands = Commands(
        io,
        None,
        verify_ssl=args.verify_ssl,
        args=args,
        parser=parser,
        verbose=args.verbose,
        editor=args.editor,
        original_read_only_fnames=read_only_fnames,
    )

    summarizer = ChatSummary(
        [main_model.weak_model, main_model],
        args.max_chat_history_tokens or main_model.max_chat_history_tokens,
    )

    if args.cache_prompts and args.map_refresh == "auto":
        args.map_refresh = "files"

    if not main_model.streaming:
        if args.stream:
            io.tool_warning(
                f"Warning: Streaming is not supported by {main_model.name}. Disabling streaming."
            )
        args.stream = False

    if args.map_tokens is None:
        map_tokens = main_model.get_repo_map_tokens()
    else:
        map_tokens = args.map_tokens

    # Track auto-commits configuration

    try:
        coder = Coder.create(
            main_model=main_model,
            edit_format=args.edit_format,
            io=io,
            repo=repo,
            fnames=fnames,
            read_only_fnames=read_only_fnames,
            show_diffs=args.show_diffs,
            auto_commits=args.auto_commits,
            dirty_commits=args.dirty_commits,
            dry_run=args.dry_run,
            map_tokens=map_tokens,
            verbose=args.verbose,
            stream=args.stream,
            use_git=args.git,
            restore_chat_history=args.restore_chat_history,
            auto_lint=args.auto_lint,
            auto_test=args.auto_test,
            lint_cmds=lint_cmds,
            test_cmd=args.test_cmd,
            commands=commands,
            summarizer=summarizer,
            map_refresh=args.map_refresh,
            cache_prompts=args.cache_prompts,
            map_mul_no_files=args.map_multiplier_no_files,
            num_cache_warming_pings=args.cache_keepalive_pings,
            suggest_shell_commands=args.suggest_shell_commands,
            chat_language=args.chat_language,
            commit_language=args.commit_language,
            detect_urls=args.detect_urls,
            auto_accept_architect=args.auto_accept_architect,
            add_gitignore_files=args.add_gitignore_files,
            use_cwd=args.cwd_relative,  # 新增参数
        )
    except UnknownEditFormat as err:
        io.tool_error(str(err))
        io.offer_url(urls.edit_formats, "Open documentation about edit formats?")
        return 1
    except ValueError as err:
        io.tool_error(str(err))
        return 1

    if return_coder:
        return coder

    ignores = []
    if vcs_root:
        ignores.append(str(Path(vcs_root) / ".gitignore"))
    if args.lsrignore:
        ignores.append(args.lsrignore)

    if args.watch_files:
        file_watcher = FileWatcher(
            coder,
            gitignores=ignores,
            verbose=args.verbose,
            root=str(Path.cwd()) if args.subtree_only else None,
        )
        coder.file_watcher = file_watcher

    coder.show_announcements()

    if args.show_prompts:
        coder.cur_messages += [
            dict(role="user", content="Hello!"),
        ]
        messages = coder.format_messages().all_messages()
        utils.show_messages(messages)
        return

    if args.lint:
        coder.commands.cmd_lint(fnames=fnames)

    if args.test:
        if not args.test_cmd:
            io.tool_error("No --test-cmd provided.")
            return 1
        coder.commands.cmd_test(args.test_cmd)
        if io.placeholder:
            coder.run(io.placeholder)

    if args.commit:
        if args.dry_run:
            io.tool_output("Dry run enabled, skipping commit.")
        else:
            coder.commands.cmd_commit()

    if args.lint or args.test or args.commit:
        return

    if args.show_repo_map:
        repo_map = coder.get_repo_map()
        if repo_map:
            io.tool_output(repo_map)
        return

    if args.apply:
        content = io.read_text(args.apply)
        if content is None:
            return
        coder.partial_response_content = content
        # For testing #2879
        # from lsr.coders.base_coder import all_fences
        # coder.fence = all_fences[1]
        coder.apply_updates()
        return

    if args.apply_clipboard_edits:
        args.edit_format = main_model.editor_edit_format
        args.message = "/paste"

    if args.show_release_notes is True:
        io.tool_output(f"Opening release notes: {urls.release_notes}")
        io.tool_output()
        webbrowser.open(urls.release_notes)
    elif args.show_release_notes is None and is_first_run:
        io.tool_output()
        io.offer_url(
            urls.release_notes,
            "Would you like to see what's new in this version?",
            allow_never=False,
        )

    if vcs_root and Path.cwd().resolve() != Path(vcs_root).resolve():
        io.tool_warning(
            "Note: in-chat filenames are always relative to the repo working dir, not the current"
            " working dir."
        )

        io.tool_output(f"Cur working dir: {Path.cwd()}")
        io.tool_output(f"Repo working dir: {vcs_root}")

    if args.stream and args.cache_prompts:
        io.tool_warning("Cost estimates may be inaccurate when using streaming and caching.")

    if args.message:
        io.add_to_input_history(args.message)
        io.tool_output()
        try:
            coder.run(with_message=args.message)
        except SwitchCoder:
            pass
        return

    if args.message_file:
        try:
            message_from_file = io.read_text(args.message_file)
            io.tool_output()
            coder.run(with_message=message_from_file)
        except FileNotFoundError:
            io.tool_error(f"Message file not found: {args.message_file}")
            return 1
        except IOError as e:
            io.tool_error(f"Error reading message file: {e}")
            return 1

        return

    if args.exit:
        return

    while True:
        try:
            coder.ok_to_warm_cache = bool(args.cache_keepalive_pings)
            coder.run()
            return
        except SwitchCoder as switch:
            coder.ok_to_warm_cache = False

            # Set the placeholder if provided
            if hasattr(switch, "placeholder") and switch.placeholder is not None:
                io.placeholder = switch.placeholder

            kwargs = dict(io=io, from_coder=coder)
            kwargs.update(switch.kwargs)
            if "show_announcements" in kwargs:
                del kwargs["show_announcements"]

            coder = Coder.create(**kwargs)

            if switch.kwargs.get("show_announcements") is not False:
                coder.show_announcements()


def is_first_run_of_new_version(io, verbose=False):
    """Check if this is the first run of a new version/executable combination"""
    installs_file = Path.home() / ".lsr" / "installs.json"
    key = (__version__, sys.executable)

    # Never show notes for .dev versions
    if ".dev" in __version__:
        return False

    if verbose:
        io.tool_output(
            f"Checking imports for version {__version__} and executable {sys.executable}"
        )
        io.tool_output(f"Installs file: {installs_file}")

    try:
        if installs_file.exists():
            with open(installs_file, "r") as f:
                installs = json.load(f)
            if verbose:
                io.tool_output("Installs file exists and loaded")
        else:
            installs = {}
            if verbose:
                io.tool_output("Installs file does not exist, creating new dictionary")

        is_first_run = str(key) not in installs

        if is_first_run:
            installs[str(key)] = True
            installs_file.parent.mkdir(parents=True, exist_ok=True)
            with open(installs_file, "w") as f:
                json.dump(installs, f, indent=4)

        return is_first_run

    except Exception as e:
        io.tool_warning(f"Error checking version: {e}")
        if verbose:
            io.tool_output(f"Full exception details: {traceback.format_exc()}")
        return True  # Safer to assume it's a first run if we hit an error


def check_and_load_imports(io, is_first_run, verbose=False):
    try:
        if is_first_run:
            if verbose:
                io.tool_output(
                    "First run for this version and executable, loading imports synchronously"
                )
            try:
                load_slow_imports(swallow=False)
            except Exception as err:
                io.tool_error(str(err))
                io.tool_output("Error loading required imports. Did you install lsr properly?")
                io.offer_url(urls.install_properly, "Open documentation url for more info?")
                sys.exit(1)

            if verbose:
                io.tool_output("Imports loaded and installs file updated")
        else:
            if verbose:
                io.tool_output("Not first run, loading imports in background thread")
            thread = threading.Thread(target=load_slow_imports)
            thread.daemon = True
            thread.start()

    except Exception as e:
        io.tool_warning(f"Error in loading imports: {e}")
        if verbose:
            io.tool_output(f"Full exception details: {traceback.format_exc()}")


def load_slow_imports(swallow=True):
    # These imports are deferred in various ways to
    # improve startup time.
    # This func is called either synchronously or in a thread
    # depending on whether it's been run before for this version and executable.

    try:
        import httpx  # noqa: F401
        import litellm  # noqa: F401
        import networkx  # noqa: F401
        import numpy  # noqa: F401
    except Exception as e:
        if not swallow:
            raise e


if __name__ == "__main__":
    status = main()
    sys.exit(status)
