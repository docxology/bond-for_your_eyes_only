"""Manuscript variable hydration for the ATAC mission package.

Every ``{{TOKEN}}`` in ``manuscript/[0-9]*.md`` resolves through
:func:`generate_variables`. Metrics are never hand-authored in prose — they
flow through this module so the manuscript cannot drift from the code or from
the computed mission outputs.

The strict-mode gate (``require_outputs=True``) verifies the domain modules
actually produce results (a non-empty escrow, a real route, a finite dive
plan) rather than ``N/A`` fallbacks, matching the exemplar's live-output
requirement while staying infrastructure-free.
"""

from __future__ import annotations

import platform
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import yaml

from for_your_eyes_only import island_routing, key_escrow, underwater_retrieval
from for_your_eyes_only.mission import ATAC_MISSION, SLUG

__all__ = ["generate_variables", "load_manuscript_config", "resolve_manuscript_tree"]

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PACKAGE_ROOT / "manuscript" / "config.yaml"

# --------------------------------------------------------------------------- #
# Domain-computed metrics (single source of truth for all result tokens)
# --------------------------------------------------------------------------- #


def _compute_mission_metrics() -> dict[str, str]:
    """Return deterministic string metrics computed from the domain modules."""
    # Escrow: build a canonical escrow and release with a quorum.
    escrow = key_escrow.create_escrow(
        4242,
        threshold=2,
        num_shares=3,
        custodian_labels=("q_branch", "m", "field_agent"),
        seed=7,
    )
    recovered = key_escrow.release_key(escrow, (0, 1))
    # Underwater: plan the canonical retrieval dive.
    planner = underwater_retrieval.RetrievalPlanner()
    retrieval = planner.plan()
    # Routing: plan the canonical insertion route.
    graph = island_routing.build_ionian_graph()
    route = island_routing.plan_route(graph, "corfu", "wreck_site", risk_weight=1.0)

    return {
        "RESULT_ESCROW_THRESHOLD": str(escrow.threshold),
        "RESULT_ESCROW_SHARES": str(escrow.num_shares),
        "RESULT_ESCROW_KEY": str(recovered),
        "RESULT_RECOVERED_MATCH": str(recovered == 4242),
        "RESULT_WRECK_DEPTH": f"{planner.wreck_depth:g}",
        "RESULT_DIVE_TOTAL_S": f"{retrieval.total_time_s:.3f}",
        "RESULT_SURFACE_OFFSET_E": f"{retrieval.surface_offset[0]:.3f}",
        "RESULT_SURFACE_OFFSET_N": f"{retrieval.surface_offset[1]:.3f}",
        "RESULT_TARGET_REACHABLE": str(retrieval.target_reachable),
        "RESULT_ROUTE": " -> ".join(route.path),
        "RESULT_ROUTE_COST": f"{route.total_cost:.3f}",
        "RESULT_ROUTE_DISTANCE": f"{route.distance_nm:.2f}",
        "RESULT_ROUTE_HOPS": str(route.hops),
    }


# --------------------------------------------------------------------------- #
# Config loading
# --------------------------------------------------------------------------- #


def load_manuscript_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load and validate ``manuscript/config.yaml`` (or an explicit path)."""
    path = Path(config_path) if config_path is not None else DEFAULT_CONFIG_PATH
    if not path.is_file():
        raise FileNotFoundError(f"manuscript config not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"manuscript config must be a top-level mapping, got {type(data).__name__}")
    return data


def generate_variables(
    *,
    config_path: str | Path | None = None,
    require_outputs: bool = True,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> dict[str, str]:
    """Compute the ``{{TOKEN}}`` → value mapping for the manuscript.

    Args:
        config_path: Override for ``manuscript/config.yaml``.
        require_outputs: When True (default), fail if the domain modules cannot
            produce live results (metrics fall back to "N/A" only in draft).
        now: A thunk returning the current UTC time (override for tests).

    Returns:
        Fully populated token map, including domain-computed result tokens.
    """
    config = load_manuscript_config(config_path)
    paper = config.get("paper", {})
    if not isinstance(paper, dict):
        raise ValueError("manuscript config 'paper' section must be a mapping")

    metrics: dict[str, str]
    try:
        metrics = _compute_mission_metrics()
    except Exception as exc:  # noqa: BLE001 — strict gate converts any failure to N/A in draft
        if require_outputs:
            raise ValueError(f"mission domain modules failed to produce live outputs: {exc}") from exc
        metrics = {
            key: "N/A"
            for key in (
                "RESULT_ESCROW_THRESHOLD",
                "RESULT_ESCROW_SHARES",
                "RESULT_ESCROW_KEY",
                "RESULT_RECOVERED_MATCH",
                "RESULT_WRECK_DEPTH",
                "RESULT_DIVE_TOTAL_S",
                "RESULT_SURFACE_OFFSET_E",
                "RESULT_SURFACE_OFFSET_N",
                "RESULT_TARGET_REACHABLE",
                "RESULT_ROUTE",
                "RESULT_ROUTE_COST",
                "RESULT_ROUTE_DISTANCE",
                "RESULT_ROUTE_HOPS",
            )
        }

    config_keywords = [str(k) for k in config.get("keywords", [])]
    variables: dict[str, str] = {
        **metrics,
        "BOND_IDENTITY": SLUG,
        "BOND_CODENAME": ATAC_MISSION,
        "BOND_VERSION": str(paper.get("version", "")),
        "BOND_TITLE": str(paper.get("title", "")),
        "BOND_SUBTITLE": str(paper.get("subtitle", "")),
        "CONFIG_KEYWORDS": ", ".join(config_keywords),
        "CONFIG_NUM_KEYWORDS": str(len(config_keywords)),
        "PYTHON_VERSION": platform.python_version(),
        "GENERATION_TIMESTAMP": now().isoformat(timespec="seconds"),
    }
    return variables


def resolve_manuscript_tree(
    variables: dict[str, str],
    *,
    manuscript_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
    strict: bool = True,
) -> tuple[Path, list[str]]:
    """Copy each ``NN_*.md`` manuscript section to ``output/manuscript/``, substituting tokens.

    In strict mode (default) any leftover ``{{TOKEN}}`` fails resolution so the
    manuscript can never render with raw braces. Returns ``(output_dir, names)``.

    Note: sidecars such as ``SYNTAX.md`` and ``AGENTS.md`` are excluded — they
    legitimately illustrate ``{{TOKEN}}`` syntax.
    """
    token_re = re.compile(r"\{\{[A-Z0-9_]+\}\}")
    manuscript_dir = Path(manuscript_dir) if manuscript_dir is not None else PACKAGE_ROOT / "manuscript"
    output_dir = Path(output_dir) if output_dir is not None else PACKAGE_ROOT / "output" / "manuscript"
    resolved: list[str] = []
    for source in sorted(manuscript_dir.glob("[0-9][0-9]_*.md")):
        text = source.read_text(encoding="utf-8")
        for token, value in variables.items():
            text = text.replace("{{" + token + "}}", value)
        unresolved = sorted(set(token_re.findall(text)))
        if unresolved and strict:
            raise ValueError(f"unresolved manuscript tokens in {source.name}: {unresolved}")
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / source.name).write_text(text, encoding="utf-8")
        resolved.append(source.name)
    return output_dir, resolved
