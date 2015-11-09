import json

import aiohttp
import aiohttp.web
import aiohttp.server
import aiohttp.client
import aiohttp.abc


async def the_handler(request):
    host, port = request.host.split(':')
    if host == 'localhost':
        host = 'www.weargoggles.co.uk'
    async with aiohttp.client.request(
        request.method,
        'http://' + host + request.path,
        chunked=1024
    ) as r:
        response = aiohttp.web.StreamResponse(status=r.status,
                                              headers=r.headers)
        await response.prepare(request)
        content = r.content
        while True:
            chunk = await content.read(1024)
            if not chunk:
                break
            response.write(chunk)
        await response.write_eof()
        return response


class ReverseProxyMatch(aiohttp.abc.AbstractMatchInfo):
    # noinspection PyMethodOverriding
    def handler(self, request):
        return the_handler(request)

    def route(self):
        pass


class AllRouter(aiohttp.abc.AbstractRouter):
    def __init__(self):
        super().__init__()

    async def resolve(self, request):
        return ReverseProxyMatch()


if __name__ == "__main__":
    import asyncio

    loop = asyncio.get_event_loop()
    app = aiohttp.web.Application(router=AllRouter())
    handler = app.make_handler()
    f = loop.create_server(handler, '0.0.0.0', '8088')
    srv = loop.run_until_complete(f)
    print("serving on:", srv.sockets[0].getsockname())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
