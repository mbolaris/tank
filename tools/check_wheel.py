#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile


def run_cmd(cmd, cwd=None, env=None):
    print(f"Running: {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Command failed with exit code {res.returncode}")
        print("STDOUT:")
        print(res.stdout)
        print("STDERR:")
        print(res.stderr)
        sys.exit(res.returncode)
    return res.stdout


def main():
    workspace = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    print(f"Workspace root: {workspace}")

    # 1. Create a temp directory
    temp_dir = tempfile.mkdtemp(prefix="tankworld_wheel_check_")
    try:
        # 2. Build the wheel
        print("Building wheel...")
        import importlib.util

        if importlib.util.find_spec("pip") is None:
            print("pip not found in current environment. Bootstrapping with ensurepip...")
            subprocess.run([sys.executable, "-m", "ensurepip", "--upgrade"], capture_output=True)
        # We use pip wheel to build without installing build package
        run_cmd(
            [sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "-w", temp_dir], cwd=workspace
        )

        # 3. Locate the built wheel
        wheels = [f for f in os.listdir(temp_dir) if f.endswith(".whl")]
        if not wheels:
            print("Error: No wheel file found in output directory.")
            sys.exit(1)
        wheel_path = os.path.join(temp_dir, wheels[0])
        print(f"Built wheel: {wheel_path}")

        # 4. Inspect wheel contents using zipfile
        print("Checking wheel contents...")
        with zipfile.ZipFile(wheel_path, "r") as zf:
            file_list = zf.namelist()

        # Core checks
        required_paths = [
            "core/algorithms/registry.py",
            "core/genetics/genome.py",
            "core/entities/fish.py",
            "core/simulation/engine.py",
            "backend/routers/worlds/__init__.py",
        ]

        missing_paths = []
        for path in required_paths:
            if path not in file_list:
                missing_paths.append(path)

        if missing_paths:
            print("Error: Wheel is missing the following expected files:")
            for p in missing_paths:
                print(f"  - {p}")
            sys.exit(1)

        # Exclusion checks: shouldn't have tests, benchmarks, etc.
        disallowed_prefixes = ["tests/", "benchmarks/", "tools/", "scripts/", "frontend/"]
        found_disallowed = []
        for name in file_list:
            for prefix in disallowed_prefixes:
                if name.startswith(prefix):
                    found_disallowed.append(name)

        if found_disallowed:
            print("Error: Wheel contains files that should not be packaged:")
            for p in found_disallowed[:10]:
                print(f"  - {p}")
            if len(found_disallowed) > 10:
                print(f"  ... and {len(found_disallowed) - 10} more")
            sys.exit(1)

        print("Wheel structure checks passed!")

        # 5. Create a clean virtual environment and install/import
        venv_dir = os.path.join(temp_dir, "venv")
        print(f"Creating test venv at {venv_dir}...")
        run_cmd([sys.executable, "-m", "venv", venv_dir])

        # Determine path to python/pip in the new venv
        if os.name == "nt":
            venv_python = os.path.join(venv_dir, "Scripts", "python.exe")
            venv_pip = os.path.join(venv_dir, "Scripts", "pip.exe")
        else:
            venv_python = os.path.join(venv_dir, "bin", "python")
            venv_pip = os.path.join(venv_dir, "bin", "pip")

        # Bootstrapping pip inside test venv if pip is missing (e.g. in uv envs)
        if not os.path.exists(venv_pip):
            print("pip not found in test venv. Bootstrapping via ensurepip...")
            run_cmd([venv_python, "-m", "ensurepip", "--upgrade"])

        print("Installing wheel in venv...")
        run_cmd([venv_pip, "install", wheel_path])

        # 6. Test imports
        print("Testing imports inside the clean venv...")
        import_test_script = (
            "import core.algorithms.registry\n"
            "import core.genetics.genome\n"
            "import core.entities.fish\n"
            "import core.simulation.engine\n"
            "import backend.routers.worlds\n"
            "print('All imports successful!')\n"
        )
        test_script_path = os.path.join(temp_dir, "test_imports.py")
        with open(test_script_path, "w") as f:
            f.write(import_test_script)

        stdout = run_cmd([venv_python, test_script_path])
        print(stdout.strip())
        print("Clean-install smoke test passed successfully!")

    finally:
        print("Cleaning up temporary directory...")
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
