from __future__ import annotations

"""Game configuration models and enums."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RPGMakerVersion(str, Enum):
    """Supported RPG Maker versions."""

    VX_ACE = "VX Ace"
    MV = "MV"
    MZ = "MZ"


class GameGenre(str, Enum):
    """Common game genres."""

    FANTASY = "fantasy"
    SCI_FI = "sci_fi"
    HORROR = "horror"
    MYSTERY = "mystery"
    ADVENTURE = "adventure"
    ROMANCE = "romance"
    OTHER = "other"


class ValidationLevel(str, Enum):
    """Levels of validation performed on export."""

    NONE = "none"
    BASIC = "basic"
    STRICT = "strict"


class StorySignificance(str, Enum):
    """Significance of the exported content to the overall story."""

    MAIN_STORY = "main_story"
    SIDE_QUEST = "side_quest"
    BACKGROUND = "background"


class ExportFormat(str, Enum):
    """Packaging formats for exported data."""

    DIRECTORY = "directory"
    ZIP = "zip"


class RPGProject(BaseModel):
    """Information about an RPG project."""

    name: str = Field(..., description="Project name")
    version: RPGMakerVersion = Field(RPGMakerVersion.MZ, description="RPG Maker version")
    genre: GameGenre = Field(GameGenre.FANTASY, description="Primary game genre")
    author: Optional[str] = Field(default=None, description="Project author")
    description: Optional[str] = Field(default=None, description="Project description")
    default_language: str = Field(default="en", description="Default language code")
    validation_level: ValidationLevel = Field(
        default=ValidationLevel.BASIC, description="Validation level for the project"
    )
    story_significance: StorySignificance = Field(
        default=StorySignificance.MAIN_STORY,
        description="Overall story significance",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )


class ExportConfiguration(BaseModel):
    """Settings for exporting a project to RPG Maker."""

    project: RPGProject = Field(..., description="Project being exported")
    target_version: RPGMakerVersion = Field(
        default=RPGMakerVersion.MZ, description="Target RPG Maker version"
    )
    include_assets: bool = Field(default=True, description="Include project assets")
    include_events: bool = Field(default=True, description="Include map events")
    package_format: ExportFormat = Field(
        default=ExportFormat.ZIP, description="Packaging format"
    )
    output_path: str = Field(default="./export", description="Export destination")
    validate_before_export: bool = Field(
        default=True, description="Run validation before exporting"
    )
    validation_level: ValidationLevel = Field(
        default=ValidationLevel.BASIC, description="Validation level for export"
    )


