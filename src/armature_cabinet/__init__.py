"""armature-cabinet — compile cabinet agent folders into Armature agent bundles."""
from .loader import load_package
from .compiler import compile_agent, compile_safety_fragment, compose_description

__all__ = ["load_package", "compile_agent", "compile_safety_fragment", "compose_description"]
__version__ = "0.1.0"
