import pytest

from backend.infrastructure.messaging.message_broker import BrokerError
from backend.infrastructure.pipeline.consumer import main, process_message


class TestMain:
    def test_delegates_each_message_to_service(self, mocker):
        mock_broker = mocker.MagicMock()
        mock_broker.consume.return_value = iter([{"text": "great"}, {"text": "ok"}])
        mock_service = mocker.MagicMock()

        main(broker=mock_broker, service=mock_service)

        assert mock_service.execute.call_count == 2
        mock_broker.close.assert_called_once()

    def test_closes_broker_on_keyboard_interrupt(self, mocker):
        mock_broker = mocker.MagicMock()
        mock_broker.consume.side_effect = KeyboardInterrupt
        mock_service = mocker.MagicMock()

        main(broker=mock_broker, service=mock_service)

        mock_broker.close.assert_called_once()

    def test_closes_broker_on_broker_error(self, mocker):
        mock_broker = mocker.MagicMock()
        mock_broker.consume.side_effect = BrokerError("dropped")
        mock_service = mocker.MagicMock()

        main(broker=mock_broker, service=mock_service)

        mock_broker.close.assert_called_once()

    def test_closes_broker_on_unexpected_error(self, mocker):
        mock_broker = mocker.MagicMock()
        mock_broker.consume.side_effect = RuntimeError("crash")
        mock_service = mocker.MagicMock()

        main(broker=mock_broker, service=mock_service)

        mock_broker.close.assert_called_once()


class TestProcessMessage:
    def test_delegates_to_service(self, mocker):
        mock_service = mocker.MagicMock()
        message = {"text": "hello"}

        process_message(message, mock_service)

        mock_service.execute.assert_called_once_with(message)
