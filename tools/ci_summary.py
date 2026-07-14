import os
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


def main():
    repo_root = Path(__file__).resolve().parent.parent

    # 1. Parse JUnit XML files
    test_cases: list[dict[str, Any]] = []
    xml_files = list(repo_root.glob("junit.*.xml"))
    for xml_file in xml_files:
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            # In pytest, junit XML root is <testsuites> or <testsuite>
            if root.tag == "testsuite":
                testsuites = [root]
            else:
                testsuites = root.findall(".//testsuite")

            for testsuite in testsuites:
                for testcase in testsuite.findall("testcase"):
                    name = testcase.get("name", "")
                    classname = testcase.get("classname", "")
                    time_str = testcase.get("time", "0")
                    try:
                        duration = float(time_str)
                    except ValueError:
                        duration = 0.0
                    test_cases.append(
                        {
                            "name": name,
                            "classname": classname,
                            "duration": duration,
                            "shard": xml_file.name.replace("junit.", "").replace(".xml", ""),
                        }
                    )
        except Exception as e:
            print(f"Error parsing {xml_file.name}: {e}")

    # Sort test cases by duration descending
    test_cases.sort(key=lambda x: float(x["duration"]), reverse=True)
    slowest_25 = test_cases[:25]

    # 2. Read CI timings
    timings = {}
    timings_path = repo_root / ".ci_timings.json"
    if timings_path.exists():
        try:
            with open(timings_path) as f:
                timings = json.load(f)
        except Exception as e:
            print(f"Error reading .ci_timings.json: {e}")

    # 3. Generate summary markdown
    markdown = []
    markdown.append("## CI Run Job Summary\n")

    # Phase Timings Table
    markdown.append("### Phase Timings\n")
    markdown.append("| Phase | Duration (seconds) |")
    markdown.append("| --- | --- |")

    # Map raw key names to human-readable names
    phase_labels = {
        "deps_install_duration": "Dependency Setup / Installation",
        "collection_duration": "Test Collection",
        "test_execution_duration": "Test Execution",
        "coverage_upload_duration": "Coverage Upload",
    }

    for key, label in phase_labels.items():
        val = timings.get(key)
        if val is not None:
            markdown.append(f"| {label} | {val:.2f}s |")
        else:
            markdown.append(f"| {label} | N/A |")
    markdown.append("")

    # Slowest Tests Table
    markdown.append("### 25 Slowest Tests\n")
    if slowest_25:
        markdown.append("| # | Test Name | Class / Module | Shard | Duration |")
        markdown.append("| --- | --- | --- | --- | --- |")
        for i, tc in enumerate(slowest_25, 1):
            markdown.append(
                f"| {i} | {tc['name']} | `{tc['classname']}` | {tc['shard']} | {tc['duration']:.2f}s |"
            )
    else:
        markdown.append("No test duration data found.")
    markdown.append("")

    summary_content = "\n".join(markdown)

    # 4. Write to GITHUB_STEP_SUMMARY or print
    github_summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if github_summary_file:
        try:
            with open(github_summary_file, "a") as f:
                f.write(summary_content + "\n")
            print("Successfully wrote summary to GITHUB_STEP_SUMMARY.")
        except Exception as e:
            print(f"Failed to write to GITHUB_STEP_SUMMARY: {e}")
            print(summary_content)
    else:
        print("GITHUB_STEP_SUMMARY not set. Outputting summary to stdout:")
        print(summary_content)


if __name__ == "__main__":
    main()
