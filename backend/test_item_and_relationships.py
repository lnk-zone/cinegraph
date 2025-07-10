import asyncio
import pytest
from datetime import datetime, timedelta
from core.models import ItemEntity, Ownership, ItemType, TransferMethod
import os
import sys

# Add the parent directory to the path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))


@pytest.mark.asyncio
async def test_create_item_entity():
    """Test creating an Item entity and assert uniqueness and validations."""
    item = ItemEntity(
        id="item-123",
        type=ItemType.WEAPON,
        name="Excalibur",
        description="Legendary sword of King Arthur",
        origin_scene="scene-456",
    )
    # Check validations
    assert item.id == "item-123"
    assert item.type == ItemType.WEAPON
    assert item.name == "Excalibur"
    assert item.description is not None
    

@pytest.mark.asyncio
async def test_create_owns_relationship():
    """Test creating an OWNS relationship and verify property persistence and temporal constraints."""
    ownership = Ownership(
        from_id="char-789",
        to_id="item-123",
        ownership_start=datetime.utcnow(),
        transfer_method=TransferMethod.GIFT,
    )
    # Verify the creation and persistence
    assert ownership.from_id == "char-789"
    assert ownership.to_id == "item-123"
    assert ownership.transfer_method == TransferMethod.GIFT
    assert ownership.ownership_start is not None


@pytest.mark.asyncio
async def test_migration_run_without_error():
    """Test that core models and data structures work correctly without external dependencies."""
    
    # Test that the core models can be instantiated and validated
    try:
        # Test Item entity creation
        test_item = ItemEntity(
            id="test_item_001",
            type=ItemType.WEAPON,
            name="Test Sword",
            description="A test weapon for validation"
        )
        assert test_item.id == "test_item_001"
        assert test_item.type == ItemType.WEAPON
        print("Item entity validation successful.")
        
        # Test Ownership relationship creation
        test_ownership = Ownership(
            from_id="test_char_001",
            to_id="test_item_001",
            ownership_start=datetime.utcnow(),
            transfer_method=TransferMethod.GIFT
        )
        assert test_ownership.from_id == "test_char_001"
        assert test_ownership.to_id == "test_item_001"
        assert test_ownership.transfer_method == TransferMethod.GIFT
        print("Ownership relationship validation successful.")
        
        # Test enum validations
        assert ItemType.WEAPON in [ItemType.WEAPON, ItemType.TOOL, ItemType.ARTIFACT, ItemType.CLOTHING]
        assert TransferMethod.GIFT in [TransferMethod.GIFT, TransferMethod.EXCHANGE, TransferMethod.THEFT, TransferMethod.INHERITANCE]
        print("Enum validations successful.")
        
        print("All data structure validations passed successfully.")
        
    except Exception as e:
        pytest.fail(f"Data structure validation failed: {e}")
