"""Tests to ensure documentation consistency and prevent stale onboarding instructions."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_AGENT_DOCS = [
    ROOT / "README.md",
    ROOT / "docs" / "EVO_CONTRIBUTING.md",
    ROOT / "docs" / "AGENT_QUICKSTART.md",
    ROOT / "AGENTS.md",
    ROOT / "docs" / "AGENT_FIELD_GUIDE.md",
]


def _workflow_job_names() -> set[str]:
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

    assert actual_jobs, "No jobs were parsed from the workflow files"
    return actual_jobs


def _markdown_section(content: str, heading: str) -> str:
    marker = f"## {heading}"
    start = content.find(marker)
    assert start != -1, f"Could not find section heading: {marker}"

    next_heading = content.find("\n## ", start + len(marker))
    if next_heading == -1:
        return content[start:]
    return content[start:next_heading]


def test_readme_references_smoke_and_pre_pr_gates():
    readme_path = ROOT / "README.md"
    assert readme_path.exists(), "README.md does not exist"
    content = readme_path.read_text(encoding="utf-8")
    assert "tools/smoke_gate.py" in content, "README.md must reference tools/smoke_gate.py"
    assert "tools/agent_gate.py" in content, "README.md must reference tools/agent_gate.py"
    assert "tools/pre_pr_gate.py" in content, "README.md must reference tools/pre_pr_gate.py"


def test_agents_references_agent_quickstart():
    agents_path = ROOT / "AGENTS.md"
    assert agents_path.exists(), "AGENTS.md does not exist"
    content = agents_path.read_text(encoding="utf-8")
    assert (
        "docs/AGENT_QUICKSTART.md" in content
    ), "AGENTS.md must reference docs/AGENT_QUICKSTART.md"
    assert "tools/agent_gate.py" in content, "AGENTS.md must reference tools/agent_gate.py"


def test_vague_prompt_guidance_starts_with_smoke_gate_not_pre_pr_gate():
    agents_path = ROOT / "AGENTS.md"
    content = agents_path.read_text(encoding="utf-8")
    section = _markdown_section(content, "If you were given a vague prompt")

    gate_commands = re.findall(r"python tools/(?:smoke|agent|pre_pr|full)_gate\.py", section)

    assert gate_commands, "AGENTS.md vague-prompt section must name a validation gate"
    assert (
        gate_commands[0] == "python tools/smoke_gate.py"
    ), "Vague-prompt guidance must make smoke_gate.py the first validation command"


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

    actual_jobs = _workflow_job_names()

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

    all_readme_job_mentions = set(
        re.findall(
            r"(?<!-)\b[a-zA-Z0-9_-]+-gate\b|(?<!-)\b[a-zA-Z0-9_-]+-ci\b|(?<!-)\bverify-[a-zA-Z0-9_-]+\b|(?<!-)\bnightly-[a-zA-Z0-9_-]+\b",
            readme_content,
        )
    )
    stale_mentions = sorted(all_readme_job_mentions - actual_jobs)
    assert not stale_mentions, f"README.md mentions stale/nonexistent CI jobs: {stale_mentions}"


def test_agent_quickstart_does_not_mention_update_champion():
    quickstart_path = ROOT / "docs" / "AGENT_QUICKSTART.md"
    content = quickstart_path.read_text(encoding="utf-8")
    assert "--update-champion" not in content, (
        "docs/AGENT_QUICKSTART.md must not instruct agents to use --update-champion. "
        "Updating champion files is restricted to authorized agents/maintainers."
    )
    assert (
        "verify_all_champions.py" not in content
    ), "docs/AGENT_QUICKSTART.md must not instruct agents to use verify_all_champions.py."
    assert (
        "Do NOT edit the `champions/**/*.json` files directly" in content
        or "do not edit the champions/**/*.json files" in content
    )


def test_public_agent_docs_restrict_champion_update_guidance():
    """Public agent docs may compare against champions, but not casually update them."""
    forbidden_unconditional_patterns = [
        r"if\s+better,\s*update\s+the\s+champion\s+file",
        r"if\s+you\s+have\s+an\s+improvement,\s*update\s+the\s+champion\s+file",
        r"git\s+add\s+champions/[^\n]+\.json",
        r"manually\s+overwrite\s+the\s+affected\s+champion\s+files",
    ]
    restricted_words = ("maintainer", "authorized", "must not", "do not", "unless explicitly")

    for doc_path in PUBLIC_AGENT_DOCS:
        assert doc_path.exists(), f"{doc_path.relative_to(ROOT)} does not exist"
        content = doc_path.read_text(encoding="utf-8")
        lower = content.lower()

        for pattern in forbidden_unconditional_patterns:
            assert not re.search(pattern, lower), (
                f"{doc_path.relative_to(ROOT)} contains unconditional champion-update guidance "
                f"matching {pattern!r}. Agents should report evidence, not update champions."
            )

        for match in re.finditer(r"--update-champion", lower):
            start = max(0, match.start() - 240)
            end = min(len(lower), match.end() + 240)
            context = lower[start:end]
            assert any(word in context for word in restricted_words), (
                f"{doc_path.relative_to(ROOT)} mentions --update-champion without clear "
                "maintainer/task authorization language nearby."
            )
