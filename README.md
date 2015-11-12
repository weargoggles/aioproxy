# example __main__

```
sk_exit(loop_instance, signal_name):
    print("got signal %s, stopping" % signal_name)
    loop_instance.stop()


if __name__ == "__main__":

    loop = asyncio.get_event_loop()
    for signame in ('SIGINT', 'SIGTERM'):
        loop.add_signal_handler(getattr(signal, signame),
                                functools.partial(ask_exit, loop, signame))

    resolver_instance = CatfishRedisResolver()
    router = ReverseProxyRouter(resolver_instance)

    app = aiohttp.web.Application(router=router)
    handler = app.make_handler()
    f = loop.create_server(handler, '0.0.0.0', '8080')
    srv = loop.run_until_complete(f)
    print("serving on:", 'http://%s:%d' % srv.sockets[0].getsockname())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(handler.finish_connections(1.0))
        srv.close()
        loop.run_until_complete(router.cleanup())
        loop.run_until_complete(srv.wait_closed())
        loop.run_until_complete(app.finish())
    loop.close()
```
