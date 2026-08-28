import os
import subprocess
import sys


def test_run_ip_models_smoke(data20):
    cmd = [
        sys.executable,
        "-m",
        "pocrp_rc.experiments.run_ip_models",
        "--root",
        data20,
        "--models",
        "rl",
        "--max-c",
        "10",
        "--limit-per-subset",
        "1",
        "--time-limit",
        "30",
    ]
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        cmd, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        env=env, text=True, capture_output=True, check=True)
    assert "RL num" in result.stdout
    assert "1.00" in result.stdout


def test_main_strict_grasp_reports_missing_paper_values(data20):
    instance = os.path.join(data20, "Bay-3-6-3-10-8-2-0.pro")
    cmd = [
        sys.executable,
        "main.py",
        instance,
        "--algorithm",
        "grasp",
        "--strict-paper",
    ]
    result = subprocess.run(
        cmd, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        text=True, capture_output=True)
    assert result.returncode == 2
    assert "paper does not publish" in result.stderr
    assert "Traceback" not in result.stderr
