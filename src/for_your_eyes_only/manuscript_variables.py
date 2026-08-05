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

from for_your_eyes_only.mission import ATAC_MISSION, MISSION_SEED, SLUG, canonical_mission

__all__ = [
    "METRIC_TOKENS",
    "generate_variables",
    "load_manuscript_config",
    "resolve_manuscript_tree",
]

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PACKAGE_ROOT / "manuscript" / "config.yaml"

# --------------------------------------------------------------------------- #
# Domain-computed metrics (single source of truth for all result tokens)
# --------------------------------------------------------------------------- #


def _compute_mission_metrics() -> dict[str, str]:
    """Return deterministic string metrics computed from the domain modules."""
    sc = canonical_mission()
    route = sc.route
    fire = sc.fire
    link_budget = sc.link_budget

    return {
        "RESULT_ESCROW_THRESHOLD": str(sc.escrow_threshold),
        "RESULT_ESCROW_SHARES": str(sc.escrow_num_shares),
        "RESULT_ESCROW_KEY": str(sc.released_key),
        # Derived by comparing the released key's fingerprint against the
        # escrow's, never stapled: a literal here would render "True" in the
        # manuscript even if release started handing back the wrong key.
        "RESULT_RECOVERED_MATCH": str(sc.fingerprint_match),
        # Erasure-coded key recovery.
        "RESULT_RECOVERY_DATA_SYMBOLS": str(sc.recovery_code.data_symbols),
        "RESULT_RECOVERY_CODE_SYMBOLS": str(sc.recovery_code.code_symbols),
        "RESULT_RECOVERY_MATCH": str(list(sc.recovery_recovered) == list(sc.recovery_data)),
        # Underwater retrieval.
        "RESULT_WRECK_DEPTH": f"{sc.wreck_depth:g}",
        "RESULT_DIVE_TOTAL_S": f"{sc.retrieval.total_time_s:.3f}",
        "RESULT_SURFACE_OFFSET_E": f"{sc.retrieval.surface_offset[0]:.3f}",
        "RESULT_SURFACE_OFFSET_N": f"{sc.retrieval.surface_offset[1]:.3f}",
        "RESULT_TARGET_REACHABLE": str(sc.retrieval.target_reachable),
        # Island routing.
        "RESULT_ROUTE": " -> ".join(route.path),
        "RESULT_ROUTE_COST": f"{route.total_cost:.3f}",
        "RESULT_ROUTE_DISTANCE": f"{route.distance_nm:.2f}",
        "RESULT_ROUTE_HOPS": str(route.hops),
        # Targeting fire control.
        "RESULT_FIRE_FEASIBLE": str(fire.feasible),
        "RESULT_FIRE_INTERCEPT_S": f"{fire.intercept_time_s:.1f}",
        "RESULT_FIRE_LEAD_DEG": f"{fire.lead_angle_deg:.2f}",
        "RESULT_FIRE_COURSE_DEG": f"{fire.weapon_course_deg:.2f}",
        "RESULT_FIRE_CLOSEST_M": f"{fire.closest_approach_m:.1f}",
        # Acoustic link budget.
        "RESULT_LINK_SNR_DB": f"{link_budget.received_snr_db:.2f}",
        "RESULT_LINK_TL_DB": f"{link_budget.transmission_loss_db:.2f}",
        "RESULT_LINK_CLOSES": str(link_budget.closes),
        "RESULT_LINK_MAX_RANGE_M": f"{link_budget.max_range_m:.0f}",
        "RESULT_LINK_RANGE_M": f"{link_budget.range_m:.0f}",
        "RESULT_LINK_THRESHOLD_DB": f"{link_budget.detection_threshold_db:g}",
        "RESULT_LINK_MARGIN_DB": f"{link_budget.margin_db:.2f}",
        # Determinism parameters (so prose never types the seed by hand).
        "RESULT_MISSION_SEED": str(MISSION_SEED),
    }


#: Every token :func:`_compute_mission_metrics` produces. Derived from a single
#: canonical run rather than hand-listed, so the draft-mode "N/A" fallback can
#: never drift out of step with the live metric set.
METRIC_TOKENS: tuple[str, ...] = tuple(sorted(_compute_mission_metrics()))


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
    metrics_provider: Callable[[], dict[str, str]] = _compute_mission_metrics,
) -> dict[str, str]:
    """Compute the ``{{TOKEN}}`` → value mapping for the manuscript.

    Args:
        config_path: Override for ``manuscript/config.yaml``.
        require_outputs: When True (default), fail if the domain modules cannot
            produce live results (metrics fall back to "N/A" only in draft).
        now: A thunk returning the current UTC time (override for tests).
        metrics_provider: The callable that computes the live result metrics.
            A real seam, not a stand-in: tests pass an ordinary function that
            raises so the strict-vs-draft branch is exercised by real control
            flow rather than left as an untested claim.

    Returns:
        Fully populated token map, including domain-computed result tokens.
    """
    config = load_manuscript_config(config_path)
    paper = config.get("paper", {})
    if not isinstance(paper, dict):
        raise ValueError("manuscript config 'paper' section must be a mapping")

    metrics: dict[str, str]
    try:
        metrics = metrics_provider()
    except Exception as exc:  # noqa: BLE001 — strict gate converts any failure to N/A in draft
        if require_outputs:
            raise ValueError(f"mission domain modules failed to produce live outputs: {exc}") from exc
        metrics = dict.fromkeys(METRIC_TOKENS, "N/A")

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
