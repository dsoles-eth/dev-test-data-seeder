import pytest
import json
from unittest.mock import patch, MagicMock, call
import integrity_checker

# Fixtures for test data
@pytest.fixture
def valid_seed_record():
    """Returns a valid data record meeting schema and business rules."""
    return {
        "id": "record-001",
        "created_at": "2023-10-27T10:00:00Z",
        "status": "active",
        "amount": 150.50,
        "category": "electronics",
        "related_id": "record-002"
    }

@pytest.fixture
def invalid_record_missing_field():
    """Returns a record missing a required field."""
    return {
        "id": "record-003",
        "status": "active",
        "amount": 150.50
    }

@pytest.fixture
def invalid_record_type_mismatch():
    """Returns a record with an incorrect data type."""
    return {
        "id": "record-004",
        "created_at": "2023-10-27T10:00:00Z",
        "status": "active",
        "amount": "not_a_number",
        "category": "electronics",
        "related_id": "record-002"
    }

@pytest.fixture
def business_rule_record_valid():
    """Record valid for business rules (status active implies non-zero amount)."""
    return {
        "id": "record-005",
        "created_at": "2023-10-27T10:00:00Z",
        "status": "active",
        "amount": 100.00
    }

@pytest.fixture
def business_rule_record_invalid():
    """Record violates business rules (status closed implies zero amount)."""
    return {
        "id": "record-006",
        "created_at": "2023-10-27T10:00:00Z",
        "status": "closed",
        "amount": 50.00
    }

@pytest.fixture
def mock_api_client():
    """Mocks the external schema API client."""
    mock_client = MagicMock()
    mock_client.fetch_schema.return_value = {
        "required_fields": ["id", "created_at", "status", "amount", "category", "related_id"]
    }
    return mock_client

class TestIntegrityCheckerSchema:
    def test_validate_schema_success(self, valid_seed_record):
        """Test happy path where data matches expected schema constraints."""
        result = integrity_checker.validate_schema(valid_seed_record)
        assert result["is_valid"] is True
        assert "errors" not in result

    def test_validate_schema_missing_field(self, invalid_record_missing_field):
        """Test error case where a required schema field is missing."""
        result = integrity_checker.validate_schema(invalid_record_missing_field)
        assert result["is_valid"] is False
        assert "errors" in result
        assert "created_at"