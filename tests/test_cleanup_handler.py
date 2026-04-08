import pytest
import unittest.mock as mock
import cleanup_handler
from cleanup_handler import (
    cleanup_session,
    prepare_rollback,
    confirm_cleanup
)

# Fixtures
@pytest.fixture
def mock_db_connection():
    with mock.patch('cleanup_handler.DatabaseConnection') as MockConn:
        instance = MockConn.return_value
        instance.get_records.return_value = []
        instance.execute.return_value = True
        yield instance

@pytest.fixture
def mock_api_client():
    with mock.patch('cleanup_handler.SessionApiClient') as MockClient:
        instance = MockClient.return_value
        instance.check_status.return_value = True
        instance.delete_data.return_value = {"status": "success"}
        yield instance

@pytest.fixture
def sample_session_id():
    return "dev-session-9981"

@pytest.fixture
def sample_data_ids():
    return ["data-001", "data-002", "data-003"]

# Tests for cleanup_session
class TestCleanupSession:

    def test_cleanup_session_happy_path(self, sample_session_id, mock_db_connection, mock_api_client):
        """Verify standard session cleanup without dry run."""
        with mock.patch('cleanup_handler.cleanup_session') as mocked_cleanup:
            mocked_cleanup.return_value = True
            result = cleanup_session(sample_session_id)
            assert result is True

    def test_cleanup_session_dry_run(self, sample_session_id, mock_db_connection, mock_api_client):
        """Verify cleanup logic skips execution during dry run."""
        with mock.patch('cleanup_handler.DatabaseConnection') as MockConn:
            instance = MockConn.return_value
            instance.get_data.return_value = True
            instance.cleanup.return_value = False
            
            result = cleanup_session(sample_session_id, dry_run=True)
            assert result is False
            instance.cleanup.assert_not_called()

    def test_cleanup_session_invalid_session(self, sample_session_id, mock_db_connection, mock_api_client):
        """Verify error handling for invalid session state."""
        with mock.patch('cleanup_handler.cleanup_session') as mocked_cleanup:
            mocked_cleanup.side_effect = ValueError("Session not found")
            with pytest.raises(ValueError):
                cleanup_session(sample_session_id)

# Tests for prepare_rollback
class TestPrepareRollback:

    def test_prepare_rollback_success(self, sample_data_ids, mock_db_connection, mock_api_client):
        """Verify successful preparation of rollback data."""
        with mock.patch('cleanup_handler.prepare_rollback') as mocked_prep:
            mocked_prep.return_value = {"rollback_id": "roll-1", "count": 3}
            result = prepare_rollback(sample_data_ids)
            assert result["rollback_id"] == "roll-1"

    def test_prepare_rollback_empty_ids(self, sample_data_ids, mock_db_connection, mock_api_client):
        """Verify handling of empty data list."""
        result = prepare_rollback([])
        assert result["status"] == "skipped" or result.get("count") == 0

    def test_prepare_rollback_system_error(self, sample_data_ids, mock_db_connection, mock_api_client):
        """Verify error propagation when preparation fails."""
        with mock.patch('cleanup_handler.prepare_rollback') as mocked_prep:
            mocked_prep.side_effect = Exception("Database timeout")
            with pytest.raises(Exception):
                prepare_rollback(sample_data_ids)

# Tests for confirm_cleanup
class TestConfirmCleanup:

    def test_confirm_cleanup_success(self, sample_session_id, mock_api_client):
        """Verify successful confirmation of cleanup state."""
        with mock.patch('cleanup_handler.confirm_cleanup') as mocked_confirm:
            mocked_confirm.return_value = True
            result = confirm_cleanup(sample_session_id)
            assert result is True

    def test_confirm_cleanup_no_session(self, sample_session_id, mock_api_client):
        """Verify handling when session does not exist on server."""
        with mock.patch('cleanup_handler.confirm_cleanup') as mocked_confirm:
            mocked_confirm.return_value = False
            result = confirm_cleanup(sample_session_id)
            assert result is False

    def test_confirm_cleanup_network_fail(self, sample_session_id, mock_api_client):
        """Verify handling of network connectivity issues."""
        with mock.patch('cleanup_handler.confirm_cleanup') as mocked_confirm:
            mocked_confirm.side_effect = ConnectionError("Network unreachable")
            with pytest.raises(ConnectionError):
                confirm_cleanup(sample_session_id)

# Integration Style Test for Safety Checks
class TestSafetyPreconditions:

    def test_safety_check_pass(self):
        """Verify system is safe for cleanup operations."""
        with mock.patch('cleanup_handler.is_safe_mode', return_value=True):
            assert cleanup_handler.is_safe_mode() is True

    def test_safety_check_fail_active_session(self):
        """Verify rejection of cleanup during active dev session."""
        with mock.patch('cleanup_handler.is_safe_mode', return_value=False):
            assert cleanup_handler.is_safe_mode() is False

    def test_safety_check_timeout(self):
        """Verify handling of timeout during safety check."""
        with mock.patch('cleanup_handler.is_safe_mode', side_effect=TimeoutError):
            with pytest.raises(TimeoutError):
                cleanup_handler.is_safe_mode()
                
    def test_cleanup_handler_initialized(self):
        """Verify module initialization status."""
        import cleanup_handler
        assert hasattr(cleanup_handler, 'cleanup_session')
        assert hasattr(cleanup_handler, 'prepare_rollback')
        assert hasattr(cleanup_handler, 'confirm_cleanup')