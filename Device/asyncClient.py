import asyncio

class Client:
    def __init__(self, host='127.0.0.1', port=5000, on_connect=None, on_disconnect=None, on_message=None):
        self.host = host
        self.port = port
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.on_message = on_message
        self.connected = False

    async def start(self):
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
        print(f'Connected to server at {self.host}:{self.port}')
        self.connected = True
        if self.on_connect:
            self.on_connect()
        await self.read()

    async def disconnect(self):
        if self.writer:
            self.writer.close()
            if self.connected:
                await self.writer.wait_closed()
        self.connected = False
        print(f'Disconnected from server at {self.host}:{self.port}')
        if self.on_disconnect:
            self.on_disconnect()

    async def send(self, message):
        print(f'Send: {message}')
        self.writer.write(message.encode())
        await self.writer.drain()

    async def read(self):
        while self.connected:
            try:
                data = await self.reader.read(100)
                message = data.decode()
                print(f'Received: {message}')
                if self.on_message:
                    self.on_message(message)
                
                # Enum값에 따른 분기 처리
                if message == 'StartTraining':
                    print("Start training...")
                elif message == 'StopTraining':
                    print("Stop training...")
                elif message == 'StartDefect':
                    print("Start defect...")
                elif message == 'StopDefect':
                    print("Stop defect...")

            except ConnectionResetError:
                print("Connection lost to server.")
                await self.disconnect()

def on_connect():
    print("Connection established.")

def on_disconnect():
    print("Connection lost.")

def on_message(message):
    print("Message received: ", message)