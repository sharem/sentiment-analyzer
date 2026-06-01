from backend.infrastructure.auth.redis_session_store import RedisSessionStore


class TestRedisSessionStore:
    def test_create_returns_a_url_safe_token(self, mocker):
        client = mocker.MagicMock()
        store = RedisSessionStore(client, ttl_seconds=3600)

        session_id = store.create(user_id=7)

        assert len(session_id) >= 32
        assert " " not in session_id

    def test_create_setex_uses_session_prefix_and_ttl(self, mocker):
        client = mocker.MagicMock()
        store = RedisSessionStore(client, ttl_seconds=3600)

        session_id = store.create(user_id=7)

        client.setex.assert_called_once_with(
            f"session:{session_id}", 3600, "7"
        )

    def test_get_returns_user_id_when_present(self, mocker):
        client = mocker.MagicMock()
        client.get.return_value = "42"
        store = RedisSessionStore(client, ttl_seconds=3600)

        assert store.get("abc") == 42
        client.get.assert_called_once_with("session:abc")

    def test_get_decodes_bytes_payload(self, mocker):
        client = mocker.MagicMock()
        client.get.return_value = b"42"
        store = RedisSessionStore(client, ttl_seconds=3600)

        assert store.get("abc") == 42

    def test_get_returns_none_when_missing(self, mocker):
        client = mocker.MagicMock()
        client.get.return_value = None
        store = RedisSessionStore(client, ttl_seconds=3600)

        assert store.get("abc") is None

    def test_get_returns_none_when_payload_is_not_an_int(self, mocker):
        client = mocker.MagicMock()
        client.get.return_value = "garbage"
        store = RedisSessionStore(client, ttl_seconds=3600)

        assert store.get("abc") is None

    def test_delete_removes_prefixed_key(self, mocker):
        client = mocker.MagicMock()
        store = RedisSessionStore(client, ttl_seconds=3600)

        store.delete("abc")

        client.delete.assert_called_once_with("session:abc")
