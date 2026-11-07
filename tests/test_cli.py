import json
import subprocess
import sys
from pathlib import Path
import pytest
import cli
from engine.params import load_preset
from engine.planner import build_plan, render_report

ROOT = Path(__file__).resolve().parent.parent
PRESETS = ["campus_lan", "metro_man", "global_wan"]


def run(argv, capsys):
    code = cli.main(argv)
    cap = capsys.readouterr()
    return code, cap.out, cap.err


def write_json(tmp_path, params, name="custom.json"):
    f = tmp_path / name
    f.write_text(json.dumps(params), encoding="utf-8")
    return str(f)


def test_list_shows_all_presets(capsys):
    code, out, _ = run(["list"], capsys)
    assert code == 0
    for n in PRESETS:
        assert n in out


@pytest.mark.parametrize("name", PRESETS)
def test_plan_preset_prints_full_report(name, capsys):
    code, out, err = run(["plan", "--preset", name], capsys)
    assert code == 0 and err == ""
    assert load_preset(name)["name"] in out
    assert "Architectural rationale log" in out


def test_plan_output_equals_planner_report(capsys):
    _, out, _ = run(["plan", "--preset", "metro_man"], capsys)
    assert out.strip() == render_report(build_plan(load_preset("metro_man"))).strip()


def test_unknown_preset_is_clean_error(capsys):
    code, out, err = run(["plan", "--preset", "nope"], capsys)
    assert code == 2 and out == ""
    assert "ERROR (InvalidParameterError)" in err
    assert "campus_lan" in err and "Traceback" not in err


def test_custom_valid_file(tmp_path, capsys):
    code, out, _ = run(["plan", "--custom", write_json(tmp_path, load_preset("metro_man"))], capsys)
    assert code == 0 and "Metro MAN" in out


def test_custom_invalid_values(tmp_path, capsys):
    p = load_preset("metro_man")
    p["endpoints"] = -1
    code, out, err = run(["plan", "--custom", write_json(tmp_path, p)], capsys)
    assert code == 2 and out == "" and "ERROR" in err


def test_custom_missing_file(tmp_path, capsys):
    code, _, err = run(["plan", "--custom", str(tmp_path / "missing.json")], capsys)
    assert code == 2 and "ERROR" in err


def test_address_exhaustion_is_clean_error(tmp_path, capsys):
    p = load_preset("campus_lan")
    p["root_cidr"] = "10.10.0.0/24"
    code, out, err = run(["plan", "--custom", write_json(tmp_path, p)], capsys)
    assert code == 2 and out == ""
    assert "AddressSpaceExhaustedError" in err


def test_preset_and_custom_together_rejected():
    with pytest.raises(SystemExit) as e:
        cli.main(["plan", "--preset", "metro_man", "--custom", "x.json"])
    assert e.value.code == 2


def test_plan_needs_a_source():
    with pytest.raises(SystemExit) as e:
        cli.main(["plan"])
    assert e.value.code == 2


def test_no_command_rejected():
    with pytest.raises(SystemExit) as e:
        cli.main([])
    assert e.value.code == 2


def test_out_file_written_and_matches(tmp_path, capsys):
    target = tmp_path / "sub" / "dir" / "report.txt"
    code, out, _ = run(["plan", "--preset", "global_wan", "--out", str(target)], capsys)
    assert code == 0 and target.exists()
    assert "Report written to" in out
    text = target.read_text(encoding="utf-8")
    assert "6. Architectural rationale log" in text
    assert text.strip() == render_report(build_plan(load_preset("global_wan"))).strip()


def test_check_link_access_run(capsys):
    code, out, _ = run(["check-link", "--distance", "50"], capsys)
    assert code == 0 and "Cat6a" in out


def test_check_link_22km_is_er(capsys):
    code, out, _ = run(["check-link", "--distance", "22000"], capsys)
    assert code == 0
    assert "10GBASE-ER" in out and "22000" in out
    assert "Choice:" in out and "Justification:" in out and "References:" in out


def test_check_link_copper_at_100m_allowed(capsys):
    code, out, _ = run(["check-link", "--distance", "100", "--media", "cat6a"], capsys)
    assert code == 0 and "Cat6a" in out


def test_check_link_copper_over_100m_is_physical_violation(capsys):
    code, out, err = run(["check-link", "--distance", "150", "--media", "cat6a"], capsys)
    assert code == 2 and out == ""
    assert "PhysicalDistanceViolationError" in err
    assert "attenuat" in err.lower()
    assert "Traceback" not in err


@pytest.mark.parametrize("d", ["nan", "inf", "-5", "0"])
def test_check_link_bad_distances_are_clean_errors(d, capsys):
    code, out, err = run(["check-link", "--distance", d], capsys)
    assert code == 2 and out == "" and "ERROR" in err and "Traceback" not in err


def test_check_link_non_numeric_distance_rejected_by_argparse():
    with pytest.raises(SystemExit) as e:
        cli.main(["check-link", "--distance", "abc"])
    assert e.value.code == 2


def test_runs_as_a_script_from_any_directory(tmp_path):
    r = subprocess.run([sys.executable, str(ROOT / "cli.py"), "check-link", "--distance", "50"],
                       cwd=tmp_path, capture_output=True, text=True)
    assert r.returncode == 0 and "Cat6a" in r.stdout


def test_script_violation_exit_code_and_no_traceback(tmp_path):
    r = subprocess.run([sys.executable, str(ROOT / "cli.py"), "check-link",
                        "--distance", "150", "--media", "cat6a"],
                       cwd=tmp_path, capture_output=True, text=True)
    assert r.returncode == 2
    assert "PhysicalDistanceViolationError" in r.stderr and "Traceback" not in r.stderr
