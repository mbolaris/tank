from tools.classify_patch import classify_diff


def test_classify_docs():
    changed_files = ["docs/ROADMAP.md", "docs/archive/README.md"]
    diff = """diff --git a/docs/ROADMAP.md b/docs/ROADMAP.md
--- a/docs/ROADMAP.md
+++ b/docs/ROADMAP.md
@@ -1,3 +1,4 @@
 # Roadmap
+Adding some text.
"""
    assert classify_diff(diff, changed_files) == "docs"


def test_classify_benchmark_or_meta():
    changed_files = ["tests/test_energy.py", "tools/run_bench.py"]
    diff = """diff --git a/tools/run_bench.py b/tools/run_bench.py
--- a/tools/run_bench.py
+++ b/tools/run_bench.py
@@ -1,3 +1,3 @@
-print("old")
+print("new")
"""
    assert classify_diff(diff, changed_files) == "benchmark-or-meta"


def test_classify_new_algorithm():
    changed_files = ["core/algorithms/new_fancy_forager.py"]
    diff = """diff --git a/core/algorithms/new_fancy_forager.py b/core/algorithms/new_fancy_forager.py
new file mode 100644
index 0000000..e69de29
--- /dev/null
+++ b/core/algorithms/new_fancy_forager.py
@@ -0,0 +1,5 @@
+class FancyForager:
+    pass
"""
    assert classify_diff(diff, changed_files) == "new-algorithm"


def test_classify_parameter_tuning():
    changed_files = ["core/config/fish.py"]
    diff = """diff --git a/core/config/fish.py b/core/config/fish.py
--- a/core/config/fish.py
+++ b/core/config/fish.py
@@ -10,3 +10,3 @@
-MUTATION_RATE = 0.05
+MUTATION_RATE = 0.08
"""
    assert classify_diff(diff, changed_files) == "parameter-tuning"


def test_classify_parameter_tuning_in_dict():
    changed_files = ["core/algorithms/composable/definitions.py"]
    diff = """diff --git a/core/algorithms/composable/definitions.py b/core/algorithms/composable/definitions.py
--- a/core/algorithms/composable/definitions.py
+++ b/core/algorithms/composable/definitions.py
@@ -5,4 +5,4 @@
-    "hunting_stamina": 12.0,
+    "hunting_stamina": 15.5,
-    'active': False,
+    'active': True,
"""
    assert classify_diff(diff, changed_files) == "parameter-tuning"


def test_classify_refactor():
    changed_files = ["core/algorithms/composable/behavior.py"]
    diff = """diff --git a/core/algorithms/composable/behavior.py b/core/algorithms/composable/behavior.py
--- a/core/algorithms/composable/behavior.py
+++ b/core/algorithms/composable/behavior.py
@@ -1,3 +1,5 @@
+# This is a comment
 from typing import Any
-def execute(fish):
-    pass
+def execute(fish: Any) -> None:
+    # Updated comment
+    pass
"""
    assert classify_diff(diff, changed_files) == "refactor"


def test_classify_logic_change():
    changed_files = ["core/algorithms/composable/behavior.py"]
    diff = """diff --git a/core/algorithms/composable/behavior.py b/core/algorithms/composable/behavior.py
--- a/core/algorithms/composable/behavior.py
+++ b/core/algorithms/composable/behavior.py
@@ -5,4 +5,4 @@
-    if fish.energy > 10:
+    if fish.energy > 20:
-        fish.swim()
+        fish.swim_fast()
"""
    assert classify_diff(diff, changed_files) == "logic-change"
