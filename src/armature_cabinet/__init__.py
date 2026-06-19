"""armature-cabinet — compile cabinet agent folders into Armature agent bundles."""
from .errors import CabinetError
from .loader import load_package
from .compiler import compile_agent, compile_safety_fragment, compose_description
from .validate import validate_package
from .select import select_skills
from .scaffold import build_folder, slugify
from .library import list_agents, build_all
from .team import generate_workflow, run_workflow

__all__ = [
    "CabinetError",
    "load_package",
    "compile_agent",
    "compile_safety_fragment",
    "compose_description",
    "validate_package",
    "select_skills",
    "build_folder",
    "slugify",
    "list_agents",
    "build_all",
    "generate_workflow",
    "run_workflow",
]
__version__ = "0.1.0"
