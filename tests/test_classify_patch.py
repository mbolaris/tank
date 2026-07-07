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


def test_classify_dict_literal_changed():
    changed_files = ["core/config/fish.py"]
    diff = """diff --git a/core/config/fish.py b/core/config/fish.py
--- a/core/config/fish.py
+++ b/core/config/fish.py
@@ -10,3 +10,3 @@
-    "threshold": 10.5,
+    "threshold": 20.0,
"""
    assert classify_diff(diff, changed_files) == "parameter-tuning"


def test_classify_dict_dynamic_changed():
    changed_files = ["core/config/fish.py"]
    diff = """diff --git a/core/config/fish.py b/core/config/fish.py
--- a/core/config/fish.py
+++ b/core/config/fish.py
@@ -10,3 +10,3 @@
-    "threshold": 10.5,
+    "threshold": SOME_DYNAMIC_FUNCTION(),
"""
    assert classify_diff(diff, changed_files) == "logic-change"


def test_classify_backend_behavior_change():
    changed_files = ["backend/world_manager.py"]
    diff = """diff --git a/backend/world_manager.py b/backend/world_manager.py
--- a/backend/world_manager.py
+++ b/backend/world_manager.py
@@ -5,4 +5,4 @@
-    def run(self):
-        self.tick()
+    def run(self):
+        self.tick_new()
"""
    assert classify_diff(diff, changed_files) == "logic-change"


def test_classify_test_only_change():
    changed_files = ["tests/test_some_feature.py"]
    diff = """diff --git a/tests/test_some_feature.py b/tests/test_some_feature.py
--- a/tests/test_some_feature.py
+++ b/tests/test_some_feature.py
@@ -1,3 +1,4 @@
 def test_foo():
-    assert True
+    assert 1 == 1
"""
    assert classify_diff(diff, changed_files) == "benchmark-or-meta"


def test_classify_new_benchmark_file():
    changed_files = ["benchmarks/tank/new_benchmark.py"]
    diff = """diff --git a/benchmarks/tank/new_benchmark.py b/benchmarks/tank/new_benchmark.py
new file mode 100644
--- /dev/null
+++ b/benchmarks/tank/new_benchmark.py
@@ -0,0 +1,5 @@
+def run(seed):
+    pass
"""
    assert classify_diff(diff, changed_files) == "benchmark-or-meta"
