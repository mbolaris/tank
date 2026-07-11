from unittest import mock

import pytest

from tools.check_locked_paths import DEFAULT_LOCKED_PATHS, get_changed_files, is_path_locked, main


def test_is_path_locked():
    locked = ["benchmarks/heldout", "tools/paper_eval.py", "some/other/dir/"]

    # Matching cases
    assert is_path_locked("benchmarks/heldout/survival_heldout_5k.py", locked) is True
    assert is_path_locked("benchmarks/heldout/nested/dir/file.py", locked) is True
    assert is_path_locked("benchmarks/heldout", locked) is True
    assert is_path_locked("tools/paper_eval.py", locked) is True
    assert is_path_locked("some/other/dir/file.txt", locked) is True

    # Non-matching cases
    assert is_path_locked("benchmarks/tank/survival_5k.py", locked) is False
    assert is_path_locked("tools/paper_eval_fake.py", locked) is False
    assert is_path_locked("some/other/dire/file.txt", locked) is False
    assert is_path_locked("main.py", locked) is False


def test_get_changed_files_with_base():
    with mock.patch("subprocess.run") as mock_run:
        mock_proc = mock.Mock()
        mock_proc.stdout = "file1.py\nfile2.py\n"
        mock_run.return_value = mock_proc

        files = get_changed_files(base="origin/master")

        mock_run.assert_called_once_with(
            ["git", "diff", "--name-only", "origin/master"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert files == ["file1.py", "file2.py"]


def test_get_changed_files_local():
    with mock.patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            mock.Mock(stdout="file1.py\n"),  # git diff --name-only
            mock.Mock(stdout="file2.py\n"),  # git diff --cached --name-only
            mock.Mock(stdout="?? untracked.py\n"),  # git status --porcelain
        ]

        files = get_changed_files(base=None)

        assert mock_run.call_count == 3
        assert files == ["file1.py", "file2.py", "untracked.py"]


def exit_side_effect(code=0):
    raise SystemExit(code)


def test_main_pass():
    with (
        mock.patch(
            "tools.check_locked_paths.get_changed_files", return_value=["main.py", "core/engine.py"]
        ),
        mock.patch("sys.exit", side_effect=exit_side_effect),
        mock.patch("sys.argv", ["check_locked_paths.py", "--locked", "benchmarks/heldout"]),
    ):

        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0


def test_main_fail():
    with (
        mock.patch(
            "tools.check_locked_paths.get_changed_files",
            return_value=["main.py", "benchmarks/heldout/survival.py"],
        ),
        mock.patch("sys.exit", side_effect=exit_side_effect),
        mock.patch("sys.argv", ["check_locked_paths.py", "--locked", "benchmarks/heldout"]),
    ):

        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 1


def test_main_uses_default_locked_paths():
    with (
        mock.patch(
            "tools.check_locked_paths.get_changed_files", return_value=["main.py", "core/engine.py"]
        ),
        mock.patch("sys.exit", side_effect=exit_side_effect),
        mock.patch("sys.argv", ["check_locked_paths.py"]),
    ):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0


def test_main_uses_default_locked_paths_fail():
    with (
        mock.patch(
            "tools.check_locked_paths.get_changed_files",
            return_value=["main.py", "core/poker/strategy/implementations/baseline.py"],
        ),
        mock.patch("sys.exit", side_effect=exit_side_effect),
        mock.patch("sys.argv", ["check_locked_paths.py"]),
    ):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 1


def test_default_locked_paths_contents():
    assert "benchmarks/heldout" in DEFAULT_LOCKED_PATHS
    assert "tools/check_locked_paths.py" in DEFAULT_LOCKED_PATHS
    assert "core/poker/strategy/implementations/baseline.py" in DEFAULT_LOCKED_PATHS
    assert "core/poker/strategy/implementations/standard.py" in DEFAULT_LOCKED_PATHS
    assert "core/poker/strategy/implementations/expert.py" in DEFAULT_LOCKED_PATHS
    assert "core/foraging/gym.py" in DEFAULT_LOCKED_PATHS
