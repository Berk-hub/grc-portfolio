#!/usr/bin/env python3

import asyncio
import signal

LISTEN_HOST = "127.0.0.1"
LISTEN_PORT = 18081

TARGET_HOST = "127.0.0.1"
TARGET_PORT = 8081


async def copy_stream(reader, writer):
    try:
        while True:
            data = await reader.read(65536)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except (ConnectionError, asyncio.CancelledError):
        pass
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def handle_client(client_reader, client_writer):
    peer = client_writer.get_extra_info("peername")
    print(f"CLIENT CONNECTED {peer}", flush=True)

    try:
        server_reader, server_writer = await asyncio.open_connection(
            TARGET_HOST,
            TARGET_PORT,
        )
    except Exception as exc:
        print(f"TARGET CONNECTION FAILED: {exc}", flush=True)
        client_writer.close()
        await client_writer.wait_closed()
        return

    try:
        await asyncio.gather(
            copy_stream(client_reader, server_writer),
            copy_stream(server_reader, client_writer),
        )
    finally:
        print(f"CLIENT DISCONNECTED {peer}", flush=True)


async def main():
    server = await asyncio.start_server(
        handle_client,
        LISTEN_HOST,
        LISTEN_PORT,
    )

    print(
        f"BACKEND LINK PROXY LISTENING "
        f"{LISTEN_HOST}:{LISTEN_PORT} -> "
        f"{TARGET_HOST}:{TARGET_PORT}",
        flush=True,
    )

    async with server:
        await server.serve_forever()


try:
    asyncio.run(main())
except KeyboardInterrupt:
    pass
