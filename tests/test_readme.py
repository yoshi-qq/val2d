"""Keep the README inventory synchronized with the game content."""

from tools.update_readme import END, README, START, content


def test_readme_content_is_current() -> None:
    actual = README.read_text(encoding="utf-8").split(START)[1].split(END)[0]
    assert actual == f"\n\n{content()}\n\n", "Refresh the README with python -m tools.update_readme."
