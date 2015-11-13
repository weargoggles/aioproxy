from unittest import TestCase, mock

import asyncio

from aioproxy import ReverseProxyRouter


class TestReverseProxyRouter(TestCase):
    def test_resolver_called_by_router(self):
        mock_resolver = mock.MagicMock()
        mock_request = mock.MagicMock()

        # noinspection PyTypeChecker
        router = ReverseProxyRouter(mock_resolver)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(router.resolve(mock_request))

        self.assertTrue(mock_resolver.find_destination.called_with(mock_request))
