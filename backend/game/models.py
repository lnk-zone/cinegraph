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


class VariableDataType(str, Enum):
    """Supported data types for RPG variables."""

    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    BOOLEAN = "boolean"


class VariableScope(str, Enum):
    """Scope levels for RPG variables."""

    GAME = "game"
    MAP = "map"
    EVENT = "event"


class SwitchScope(str, Enum):
    """Scope levels for RPG switches."""

    GLOBAL = "global"
    LOCAL = "local"


class RPGVariable(BaseModel):
    """Represents a variable in an RPG project."""

    name: str = Field(..., description="Variable name")
    value: Optional[str | int | float | bool] = Field(
        default=None, description="Initial value of the variable"
    )
    data_type: VariableDataType = Field(
        default=VariableDataType.INTEGER, description="Data type of the variable"
    )
    scope: VariableScope = Field(
        default=VariableScope.GAME, description="Scope of the variable"
    )
    description: Optional[str] = Field(default=None, description="Variable description")


class RPGSwitch(BaseModel):
    """Represents a boolean switch in an RPG project."""

    name: str = Field(..., description="Switch name")
    is_on: bool = Field(default=False, description="Initial state of the switch")
    scope: SwitchScope = Field(
        default=SwitchScope.GLOBAL, description="Scope of the switch"
    )
    description: Optional[str] = Field(default=None, description="Switch description")


class RPGCharacterType(str, Enum):
    """Types of RPG characters."""

    HERO = "hero"
    VILLAIN = "villain"
    COMPANION = "companion"
    NPC = "npc"
    OTHER = "other"


class CharacterStats(BaseModel):
    """Basic RPG-style character statistics."""

    hp: int = Field(default=100, description="Hit points")
    mp: int = Field(default=0, description="Magic points")
    strength: int = Field(default=10, description="Physical power")
    agility: int = Field(default=10, description="Dexterity and speed")
    intelligence: int = Field(default=10, description="Mental acuity")
    charisma: int = Field(default=10, description="Social aptitude")


class RPGCharacter(BaseModel):
    """Represents a playable or non-playable character."""

    name: str = Field(..., description="Character name")
    type: RPGCharacterType = Field(default=RPGCharacterType.NPC, description="Character type")
    level: int = Field(default=1, description="Character level")
    stats: CharacterStats = Field(default_factory=CharacterStats, description="Character statistics")
    knowledge_state: list[dict] = Field(default_factory=list, description="Known facts or memories")
    description: Optional[str] = Field(default=None, description="Character description")


class LocationType(str, Enum):
    """Types of locations within an RPG world."""

    TOWN = "town"
    DUNGEON = "dungeon"
    BUILDING = "building"
    WILDERNESS = "wilderness"
    OTHER = "other"


class ConnectionType(str, Enum):
    """Ways locations can be connected."""

    PATH = "path"
    DOOR = "door"
    PORTAL = "portal"
    OTHER = "other"


class Direction(str, Enum):
    """Cardinal or relative directions for connections."""

    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"
    UP = "up"
    DOWN = "down"


class RPGLocation(BaseModel):
    """Represents a location within the story world."""

    name: str = Field(..., description="Location name")
    type: LocationType = Field(default=LocationType.OTHER, description="Location type")
    description: Optional[str] = Field(default=None, description="Location description")
    events: list[str] = Field(default_factory=list, description="Story events that occur here")


class LocationConnection(BaseModel):
    """Connection from one location to another."""

    from_location: str = Field(..., description="Starting location name")
    to_location: str = Field(..., description="Destination location name")
    type: ConnectionType = Field(default=ConnectionType.PATH, description="Connection type")
    direction: Optional[Direction] = Field(default=None, description="Direction from start to destination")


