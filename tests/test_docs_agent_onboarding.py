"""Tests to ensure documentation consistency and prevent stale onboarding instructions."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readme_references_smoke_and_fast_gates():
    readme_path = ROOT / "README.md"
    assert readme_path.exists(), "README.md does not exist"
    content = readme_path.read_text(encoding="utf-8")
    assert "tools/smoke_gate.py" in content, "README.md must reference tools/smoke_gate.py"
    assert "tools/fast_gate.py" in content, "README.md must reference tools/fast_gate.py"


def test_agents_references_agent_quickstart():
    agents_path = ROOT / "AGENTS.md"
    assert agents_path.exists(), "AGENTS.md does not exist"
    content = agents_path.read_text(encoding="utf-8")
    assert (
        "docs/AGENT_QUICKSTART.md" in content
    ), "AGENTS.md must reference docs/AGENT_QUICKSTART.md"


def test_agent_quickstart_exists():
    quickstart_path = ROOT / "docs" / "AGENT_QUICKSTART.md"
    assert quickstart_path.exists(), "docs/AGENT_QUICKSTART.md does not exist"


def test_evo_contributing_does_not_reference_stale_benchmarks():
    contributing_path = ROOT / "docs" / "EVO_CONTRIBUTING.md"
    assert contributing_path.exists(), "docs/EVO_CONTRIBUTING.md does not exist"
    content = contributing_path.read_text(encoding="utf-8")

    stale_benchmarks = ["survival_30k.py", "reproduction_30k.py", "diversity_30k.py"]
    for stale in stale_benchmarks:
        assert (
            stale not in content
        ), f"docs/EVO_CONTRIBUTING.md should not reference stale benchmark '{stale}'"


def test_live_benchmark_paths_in_docs_exist():
    # Gather all markdown files in the repository (excluding ROADMAP.md and docs/ROADMAP.md)
    md_files = list(ROOT.glob("*.md")) + list((ROOT / "docs").glob("*.md"))

    # Exclude ROADMAP.md because planned benchmarks belong there
    md_files = [f for f in md_files if f.name != "ROADMAP.md"]

    benchmark_pattern = re.compile(r"\bbenchmarks/[a-zA-Z0-9_/-]+\.py\b")

    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")
        matches = benchmark_pattern.findall(content)
        for match in matches:
            bench_path = ROOT / match
            assert (
                bench_path.exists()
            ), f"File {md_file.relative_to(ROOT)} references nonexistent benchmark path: {match}"


def test_ci_job_names_in_readme_match_workflow_files():
    readme_path = ROOT / "README.md"
    readme_content = readme_path.read_text(encoding="utf-8")

    # Extract actual job names from CI and Bench workflow files
    workflow_paths = [
        ROOT / ".github" / "workflows" / "ci.yml",
        ROOT / ".github" / "workflows" / "bench.yml",
    ]

    actual_jobs = set()
    job_pattern = re.compile(r"^(?:  |\t)([a-zA-Z0-9_-]+):")

    for wf_path in workflow_paths:
        assert wf_path.exists(), f"Workflow file {wf_path} does not exist"
        in_jobs = False
        for line in wf_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("jobs:"):
                in_jobs = True
                continue
            if in_jobs:
                if line.strip() == "":
                    continue
                if not line.startswith(" ") and not line.startswith("\t"):
                    in_jobs = False
                    continue
                match = job_pattern.match(line)
                if match:
                    actual_jobs.add(match.group(1))

    # Assert that actual jobs are found
    assert actual_jobs, "No jobs were parsed from the workflow files"

    # Extract the job names mentioned in the CI section of README.md
    # Look for "CI currently runs" sentence
    ci_match = re.search(r"CI currently runs ([^.]+)", readme_content)
    assert ci_match, "Could not find 'CI currently runs' sentence in README.md"

    ci_sentence = ci_match.group(1)
    # Find all words that look like job names (e.g. containing hyphen and ending with gate, ci, champions, full)
    job_mentions = re.findall(
        r"\b[a-zA-Z0-9_-]+-gate\b|\b[a-zA-Z0-9_-]+-ci\b|\bverify-[a-zA-Z0-9_-]+\b|\bnightly-[a-zA-Z0-9_-]+\b",
        ci_sentence,
    )

    assert job_mentions, f"No job mentions parsed from README CI sentence: '{ci_sentence}'"

    for job in job_mentions:
        assert (
            job in actual_jobs
        ), f"README.md references stale/nonexistent CI job '{job}' (actual jobs: {actual_jobs})"
