import json

import aiohttp
import aiohttp.web
import aiohttp.server
import aiohttp.client
import aiohttp.abc


THE_HOST = 'google.com'


async def the_handler(request):
    return aiohttp.web.Response(body=b"<h1>Hello, asyncio</h1>")


class ReverseProxyMatch(aiohttp.abc.AbstractMatchInfo):
    def handler(self, request):
        return the_handler(request)

    def route(self):
        pass


class AllRouter(aiohttp.abc.AbstractRouter):
    def __init__(self):
        super().__init__()

    async def resolve(self, request):
        return ReverseProxyMatch()


class ReverseProxyHandler(aiohttp.server.ServerHttpProtocol):

    async def handle_request(self, message, payload):
        url = 'http://' + THE_HOST + message.path
        print(url)
        async with aiohttp.client.request(message.method, url) as r:
            response = aiohttp.Response(self.writer, r.status,
                                        http_version=message.version)
            print({i: r.headers[i] for i in r.headers})
            response.add_headers(*[(i, r.headers[i]) for i in r.headers])
            response.send_headers()
            response.write(r.content.read())
            await response.write_eof()


if __name__ == "__main__":
    import asyncio
    loop = asyncio.get_event_loop()
    app = aiohttp.web.Application(router=AllRouter())
    handler = app.make_handler()
    f = loop.create_server(handler, '0.0.0.0', '8088')
    # f = loop.create_server(lambda: ReverseProxyHandler(debug=True, keep_alive=75), '0.0.0.0', '8088')
    srv = loop.run_until_complete(f)
    print("serving on:", srv.sockets[0].getsockname())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
