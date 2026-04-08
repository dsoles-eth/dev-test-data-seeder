import pytest
import unittest.mock as mock
import container_manager

@pytest.fixture
def mock_docker_client():
    """Fixture to provide a mocked Docker client for testing."""
    client = mock.MagicMock()
    client.containers.run.return_value.id = "test_container_id_123"
    client.containers.run.side_effect = None
    return client

@pytest.fixture
def mock_docker_config():
    """Fixture to mock the docker module import within container_manager."""
    with mock.patch.object(container_manager, 'docker_client', autospec=True) as mock_client:
        mock_client.run.return_value.id = "test_container_id_123"
        mock_client.containers.get.return_value.status = "running"
        yield mock_client

class TestSeedDataFunction:
    """Tests for the seed_data public function in container_manager."""

    def test_seed_data_successful_creation(self, mock_docker_config):
        """Test happy path where container starts successfully."""
        image = "test-image:latest"
        name = "test-seed"
        ports = {"8080": 8080}
        env_vars = {"ENV": "dev"}

        result = container_manager.seed_data(image, name, ports, env_vars)

        assert result == "test_container_id_123"
        mock_docker_config.containers.run.assert_called_once()

    def test_seed_data_handles_image_not_found(self, mock_docker_config):
        """Test error handling when requested image is missing."""
        mock_docker_config.containers.run.side_effect = mock.DockerError("Image not found")

        with pytest.raises(container_manager.DockerError) as excinfo:
            container_manager.seed_data("nonexistent:image", "test-seed", {}, {})

        assert "not found" in str(excinfo.value)
        mock_docker_config.containers.run.assert_called_once()

    def test_seed_data_handles_connection_timeout(self, mock_docker_config):
        """Test error handling when docker daemon is unreachable."""
        mock_docker_config.containers.run.side_effect = mock.ConnectTimeout("Docker daemon timeout")

        with pytest.raises(container_manager.DockerError) as excinfo:
            container_manager.seed_data("valid:image", "test-seed", {}, {})

        assert "timeout" in str(excinfo.value).lower()
        mock_docker_config.containers.run.assert_called_once()


class TestTeardownFunction:
    """Tests for the teardown public function in container_manager."""

    def test_teardown_stops_container_success(self, mock_docker_config):
        """Test happy path where container stops successfully."""
        container_id = "existing_container_123"
        
        mock_docker_config.containers.get.return_value.id = container_id
        result = container_manager