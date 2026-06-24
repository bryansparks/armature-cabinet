from pathlib import Path
from armature_cabinet import load_package, compile_agent

FIX = Path(__file__).parent / "fixtures" / "security-triage"


def test_bundle_carries_agent_version():
    pkg = load_package(FIX)
    pkg.manifest["version"] = "0.2.0"  # simulate the new manifest field
    b = compile_agent(pkg)
    assert b["role"]["x_agent_version"] == "0.2.0"


def test_bundle_carries_richness_when_present():
    pkg = load_package(FIX)
    pkg.manifest["version"] = "0.2.0"
    pkg.manifest["summary"] = "Triage security alerts."
    pkg.manifest["tags"] = ["security", "triage"]
    pkg.manifest["maturity"] = "L1"
    pkg.manifest["runtime_hints"] = {"default_cost_tier": "T2"}
    b = compile_agent(pkg)
    assert b["role"]["x_summary"] == "Triage security alerts."
    assert b["role"]["x_tags"] == ["security", "triage"]
    assert b["role"]["x_maturity"] == "L1"
    assert b["role"]["x_runtime_hints"] == {"default_cost_tier": "T2"}


def test_bundle_omits_meta_when_absent():
    b = compile_agent(load_package(FIX))  # no version/summary set on fixture
    assert "x_agent_version" not in b["role"]
