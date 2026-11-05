"""Built-in quiz package providers loaded during application bootstrap."""

from quiz_packages.ag.legacy_v1 import create_provider as create_ag_provider
from quiz_packages.ag.legacy_v1.runtime import create_runtime_provider as create_ag_runtime
from quiz_packages.scl.legacy_v1 import create_provider as create_scl_provider
from quiz_packages.scl.legacy_v1.runtime import create_runtime_provider as create_scl_runtime


BUILTIN_PACKAGE_FACTORIES = (create_ag_provider, create_scl_provider)
BUILTIN_RUNTIME_FACTORIES = (create_ag_runtime, create_scl_runtime)
