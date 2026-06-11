---
phase: phase-01
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - lsr/repomap.py
  - tests/basic/test_repomap.py
  - lsr/coders/base_coder.py
  - lsr/models.py
  - lsr/openrouter.py
  - tests/basic/test_models.py
  - lsr/resources/model-settings.yml
autonomous: true
requirements:
  - STRIP-01
  - STRIP-02

must_haves:
  truths:
    - "lsr/repomap.py does not exist"
    - "python -X importtime -m lsr --version shows no tree_sitter, grep_ast, diskcache, or tqdm in trace"
    - "python -X importtime -m lsr --version shows no requests import triggered by openrouter"
    - "python -c 'import lsr.openrouter' completes in <5ms"
    - "pytest tests/ passes with zero new failures"
    - "Benchmark shows ~164ms improvement from Phase 1 changes"
  artifacts:
    - path: "lsr/coders/base_coder.py"
      provides: "Coder class with no repomap import or usage"
      must_not_contain: ["from lsr.repomap import RepoMap", "RepoMap is not None", "use_repo_map"]
    - path: "lsr/models.py"
      provides: "ModelSettings without use_repo_map; ModelInfoManager with lazy openrouter_manager"
      must_not_contain: ["use_repo_map", "self.openrouter_manager = OpenRouterModelManager()"]
    - path: "lsr/openrouter.py"
      provides: "OpenRouterModelManager with deferred requests import"
      must_not_contain: ["import requests"]
      must_contain: ["requests"]
    - path: "lsr/resources/model-settings.yml"
      provides: "Model settings YAML with no use_repo_map field"
      must_not_contain: ["use_repo_map"]
  key_links:
    - from: "lsr/coders/base_coder.py"
      to: "lsr.models.ModelSettings"
      pattern: "main_model.use_repo_map"
      state: "removed"
    - from: "lsr/models.py"
      to: "lsr.openrouter.OpenRouterModelManager"
      pattern: "self.openrouter_manager"
      state: "lazy property"
    - from: "lsr/openrouter.py"
      to: "requests"
      pattern: "import requests"
      state: "inside _update_cache method only"
    - from: "lsr/resources/model-settings.yml"
      to: "lsr.models.ModelSettings"
      pattern: "use_repo_map"
      state: "removed from all model entries"
---

## Phase Goal

**As a** LaTeX writer using LSR, **I want to** start the tool without loading code-repository mapping modules or niche provider HTTP libraries, **so that** cold-start time drops by ~164ms and I can begin editing faster.

<objective>
Remove all code and imports related to repomap (tree-sitter based code repository mapping) and defer loading of the `requests` library used only by the OpenRouter provider.

Purpose: Repomap has zero relevance to LaTeX document editing. OpenRouter is a niche provider; loading `requests` (146ms) for every user is wasteful.
Output: Deleted repomap module, cleaned imports in base_coder.py and models.py, lazy requests import in openrouter.py, lazy OpenRouterModelManager in models.py, updated tests, verified benchmark improvement.
</objective>

<execution_context>
@/home/smh/lsr-dev/.claude/gsd-core/workflows/execute-plan.md
@/home/smh/lsr-dev/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/phase-01/1-CONTEXT.md
</context>

## Decisions Implemented

- **D1**: Repomap must be deleted, not lazy-loaded. Delete `lsr/repomap.py` and `tests/basic/test_repomap.py`. Remove import in `base_coder.py`. Remove `use_repo_map` from `models.py` and `model-settings.yml`.
- **D2**: OpenRouter must not be default-loaded. Move `import requests` inside methods in `openrouter.py`. Defer `OpenRouterModelManager` instantiation in `ModelInfoManager`.
- **D3**: Git support is retained. Do not touch `lsr/repo.py` or git import chain.

## Artifacts This Phase Produces

This phase primarily **removes** code rather than adding new symbols. The following changes are made:

### Deleted Files
- `lsr/repomap.py` — entire module deleted
- `tests/basic/test_repomap.py` — entire test file deleted

### Modified Symbols (behavior changes)
- `lsr.coders.base_coder.Coder`:
  - `repo_map` class attribute remains `None` (no change)
  - `__init__` no longer references `use_repo_map` or instantiates `RepoMap`
  - `get_repo_map` method removed entirely
  - `get_chat_files_messages` simplified (repo_map branch removed)
- `lsr.models.ModelSettings`:
  - `use_repo_map: bool = False` field removed
- `lsr.models.Model.configure_model_settings`:
  - All `self.use_repo_map = True` assignments removed (~20 occurrences)
- `lsr.models.ModelInfoManager`:
  - `__init__` no longer eagerly creates `self.openrouter_manager`
  - New lazy property `openrouter_manager` that creates `OpenRouterModelManager()` on first access
- `lsr.openrouter.OpenRouterModelManager`:
  - `_update_cache` method now contains `import requests` as first statement
  - Module-level `import requests` removed
- `lsr/resources/model-settings.yml`:
  - All `use_repo_map: true` lines removed (~338 occurrences)

### Modified Test File
- `tests/basic/test_models.py`:
  - All `self.assertTrue(model.use_repo_map)` assertions removed (~16 occurrences)
  - `test_get_repo_map_tokens` retained (method still exists on Model)

<tasks>

<task type="auto">
  <name>Task 1: Delete repomap module and remove all references</name>
  <files>
    lsr/repomap.py
    tests/basic/test_repomap.py
    lsr/coders/base_coder.py
    lsr/models.py
    lsr/resources/model-settings.yml
  </files>
  <read_first>
    lsr/repomap.py
    tests/basic/test_repomap.py
    lsr/coders/base_coder.py
    lsr/models.py
    lsr/resources/model-settings.yml
  </read_first>
  <action>
    1. Delete `lsr/repomap.py` entirely.
    2. Delete `tests/basic/test_repomap.py` entirely.
    3. In `lsr/coders/base_coder.py`:
       - Remove the `try/except` import block at lines 50-53 (`from lsr.repomap import RepoMap` / `RepoMap = None`).
       - Keep the class attribute `repo_map = None` at line 106.
       - In `__init__`, remove the `use_repo_map` local variable and the conditional block that instantiates `RepoMap` (around lines 513-536). After removal, `self.repo_map` should remain `None` (the class default).
       - Remove the `get_repo_map` method entirely (around lines 774-808).
       - In `get_chat_files_messages`, simplify the `elif` branch at line 864 that checks `self.get_repo_map()` — since repo_map is always None, this branch never executes. Change to just the `else` branch (`files_content = self.gpt_prompts.files_no_full_files`).
       - Remove the `if self.repo_map:` block in `get_repo_info` (around lines 284-293) that prints repo-map token stats.
    4. In `lsr/models.py`:
       - Remove `use_repo_map: bool = False` from the `ModelSettings` dataclass (around line 125).
       - In `Model.configure_model_settings`, remove ALL `self.use_repo_map = True` assignments. These appear in model-specific blocks (o3-mini, gpt-4.1-mini, o1-mini, o1-preview, o1, deepseek-v3, deepseek-r1, llama3-70b, gpt-4, claude-3.5-sonnet, gpt-5.5, gpt-5.5-pro, and their provider-prefixed variants). Remove only the `self.use_repo_map = True` line from each block; keep all other settings in each block.
       - Keep `Model.get_repo_map_tokens()` method — it is still a valid utility even without repomap.
    5. In `lsr/resources/model-settings.yml`:
       - Remove ALL lines containing `use_repo_map: true` (approximately 338 occurrences across the file). Use `sed -i '/use_repo_map: true/d' lsr/resources/model-settings.yml` or equivalent.
       - Verify the file still parses as valid YAML after removal.
  </action>
  <verify>
    <automated>
      test ! -f lsr/repomap.py && test ! -f tests/basic/test_repomap.py && echo "Files deleted OK"
    </automated>
    <automated>
      grep -c "from lsr.repomap import RepoMap" lsr/coders/base_coder.py; test $? -eq 1
    </automated>
    <automated>
      grep -c "use_repo_map" lsr/coders/base_coder.py; test $? -eq 1
    </automated>
    <automated>
      grep -c "use_repo_map" lsr/models.py; test $? -eq 1
    </automated>
    <automated>
      grep -c "def get_repo_map" lsr/coders/base_coder.py; test $? -eq 1
    </automated>
    <automated>
      grep -c "use_repo_map" lsr/resources/model-settings.yml; test $? -eq 1
    </automated>
    <automated>
      python -c "import yaml; yaml.safe_load(open('lsr/resources/model-settings.yml'))" && echo "YAML valid"
    </automated>
  </verify>
  <done>
    - lsr/repomap.py and tests/basic/test_repomap.py do not exist
    - base_coder.py has no repomap import, no use_repo_map references, no get_repo_map method
    - models.py has no use_repo_map attribute or assignments
    - model-settings.yml has no use_repo_map lines and is valid YAML
    - All other model settings (edit_format, use_temperature, etc.) preserved
  </done>
  <acceptance_criteria>
    - `lsr/repomap.py` does not exist (verify: `test ! -f lsr/repomap.py`)
    - `tests/basic/test_repomap.py` does not exist (verify: `test ! -f tests/basic/test_repomap.py`)
    - `lsr/coders/base_coder.py` contains no line matching `from lsr.repomap import RepoMap` (verify: `grep -c "from lsr.repomap import RepoMap" lsr/coders/base_coder.py` returns non-zero exit code)
    - `lsr/coders/base_coder.py` contains no line matching `use_repo_map` (verify: `grep -c "use_repo_map" lsr/coders/base_coder.py` returns non-zero exit code)
    - `lsr/coders/base_coder.py` contains no `def get_repo_map` (verify: `grep -c "def get_repo_map" lsr/coders/base_coder.py` returns non-zero exit code)
    - `lsr/models.py` contains no line matching `use_repo_map` (verify: `grep -c "use_repo_map" lsr/models.py` returns non-zero exit code)
    - `lsr/resources/model-settings.yml` contains no line matching `use_repo_map` (verify: `grep -c "use_repo_map" lsr/resources/model-settings.yml` returns non-zero exit code)
    - `lsr/resources/model-settings.yml` is valid YAML (verify: `python -c "import yaml; yaml.safe_load(open('lsr/resources/model-settings.yml'))"`)
    - `lsr/coders/base_coder.py` still contains `repo_map = None` as a class attribute (verify: `grep -c "repo_map = None" lsr/coders/base_coder.py` returns 1)
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Defer openrouter and requests loading</name>
  <files>
    lsr/openrouter.py
    lsr/models.py
  </files>
  <read_first>
    lsr/openrouter.py
    lsr/models.py
  </read_first>
  <action>
    1. In `lsr/openrouter.py`:
       - Remove the module-level `import requests` at line 16.
       - Add `import requests` as the first statement inside the `_update_cache` method (around line 114), before the `requests.get()` call.
       - No other changes to openrouter.py.
    2. In `lsr/models.py`:
       - In `ModelInfoManager.__init__` (around line 194), remove the eager instantiation `self.openrouter_manager = OpenRouterModelManager()`.
       - Add a lazy property or getter method `openrouter_manager` to `ModelInfoManager` that creates and caches an `OpenRouterModelManager()` instance on first access. Store the instance in a private attribute (e.g., `_openrouter_manager`).
       - Update `set_verify_ssl` to use the lazy property: `if hasattr(self, "_openrouter_manager") and self._openrouter_manager:` instead of checking `hasattr(self, "openrouter_manager")`.
       - Keep the `from lsr.openrouter import OpenRouterModelManager` import at the top of models.py — this is acceptable because openrouter.py no longer imports requests at module level.
  </action>
  <verify>
    <automated>
      python -c "import lsr.openrouter; print('OK')" && python -c "import time; t=time.time(); import lsr.openrouter; print(f'{(time.time()-t)*1000:.1f}ms')"
    </automated>
    <automated>
      grep -n "import requests" lsr/openrouter.py | grep -q "_update_cache" && echo "requests inside method"
    </automated>
    <automated>
      grep -n "import requests" lsr/openrouter.py | grep -v "_update_cache" | grep -v "^#" | wc -l | xargs test 0 -eq
    </automated>
  </verify>
  <done>
    - openrouter.py has no module-level `import requests`
    - `_update_cache` method contains `import requests` as its first statement
    - `python -c "import lsr.openrouter"` completes in under 5ms
    - ModelInfoManager no longer eagerly creates OpenRouterModelManager in __init__
    - ModelInfoManager has a lazy property/getter for openrouter_manager
  </done>
  <acceptance_criteria>
    - `lsr/openrouter.py` has no module-level `import requests` (verify: `grep -n "import requests" lsr/openrouter.py | grep -v "_update_cache" | wc -l` returns 0)
    - `lsr/openrouter.py` `_update_cache` method contains `import requests` (verify: `grep -A2 "def _update_cache" lsr/openrouter.py | grep -c "import requests"` returns 1)
    - `python -c "import lsr.openrouter"` completes in under 5ms (verify: `python -c "import time; t=time.time(); import lsr.openrouter; assert (time.time()-t)*1000 < 5; print('OK')"`)
    - `lsr/models.py` `ModelInfoManager.__init__` does not contain `self.openrouter_manager = OpenRouterModelManager()` (verify: `grep -c "self.openrouter_manager = OpenRouterModelManager()" lsr/models.py` returns non-zero exit code)
    - `lsr/models.py` contains a lazy accessor for openrouter_manager (verify: `grep -c "_openrouter_manager" lsr/models.py` returns at least 1)
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 3: Update tests and verify benchmark</name>
  <files>
    tests/basic/test_models.py
  </files>
  <read_first>
    tests/basic/test_models.py
  </read_first>
  <action>
    1. In `tests/basic/test_models.py`:
       - Remove ALL `self.assertTrue(model.use_repo_map)` assertions. These appear in `test_configure_model_settings` and `test_gpt55_model_settings` (around lines 286, 291, 298, 305, 312, 319, 327, 335, 342, 349, 359, 372, 574, 592 — verify exact lines by reading the file first).
       - Keep `test_get_repo_map_tokens` — this method tests `Model.get_repo_map_tokens()` which is still a valid method.
       - Keep all other assertions in `test_configure_model_settings` and `test_gpt55_model_settings` (edit_format, use_temperature, use_system_prompt, streaming, etc.).
    2. Run the full test suite: `pytest tests/ -x`
    3. Run the import-time benchmark: `python -X importtime -m lsr --version 2>&1 | grep -E "tree_sitter|grep_ast|diskcache|tqdm|requests|lsr.repomap|lsr.openrouter"`
       - Verify NO matches for tree_sitter, grep_ast, diskcache, tqdm, requests, lsr.repomap.
       - Verify lsr.openrouter appears but with a small cumulative time (<5ms).
    4. Compare total startup time before (236ms for lsr.main) vs after. Target: ~164ms saved.
  </action>
  <verify>
    <automated>
      pytest tests/ -x --tb=short
    </automated>
    <automated>
      python -X importtime -m lsr --version 2>&1 | grep -E "tree_sitter|grep_ast|diskcache|tqdm|lsr.repomap" | wc -l | xargs test 0 -eq
    </automated>
    <automated>
      python -X importtime -m lsr --version 2>&1 | grep "requests" | wc -l | xargs test 0 -eq
    </automated>
    <automated>
      python -c "
import subprocess, sys
result = subprocess.run([sys.executable, '-X', 'importtime', '-m', 'lsr', '--version'], capture_output=True, text=True)
for line in result.stderr.splitlines():
    if 'lsr.main' in line:
        parts = line.split()
        for p in parts:
            if p.isdigit():
                cum = int(p)
                assert cum < 140000, f'lsr.main cumulative time {cum}us exceeds 140000us threshold'
                print(f'OK: lsr.main cumulative time = {cum}us')
                break
        break
"
    </automated>
  </verify>
  <done>
    - pytest tests/ passes with zero new failures
    - Import trace shows no tree_sitter, grep_ast, diskcache, tqdm, or requests
    - lsr.repomap does not appear in import trace
    - lsr.openrouter appears with <5ms cumulative time
    - Total lsr.main cumulative time is below 140000us (at least 100ms reduction from baseline 236170us)
  </done>
  <acceptance_criteria>
    - `pytest tests/ -x` exits with code 0 (verify: run command)
    - `python -X importtime -m lsr --version 2>&1 | grep -c "tree_sitter"` returns 0
    - `python -X importtime -m lsr --version 2>&1 | grep -c "grep_ast"` returns 0
    - `python -X importtime -m lsr --version 2>&1 | grep -c "diskcache"` returns 0
    - `python -X importtime -m lsr --version 2>&1 | grep -c "tqdm"` returns 0
    - `python -X importtime -m lsr --version 2>&1 | grep -c "lsr.repomap"` returns 0
    - `python -X importtime -m lsr --version 2>&1 | grep -c "requests"` returns 0
    - `python -X importtime -m lsr --version 2>&1 | grep "lsr.main"` shows cumulative time below 140000us (at least 100ms reduction from baseline 236170us)
  </acceptance_criteria>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Module import → execution | Untrusted: moving imports inside methods changes when exceptions are raised |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-phase-01-01 | Denial of Service | openrouter.py `_update_cache` | mitigate | `import requests` inside method must be wrapped in try/except; if requests is not installed, print informative error (already handled by existing except block) |
| T-phase-01-02 | Information Disclosure | models.py lazy property | accept | No PII involved; OpenRouterModelManager is a cache lookup utility |
| T-phase-01-03 | Denial of Service | base_coder.py repo_map removal | mitigate | Ensure `self.repo_map = None` class attribute remains so any external code referencing it gets None, not AttributeError |
| T-phase-01-04 | Denial of Service | model-settings.yml cleanup | mitigate | Remove `use_repo_map` lines from YAML to prevent TypeError when ModelSettings dataclass no longer has the field |
</threat_model>

<verification>
1. File deletion verified: `test ! -f lsr/repomap.py && test ! -f tests/basic/test_repomap.py`
2. Import removal verified: `grep` confirms no repomap/requests references in modified files
3. YAML cleanup verified: `grep` confirms no `use_repo_map` in model-settings.yml, YAML still parses
4. Lazy loading verified: `python -c "import lsr.openrouter"` completes in <5ms
5. Import trace verified: `python -X importtime -m lsr --version` shows no tree_sitter/grep_ast/diskcache/tqdm/requests
6. Test suite verified: `pytest tests/ -x` passes
7. Benchmark verified: Total lsr.main cumulative time below 140000us (at least 100ms reduction from baseline 236170us)
</verification>

<success_criteria>
- lsr/repomap.py and tests/basic/test_repomap.py are deleted
- lsr/coders/base_coder.py has no repomap import or usage
- lsr/models.py has no use_repo_map attribute or assignments
- lsr/resources/model-settings.yml has no use_repo_map lines and is valid YAML
- lsr/openrouter.py imports requests only inside _update_cache method
- lsr/models.py ModelInfoManager lazily creates OpenRouterModelManager
- tests/basic/test_models.py has no use_repo_map assertions
- pytest tests/ passes with zero new failures
- python -X importtime -m lsr --version shows no tree_sitter, grep_ast, diskcache, tqdm, or requests
- Benchmark shows lsr.main cumulative time below 140000us (at least 100ms reduction from baseline 236ms)
</success_criteria>

<output>
Create `.planning/phases/phase-01/phase-01-01-SUMMARY.md` when done
</output>
