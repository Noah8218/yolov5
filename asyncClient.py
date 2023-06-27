import asyncio

class EchoClientProtocol(asyncio.Protocol):
    def __init__(self, message, loop):
        self.message = message
        self.loop = loop

    def connection_made(self, transport):
        self.transport = transport
        print('Connection made')
        transport.write(self.message.encode())
        print(f'Send: {self.message!r}')

    def data_received(self, data):
        print(f'Data received: {data.decode()!r}')

    def connection_lost(self, exc):
        print('Connection lost')
        self.loop.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    message = 'Hello, Server!'
    coro = loop.create_connection(
        lambda: EchoClientProtocol(message, loop),
        '127.0.0.1', 5000)
    loop.run_until_complete(coro)
    loop.run_forever()
    loop.close()