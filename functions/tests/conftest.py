"""
conftest.py — shared pytest fixtures for the functions test suite.

Stubs Azure SDK packages that are only available at runtime on Azure, so tests
can run locally without installing the full Azure SDK.  All azure.* modules that
are imported at the top level of production code are replaced with MagicMock-based
stubs before any test module is loaded.
"""

import sys
import types
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Build a fake azure namespace package tree
# ---------------------------------------------------------------------------

def _stub(name: str, **attrs) -> types.ModuleType:
    """Create a stub module and register it in sys.modules."""
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


# azure (namespace package)
azure_pkg = sys.modules.get("azure")
if azure_pkg is None or not isinstance(azure_pkg, types.ModuleType):
    azure_pkg = _stub("azure")


# ---------------------------------------------------------------------------
# azure.functions
# ---------------------------------------------------------------------------

class _FakeHttpResponse:
    """Minimal stand-in for azure.functions.HttpResponse."""
    def __init__(self, body="", status_code=200, mimetype="application/json", headers=None):
        self._body = body.encode() if isinstance(body, str) else body
        self.status_code = status_code
        self.mimetype = mimetype
        self.headers = headers or {}

    def get_body(self) -> bytes:
        return self._body


_af = _stub(
    "azure.functions",
    HttpResponse=_FakeHttpResponse,
    HttpRequest=MagicMock,
)
azure_pkg.functions = _af  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# azure.cosmos (used by schema.service, export/*, etc.)
# ---------------------------------------------------------------------------

_cosmos_exc = _stub("azure.cosmos.exceptions", CosmosResourceNotFoundError=Exception)
_cosmos = _stub(
    "azure.cosmos",
    CosmosClient=MagicMock,
    exceptions=_cosmos_exc,
)
azure_pkg.cosmos = _cosmos  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# azure.storage.blob  (used by export/geojson.py for SAS URLs)
# ---------------------------------------------------------------------------

_blob = _stub(
    "azure.storage.blob",
    BlobSasPermissions=MagicMock,
    generate_blob_sas=MagicMock(return_value="fake-sas-token"),
)
_storage = _stub("azure.storage", blob=_blob)
azure_pkg.storage = _storage  # type: ignore[attr-defined]
# Keep the blob stub registered (do NOT call _stub again — it would overwrite it)
sys.modules["azure.storage"] = _storage
# sys.modules["azure.storage.blob"] is already set by the _stub("azure.storage.blob") call above


# ---------------------------------------------------------------------------
# azure.eventgrid  (used by pipeline — keep it out of the way)
# ---------------------------------------------------------------------------

_stub("azure.eventgrid", EventGridPublisherClient=MagicMock, EventGridEvent=MagicMock)


# ---------------------------------------------------------------------------
# Ensure the azure package is in sys.modules under its real name
# ---------------------------------------------------------------------------

sys.modules["azure"] = azure_pkg

# ---------------------------------------------------------------------------
# Eagerly import submodules so they become attributes of their parent packages.
# This is required for unittest.mock.patch("pkg.submodule.thing") to work —
# patch resolves the chain via getattr(), which only works if the submodule
# has already been imported and registered on the parent package object.
# ---------------------------------------------------------------------------

import importlib as _il
import os as _os
import sys as _sys

_functions_root = _os.path.join(_os.path.dirname(__file__), "..")
if _functions_root not in _sys.path:
    _sys.path.insert(0, _functions_root)

for _mod in [
    "schema.service",
    "schema.handlers",
    "schema.defaults",
    "export.geojson",
    "export.csv_export",
]:
    try:
        _il.import_module(_mod)
    except Exception:
        pass  # if a submodule fails to import, tests will skip it naturally
