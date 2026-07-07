"""Regression guards for the runtime-perf structural optimizations (B3/B4).

These assert machine-independent *invariants* — not timings — so the startup
and chat-first-call gains do not silently regress. A timing threshold would be
flaky across machines/CI; a structural invariant ("this import is deferred",
"this work is lazy") is not.

Guarded invariants:
- B4: ``lsr.models`` import must NOT pull in ``requests`` (deferred openrouter chain).
- B3: ``ModelInfoManager`` must NOT be built at ``lsr.models`` import time (lazy
  singleton), so neither it nor ``~/.lsr/caches`` is created until first use.
- B3: ``Model()`` construction must defer ``validate_environment`` and model-info
  fetch to first use (lazy properties).
"""

import os
import subprocess
import sys


class TestLsrModelsImportIsLazy:
    """B3/B4: importing lsr.models must stay cheap."""

    def test_import_defers_requests_and_model_info_manager(self, tmp_path):
        """One fresh-interpreter check for three import-time invariants.

        - ``requests`` is not loaded (B4 deferred the openrouter chain).
        - ``model_info_manager._manager`` is still None (B3 lazy singleton).
        - ``~/.lsr/caches`` is not created (B3 defers ModelInfoManager construction).
        """
        code = (
            "import sys, pathlib\n"
            "import lsr.models\n"
            "mgr = lsr.models.model_info_manager\n"
            "cache = pathlib.Path.home() / '.lsr' / 'caches'\n"
            "ok = (\n"
            "    'requests' not in sys.modules\n"
            "    and mgr._manager is None\n"
            "    and not cache.exists()\n"
            ")\n"
            "sys.exit(0 if ok else 1)\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            env={**os.environ, "HOME": str(tmp_path)},
        )
        assert result.returncode == 0, (
            "lsr.models import regressed an import-time perf invariant "
            "(requests loaded, ModelInfoManager built eagerly, or cache-dir created):\n"
            + result.stderr.decode()
        )


class TestModelConstructionIsLazy:
    """B3: Model() construction defers validation and model-info to first use."""

    def test_construction_does_not_validate_or_fetch_info(self):
        from lsr.models import Model

        m = Model("gpt-4")
        assert (
            m._validation_result is None
        ), "Model.__init__ eagerly ran validate_environment (B3 regression)"
        assert m._info is None, "Model.__init__ eagerly fetched model info (B3 regression)"
