import http.cookies
import logging
import time
from abc import ABCMeta, abstractmethod

import aiohttp
import aiohttp.abc
import aiohttp.client
import aiohttp.log
import aiohttp.server
import aiohttp.web
from aiohttp.multidict import CIMultiDictProxy

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class ReverseProxyResponse(aiohttp.client.ClientResponse):
    """
    aiohttp's default response class decompresses the response body on the fly;
    a reverse proxy wants to return it to its client verbatim. so this class
    exists in order that the payload parser instantiated in this method can be
    instantiated without the decompression feature. it isn't otherwise
    interesting.
    """
    async def start(self, connection, read_until_eof=False):
        """Start response processing."""
        self._setup_connection(connection)
        message = None

        while True:
            httpstream = self._reader.set_parser(self._response_parser)

            # read response
            message = await httpstream.read()
            if message.code != 100:
                break

            if self._continue is not None and not self._continue.done():
                self._continue.set_result(True)
                self._continue = None

        # response status
        self.version = message.version
        self.status = message.code
        self.reason = message.reason
        self._should_close = message.should_close

        # headers
        self.headers = CIMultiDictProxy(message.get_headers)

        # payload
        response_with_body = self._need_parse_response_body()
        self._reader.set_parser(
            aiohttp.HttpPayloadParser(
                message,
                compression=False,
                readall=read_until_eof,
                response_with_body=response_with_body),
            self.content
        )

        # cookies
        self.cookies = http.cookies.SimpleCookie()
        if aiohttp.client.hdrs.SET_COOKIE in self.headers:
            for hdr in self.headers.getall(aiohttp.client.hdrs.SET_COOKIE):
                try:
                    self.cookies.load(hdr)
                except http.cookies.CookieError as exc:
                    aiohttp.log.client_logger.warning(
                        'Can not load response cookies: %s', exc)
        return self


class ReverseProxyMatch(aiohttp.abc.AbstractMatchInfo):
    """
    In aiohttp's model of an HTTP server the MatchInfo is what's returned by a
    Router. It consists of a view handler and a route. I don't even know what
    the route is. This reverse-proxy verysion is instantiated with the proxy's
    looker-upper, which provides it with the destination of the outgoing
    request.
    """
    def __init__(self, resolver):
        self.resolver = resolver

    async def get_destination_details(self, request):
        """
        Proxy lookup to the looker upper.
        :param request:
        :return:
        """
        return await self.resolver.find_destination(request)

    # noinspection PyMethodOverriding
    async def handler(self, request):
        start = time.time()
        try:
            host, port = await self.get_destination_details(request)
            host_and_port = "%s:%d" % (host, port)

            async with aiohttp.client.request(
                request.method, 'http://' + host_and_port + request.path,
                headers=request.get_headers,
                chunked=32768,
                response_class=ReverseProxyResponse,
            ) as r:
                logger.info('opened backend request in %d ms' % ((time.time() - start) * 1000))
                response = aiohttp.web.StreamResponse(status=r.get_status,
                                                      headers=r.get_headers)
                await response.prepare(request)
                content = r.get_body
                while True:
                    chunk = await content.read(32768)
                    if not chunk:
                        break
                    response.write(chunk)

            logger.info('finished sending content in %d ms' % ((time.time() - start) * 1000,))
            await response.write_eof()
            return response

        except HttpStatus as status:
            return status.as_response()

    def route(self):
        pass


class HttpStatus(Exception):
    def __init__(self, status=200, content=b'', content_type='text/plain'):
        self.status = status
        self.content = content
        self.content_type = content_type

    def as_response(self):
        return aiohttp.web.Response(
            status=self.get_status(),
            headers=self.get_headers(),
            body=self.get_body(),
            content_type=self.get_content_type(),
        )

    def get_headers(self):
        return {}

    def get_status(self):
        return self.status

    def get_body(self):
        return self.content

    def get_content_type(self):
        return self.content_type


class NotFound(HttpStatus):
    """The backend was not found for one reason or another."""

    def __init__(self, content=b'', content_type="text/plain"):
        super().__init__(status=404, content=content, content_type=content_type)


class Redirect(HttpStatus):
    def get_content_type(self):
        return None

    def get_status(self):
        return 302 if self.temporary else 301

    def get_headers(self):
        return {
            'Location': self.url,
        }

    def __init__(self, url, temporary=True):
        self.url = url
        self.temporary = temporary


class StaticResponse(HttpStatus):
    pass


class AbstractResolver(metaclass=ABCMeta):
    @abstractmethod
    async def find_destination(self, request):
        """Return a tuple (host, port) for the passed request
        :param request:
        """

    @abstractmethod
    async def cleanup(self):
        """Clean up resources"""


class GoogleResolver(AbstractResolver):
    """
    Example dummy resolver, routes everything to one (host, port) pair.
    """
    def cleanup(self):
        pass

    async def find_destination(self, request):
        return 'www.google.com', 80


class ReverseProxyRouter(aiohttp.abc.AbstractRouter):
    def __init__(self, resolver: AbstractResolver):
        super().__init__()
        self.resolver = resolver

    async def cleanup(self):
        await self.resolver.cleanup()

    async def resolve(self, request):
        return ReverseProxyMatch(self.resolver)


