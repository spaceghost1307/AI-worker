"""Tests for utility modules — OllamaClient."""

from unittest.mock import MagicMock

from src.utils.ollama_client import OllamaClient


class TestOllamaClientInit:
    """Test OllamaClient initialization."""

    def test_default_host(self) -> None:
        client = OllamaClient()
        assert client.host == "http://localhost:11434"

    def test_custom_host(self) -> None:
        client = OllamaClient(host="http://gpu-server:11434")
        assert client.host == "http://gpu-server:11434"


class TestOllamaClientChat:
    """Test OllamaClient.chat with mocked HTTP."""

    def test_chat_payload(self) -> None:
        client = OllamaClient()
        mock_response = MagicMock()
        mock_response.json.return_value = {"message": {"content": "Hello!"}}
        mock_response.raise_for_status = MagicMock()
        client._client = MagicMock()
        client._client.post.return_value = mock_response

        result = client.chat(
            model="qwen3:8b",
            messages=[{"role": "user", "content": "Hello"}],
            temperature=0.5,
        )
        assert result["message"]["content"] == "Hello!"

        call_args = client._client.post.call_args
        payload = call_args[1]["json"]
        assert payload["model"] == "qwen3:8b"
        assert payload["stream"] is False
        assert payload["options"]["temperature"] == 0.5

    def test_chat_with_json_format(self) -> None:
        client = OllamaClient()
        mock_response = MagicMock()
        mock_response.json.return_value = {"message": {"content": '{"key": "value"}'}}
        mock_response.raise_for_status = MagicMock()
        client._client = MagicMock()
        client._client.post.return_value = mock_response

        client.chat(
            model="qwen3:8b",
            messages=[{"role": "user", "content": "test"}],
            format="json",
        )
        call_args = client._client.post.call_args
        payload = call_args[1]["json"]
        assert payload["format"] == "json"

    def test_chat_without_format(self) -> None:
        client = OllamaClient()
        mock_response = MagicMock()
        mock_response.json.return_value = {"message": {"content": "text"}}
        mock_response.raise_for_status = MagicMock()
        client._client = MagicMock()
        client._client.post.return_value = mock_response

        client.chat(
            model="qwen3:8b",
            messages=[{"role": "user", "content": "test"}],
        )
        call_args = client._client.post.call_args
        payload = call_args[1]["json"]
        assert "format" not in payload


class TestOllamaClientVision:
    """Test OllamaClient.chat_with_images."""

    def test_chat_with_images_payload(self) -> None:
        import tempfile
        from pathlib import Path

        client = OllamaClient()
        mock_response = MagicMock()
        mock_response.json.return_value = {"message": {"content": '{"room": "kitchen"}'}}
        mock_response.raise_for_status = MagicMock()
        client._client = MagicMock()
        client._client.post.return_value = mock_response

        # Create a temporary file to simulate an image
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"\xff\xd8\xff\xe0" + b"\x00" * 100)  # Fake JPEG header
            temp_path = f.name

        try:
            result = client.chat_with_images(
                model="qwen2.5vl:7b",
                prompt="Analyze this photo",
                image_paths=[temp_path],
                format="json",
            )
            assert result["message"]["content"] == '{"room": "kitchen"}'

            call_args = client._client.post.call_args
            payload = call_args[1]["json"]
            assert payload["model"] == "qwen2.5vl:7b"
            assert len(payload["messages"][0]["images"]) == 1
        finally:
            Path(temp_path).unlink()


class TestOllamaClientListModels:
    """Test OllamaClient.list_models."""

    def test_list_models(self) -> None:
        client = OllamaClient()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "models": [
                {"name": "qwen3:8b", "size": 5200000000},
                {"name": "nomic-embed-text", "size": 500000000},
            ]
        }
        mock_response.raise_for_status = MagicMock()
        client._client = MagicMock()
        client._client.get.return_value = mock_response

        models = client.list_models()
        assert len(models) == 2
        assert models[0]["name"] == "qwen3:8b"

    def test_list_models_empty(self) -> None:
        client = OllamaClient()
        mock_response = MagicMock()
        mock_response.json.return_value = {"models": []}
        mock_response.raise_for_status = MagicMock()
        client._client = MagicMock()
        client._client.get.return_value = mock_response

        models = client.list_models()
        assert models == []


class TestOllamaClientModelManagement:
    """Test model management methods."""

    def test_pull_model(self) -> None:
        client = OllamaClient()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        client._client = MagicMock()
        client._client.post.return_value = mock_response

        # Should not raise
        client.pull_model("qwen3:14b")
        client._client.post.assert_called_once()
        call_args = client._client.post.call_args
        assert call_args[1]["json"]["name"] == "qwen3:14b"

    def test_is_model_loaded_true(self) -> None:
        client = OllamaClient()
        mock_response = MagicMock()
        mock_response.json.return_value = {"models": [{"name": "qwen3:8b"}]}
        mock_response.raise_for_status = MagicMock()
        client._client = MagicMock()
        client._client.get.return_value = mock_response

        assert client.is_model_loaded("qwen3:8b") is True

    def test_is_model_loaded_false(self) -> None:
        client = OllamaClient()
        mock_response = MagicMock()
        mock_response.json.return_value = {"models": [{"name": "qwen3:8b"}]}
        mock_response.raise_for_status = MagicMock()
        client._client = MagicMock()
        client._client.get.return_value = mock_response

        assert client.is_model_loaded("qwen3:14b") is False

    def test_is_model_loaded_empty(self) -> None:
        client = OllamaClient()
        mock_response = MagicMock()
        mock_response.json.return_value = {"models": []}
        mock_response.raise_for_status = MagicMock()
        client._client = MagicMock()
        client._client.get.return_value = mock_response

        assert client.is_model_loaded("any_model") is False
