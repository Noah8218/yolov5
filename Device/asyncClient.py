import asyncio
from PIL import Image
import io
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from Yolov5 import yolov5Defect

class Client:
    def __init__(self, host='127.0.0.1', port=5000, on_connect=None, on_disconnect=None, on_message=None, run_classification=None):
        self.host = host
        self.port = port
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.on_message = on_message
        self.connected = False
        self.run_classification = run_classification
        print(f"Type of RunClassification: {type(self.run_classification)}")  # Add this line

    async def start(self, delay=5):
        while not self.connected:
            try:
                self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
                print(f'Connected to server at {self.host}:{self.port}')
                self.connected = True
                if self.on_connect:
                    self.on_connect()
                await self.read()
            except Exception as e:
                print(f"Failed to connect to server at {self.host}:{self.port}, retrying in {delay} seconds...")
                await asyncio.sleep(delay)

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
                # Increase buffer size
                data = await self.reader.read(1024)
                    
                # Check if data contains both message and image data
                if b'\n\n' in data:
                    message_data, image_data = data.split(b'\n\n', 1)
                        
                    # Decode message data
                    message = message_data.decode()
                    print(f'Received: {message}')
                        
                    if message == 'StartDefect':
                        # Pass the image data to RunClassification function
                        image = Image.open(io.BytesIO(image_data))
                        # Run the classification
                        h =  image.height
                        w =  image.width
                        print(image.format)
                        yolov5Defect.detect_and_draw(image)
                else:
                    # If data contains only a message, decode it
                    message = data.decode()
                    print(f'Received: {message}')

                # Process the message
                self.process_message(message)

            except Exception as e:
                print(e)

    def process_message(self, message):
        # Enum값에 따른 분기 처리
        if message == 'StartTraining':
            print("Start training...")
        elif message == 'StopTraining':
            print("Stop training...")
        elif message == 'StartDefect':
            print("Start defect...")
        elif message == 'StopDefect':
            print("Stop defect...")

def on_connect():
    print("Connection established.")

def on_disconnect():
    print("Connection lost.")

def on_message(message):
    print("Message received: ", message)

def run_classification(image_data):
    print("Running classification with image data...")
    # Implement your classification logic here

if __name__ == "__main__":
    client = Client(on_connect=on_connect, on_disconnect=on_disconnect, on_message=on_message, run_classification=run_classification)
    asyncio.run(client.start())