import subprocess
import re
import sys
import json
from pathlib import Path

# ARGUMENTS

if len(sys.argv) < 2:
    print("Usage: python script.py <path_to_project> [--exclude <pattern>]")
    sys.exit(1)

PROJECT = sys.argv[1]

exclude_pattern = None
if len(sys.argv) == 4 and sys.argv[2] in ("-e", "--exclude"):
    exclude_pattern = sys.argv[3]

PROJECT_NAME = PROJECT.replace("/", "_").replace("\\", "_")

OUT_DIR = Path("radon_runs")
OUT_DIR.mkdir(exist_ok=True)


def run(cmd):
    if exclude_pattern:
        cmd += ["-e", exclude_pattern]
    return subprocess.check_output(cmd, text=True)


def next_run_id():
    runs = []
    for p in OUT_DIR.glob(f"run_*_{PROJECT_NAME}"):
        parts = p.name.split("_")
        if len(parts) >= 3 and parts[1].isdigit():
            runs.append(int(parts[1]))
    return max(runs, default=0) + 1


run_id = next_run_id()
run_dir = OUT_DIR / f"run_{run_id}_{PROJECT_NAME}"
run_dir.mkdir()

# RAW

raw = run(["radon", "raw", PROJECT, "-s"])
run_dir.joinpath("raw.txt").write_text(raw)

total_block = raw.split("** Total **", 1)[1]

loc = int(re.search(r"LOC:\s+(\d+)", total_block).group(1))
comments = int(re.search(r"Comments:\s+(\d+)", total_block).group(1))
multi = int(re.search(r"Multi:\s+(\d+)", total_block).group(1))

number_of_comments = comments + multi

percentage_comments = int(
    re.search(r"\(C \+ M % L\):\s+(\d+)%", total_block).group(1)
)

# CC

cc = run(["radon", "cc", PROJECT, "-s", "-a"])
run_dir.joinpath("cc.txt").write_text(cc)

mean_per_block_cc = float(
    re.search(
        r"Average complexity: [A-F] \(([\d.]+)\)",
        cc
    ).group(1)
)

# HAL

hal_json = run(["radon", "hal", PROJECT, "-j"])
hal_data = json.loads(hal_json)
run_dir.joinpath("hal.json").write_text(hal_json)

hal_values = []
for file_data in hal_data.values():
    hal_values.append(file_data["total"]["effort"])

mean_per_file_halstead_effort = sum(hal_values) / len(hal_values)

# MI
mi_json = run(["radon", "mi", PROJECT, "-j"])
mi_data = json.loads(mi_json)
run_dir.joinpath("mi.json").write_text(mi_json)

mi_values = []
for file_data in mi_data.values():
    mi_values.append(file_data["mi"])

mean_per_file_mi = sum(mi_values) / len(mi_values)

# SUMMARY

summary = {
    "run": run_id,
    "project_path": PROJECT,
    "exclude": exclude_pattern,
    "raw": {
        "loc": loc,
        "number_of_comments": number_of_comments,
        "percentage_of_comments": percentage_comments,
    },
    "cc": {
        "mean_per_block_cc": mean_per_block_cc,
    },
    "halstead": {
        "mean_per_file_effort": mean_per_file_halstead_effort,
    },
    "mi": {
        "mean_per_file_mi": mean_per_file_mi,
    },
}

run_dir.joinpath("summary.json").write_text(
    json.dumps(summary, indent=2)
)

# STDOUT

print(f"Run: {run_id}")
print(f"Project path: {PROJECT}")
if (exclude_pattern): print(f"Exclude: {exclude_pattern}")
print(f"LOC: {loc}")
print(f"Number of comments: {number_of_comments}")
print(f"Percentage of comments: {percentage_comments}%")
print(f"Mean per-block CC: {mean_per_block_cc}")
print(f"Mean per-file Halstead effort: {mean_per_file_halstead_effort}")
print(f"Mean per-file MI: {mean_per_file_mi}")
