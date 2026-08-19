"""Guards against README.md drifting out of sync with manifest.json's version.

manifest.json is the single source of truth for the integration's version.
This test doesn't rewrite README.md - it just fails CI loudly if someone
bumps the version in one place and forgets the other, the way the README's
footer sat on a stale "0.4.0" for a long time while manifest.json had long
since moved on.
"""
import json
import pathlib

MANIFEST_PATH = (
    pathlib.Path(__file__).resolve().parent.parent
    / "custom_components" / "oekofen" / "manifest.json"
)
README_PATH = pathlib.Path(__file__).resolve().parent.parent / "README.md"


def _manifest_version() -> str:
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        return json.load(f)["version"]


def test_readme_footer_matches_manifest_version():
    version = _manifest_version()
    readme = README_PATH.read_text(encoding="utf-8")
    assert f"**Version**: {version}" in readme, (
        f"README.md's footer doesn't mention manifest.json's version ({version}). "
        "Update the '**Version**: ...' line at the bottom of README.md."
    )


def test_readme_has_changelog_entry_for_manifest_version():
    version = _manifest_version()
    readme = README_PATH.read_text(encoding="utf-8")
    assert f"### Version {version}" in readme, (
        f"README.md has no '### Version {version}' changelog heading for "
        "manifest.json's current version. Add one (even a short one) under "
        "'## 📝 Changelog' before bumping manifest.json further."
    )
