"""Load the reproduction configuration without inventing paper values."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .heuristics.grasp import GraspConfig
from .heuristics.greedy import GreedyConfig


DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "config.yaml"


def load_config(path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as stream:
        value = yaml.safe_load(stream)
    if not isinstance(value, dict):
        raise ValueError("configuration root must be a mapping")
    return value


def paper_greedy_config(config: dict[str, Any]) -> GreedyConfig:
    values = config["greedy"]
    return GreedyConfig.paper(
        deadlock_in_target=bool(values["deadlock_in_target"]),
        deadlock_in_stack=bool(values["deadlock_in_stack"]))


def grasp_config_with_assumptions(config: dict[str, Any]) -> GraspConfig:
    """Build runnable GRASP config, explicitly using documented assumptions."""
    values = config["grasp"]
    assumed = values["assumptions"]
    return GraspConfig(
        max_iteration=int(values["max_iteration"]),
        hood_num=int(values["hood_num"]),
        noimpr_limit=int(values["noimpr_limit"]),
        ma=int(assumed["ma"]), mb=int(assumed["mb"]), mc=int(assumed["mc"]),
        initfit=float(assumed["initfit"]), alpha=float(assumed["alpha"]),
        initial_temp=float(assumed["initial_temp"]),
        final_temp=float(assumed["final_temp"]), beta=float(assumed["beta"]),
        k=float(assumed["boltzmann_k"]))


def grasp_config_from_paper(config: dict[str, Any]) -> GraspConfig:
    """Build GRASP config from paper-published values only.

    The paper publishes ``max-iteration = 10``, ``hood-num = 10`` and
    ``NOIMPRLIMIT = 3`` after tuning. It names the remaining LNS parameters but
    does not give numeric values, so strict paper mode refuses to fabricate a
    runnable configuration when any required value is absent.
    """
    values = config["grasp"]
    unpublished = values["unpublished"]
    required = {
        "ma": int,
        "mb": int,
        "mc": int,
        "initfit": float,
        "alpha": float,
        "initial_temp": float,
        "final_temp": float,
        "beta": float,
        "boltzmann_k": float,
    }
    missing = [name for name in required if unpublished.get(name) is None]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(
            "cannot build a strict paper-faithful GRASP configuration; "
            f"the paper does not publish: {joined}")
    return GraspConfig(
        max_iteration=int(values["max_iteration"]),
        hood_num=int(values["hood_num"]),
        noimpr_limit=int(values["noimpr_limit"]),
        ma=int(unpublished["ma"]),
        mb=int(unpublished["mb"]),
        mc=int(unpublished["mc"]),
        initfit=float(unpublished["initfit"]),
        alpha=float(unpublished["alpha"]),
        initial_temp=float(unpublished["initial_temp"]),
        final_temp=float(unpublished["final_temp"]),
        beta=float(unpublished["beta"]),
        k=float(unpublished["boltzmann_k"]))
