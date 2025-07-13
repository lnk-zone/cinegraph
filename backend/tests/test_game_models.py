from datetime import datetime

import pytest

from game.models import (
    RPGMakerVersion,
    GameGenre,
    ValidationLevel,
    StorySignificance,
    ExportFormat,
    RPGProject,
    ExportConfiguration,
)


def test_rpg_project_defaults():
    project = RPGProject(name="Test", version=RPGMakerVersion.MZ, genre=GameGenre.FANTASY)
    assert project.validation_level == ValidationLevel.BASIC
    assert project.default_language == "en"
    assert project.story_significance == StorySignificance.MAIN_STORY
    assert isinstance(project.created_at, datetime)
    assert isinstance(project.updated_at, datetime)


def test_export_configuration_defaults():
    project = RPGProject(name="Demo", version=RPGMakerVersion.MZ, genre=GameGenre.FANTASY)
    config = ExportConfiguration(project=project)
    assert config.target_version == RPGMakerVersion.MZ
    assert config.include_assets is True
    assert config.include_events is True
    assert config.package_format == ExportFormat.ZIP
    assert config.output_path == "./export"
    assert config.validate_before_export is True
    assert config.validation_level == ValidationLevel.BASIC

