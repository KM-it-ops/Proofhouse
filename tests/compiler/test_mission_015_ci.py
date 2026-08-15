from pathlib import Path


def test_ci_has_ubuntu_wheel_install_job() -> None:
    text = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "wheel-install:" in text
    assert "ubuntu-latest" in text
    assert "python -m build" in text
    assert "pip install" in text
    assert "promptrig-compiler doctor --json" in text
    assert "external_consumer_closed_loop.py" in text
    assert "install -e" in text  # existing editable matrix stays
