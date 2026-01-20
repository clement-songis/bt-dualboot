import os
import shutil
from pathlib import Path

from pytest import TempPathFactory, fixture

from bt_dualboot.windows_registry import WindowsRegistry

wp = WindowsRegistry.with_prefix


@fixture
def windows_registry_samples_dir():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_samples")


@fixture
def tmpdir(tmp_path_factory: TempPathFactory):
    return tmp_path_factory.mktemp("windows_registry")


@fixture
def sample_reg_file_path(windows_registry_samples_dir: str):
    """
    Windows/System32/config/SYSTEM snapshot from fresh-installed Windows 10
    """
    return os.path.join(windows_registry_samples_dir, "SYSTEM_BLANK")


@fixture
def registry_file_path(sample_reg_file_path: str, tmpdir: Path):
    """
    Making working copy of SYSTEM Hive file
    """
    test_reg = str(tmpdir / "SYSTEM")
    shutil.copy(sample_reg_file_path, test_reg)
    os.chmod(test_reg, 0o600)
    yield test_reg
    os.unlink(test_reg)


@fixture
def windows_registry(registry_file_path: str):
    return WindowsRegistry(registry_file_path)
