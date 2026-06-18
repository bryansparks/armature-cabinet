"""armature-cabinet — compile cabinet agent folders into Armature agent bundles."""
from .errors import CabinetError
from .loader import load_package
from .validate import validate_package
from .compiler import compile_agent, compile_safety_fragment, compose_description

__all__ = [
    "CabinetError",
    "load_package",
    "validate_package",
    "compile_agent",
    "compile_safety_fragment",
    "compose_description",
]
__version__ = "0.1.0"
