from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
from crashDetector import main_watcher

app = FastAPI()

# Allow your Next.js app to talk to this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws/process")
async def process_video(websocket: WebSocket):
    await websocket.accept()
    
    try:
        # 1. Receive the video path from React
        data = await websocket.receive_text()
        payload = json.loads(data)
        video_path = payload.get("video_path")

        if not video_path:
            await websocket.send_json({"log": "❌ Error: No video path provided."})
            return

        # 2. Setup an async queue for thread-safe logging
        loop = asyncio.get_running_loop()
        queue = asyncio.Queue()

        def sync_log_callback(msg: str):
            """Pushes logs from the sync video thread into the async queue."""
            loop.call_soon_threadsafe(queue.put_nowait, msg)

        # 3. Send queue items to the WebSocket as they arrive
        async def send_logs():
            while True:
                msg = await queue.get()
                if msg is None: # None acts as our stop signal
                    break
                await websocket.send_json({"log": msg})

        sender_task = asyncio.create_task(send_logs())

        # 4. Run your heavy video processing in a background thread
        await loop.run_in_executor(None, main_watcher, video_path, sync_log_callback)

        # 5. Tell the sender loop we're done
        await queue.put(None)
        await sender_task
        
        await websocket.send_json({"log": "✅ Processing gracefully finished."})

    except WebSocketDisconnect:
        print("Client disconnected.")
    except Exception as e:
        await websocket.send_json({"log": f"❌ Server Error: {str(e)}"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)