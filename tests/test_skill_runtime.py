from pathlib import Path

import pytest

from hermes_cli.skill_runtime import (
    SkillError,
    SkillRegistry,
    SkillSecurityError,
    compose_instructions,
    discover_skills,
    load_skill,
    manifest,
)


def write_skill(root: Path, name: str, *, description: str = "Android agent skill", triggers: str = "android, agent") -> Path:
    directory = root / name
    directory.mkdir(parents=True)
    path = directory / "SKILL.md"
    path.write_text(
        "---\n"
        f"name: {name}\n"
        "version: 1.2.3\n"
        f"description: {description}\n"
        f"triggers: {triggers}\n"
        "---\n\n# Instructions\nUse the narrow tool boundary.\n",
        encoding="utf-8",
    )
    return path


def test_discovery_is_deterministic_and_manifest_hides_instructions(tmp_path: Path) -> None:
    root = tmp_path / "skills"
    write_skill(root, "zeta", triggers="vision")
    write_skill(root, "alpha", triggers="android")

    skills = discover_skills(root)
    assert [skill.name for skill in skills] == ["alpha", "zeta"]
    assert manifest(skills)[0]["name"] == "alpha"
    assert "instructions" not in manifest(skills)[0]


def test_selection_prefers_trigger_match(tmp_path: Path) -> None:
    root = tmp_path / "skills"
    write_skill(root, "android-agent", triggers="android, device")
    write_skill(root, "vision", triggers="image, vision")

    registry = SkillRegistry.from_directory(root)
    matches = registry.select("configure android device permissions")
    assert matches
    assert matches[0].skill.name == "android-agent"


def test_composition_contains_provenance_digest(tmp_path: Path) -> None:
    root = tmp_path / "skills"
    write_skill(root, "alpha")
    skill = load_skill(root / "alpha" / "SKILL.md", skill_root=root)
    selected = SkillRegistry((skill,)).select("android agent")
    text = compose_instructions(selected)
    assert "## Skill: alpha" in text
    assert f"skill-sha256: {skill.digest}" in text


def test_rejects_unsafe_name(tmp_path: Path) -> None:
    root = tmp_path / "skills"
    directory = root / "Bad Name"
    directory.mkdir(parents=True)
    path = directory / "SKILL.md"
    path.write_text(
        "---\nname: Bad Name\ndescription: invalid\n---\n\nInstructions\n",
        encoding="utf-8",
    )
    with pytest.raises(SkillError):
        load_skill(path, skill_root=root)


def test_rejects_skill_path_escape(tmp_path: Path) -> None:
    root = tmp_path / "skills"
    outside = tmp_path / "SKILL.md"
    outside.write_text("---\nname: escape\ndescription: bad\n---\n", encoding="utf-8")
    with pytest.raises(SkillSecurityError):
        load_skill(outside, skill_root=root)
