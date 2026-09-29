"""Test isolation: tests must NEVER write into the real backend/data history.

Sets DATA_DIR to a throwaway temp dir before any backend module is imported.
(Previously every pytest run polluted backend/data/sessions.json + profile.json
with synthetic sessions, which showed up as fake history in the app.)
"""
import os
import tempfile

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="beready_test_data_")
