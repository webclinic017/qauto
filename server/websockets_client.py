#!/usr/bin/env python

import asyncio
import websockets

async def hello(uri):
    async with websockets.connect(uri) as websocket:
        await websocket.send("Hello world!")
        ret = await websocket.recv()
        print('recv', ret)

asyncio.get_event_loop().run_until_complete(
    hello('ws://localhost:8765'))