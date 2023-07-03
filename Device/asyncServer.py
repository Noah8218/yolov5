import asyncio

class EchoServerProtocol(asyncio.Protocol):
    def connection_made(self, transport):
        self.transport = transport
        self.peername = transport.get_extra_info('peername')
        print(f'Connection from {self.peername}')

    def data_received(self, data):
        message = data.decode()
        print(f'Data received: {message!r} from {self.peername}')

        print(f'Send: {message!r}')
        self.transport.write(data)

    def connection_lost(self, exc):
        print(f'Connection lost with {self.peername}')
        self.transport.close()

async def main():
    loop = asyncio.get_running_loop()

    server = await loop.create_server(
        lambda: EchoServerProtocol(),
        '127.0.0.1', 5000)

    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())