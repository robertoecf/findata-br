"""Data-source adapters — one sub-package per external provider.

Each sub-package is self-contained: models, client, and (optional) parser
live together, and only the top-level `__init__` re-exports the public
surface used by the API routers and the CLI.
"""
