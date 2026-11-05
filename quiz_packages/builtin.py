"""Built-in quiz package providers loaded during application bootstrap."""

from quiz_packages.ag.legacy_v1 import create_provider as create_ag_provider
from quiz_packages.scl.legacy_v1 import create_provider as create_scl_provider


BUILTIN_PACKAGE_FACTORIES = (create_ag_provider, create_scl_provider)
