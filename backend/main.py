from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import os

# Import your crash detector
from crashDetector import main_watcher

app = FastAPI()

# CORS configuration - allows Next.js frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws/process")
async def process_video(websocket: WebSocket):
    """
    WebSocket endpoint that processes videos and streams logs back to the client.
    """
    await websocket.accept()
    
    try:
        # 1. Receive the video path from the React frontend
        data = await websocket.receive_text()
        payload = json.loads(data)
        video_path = payload.get("video_path")

        if not video_path:
            await websocket.send_json({"log": "❌ Error: No video path provided."})
            return

        # Resolve relative paths if needed
        if not os.path.isabs(video_path):
            # Assuming videos are in a 'public' or 'videos' folder
            video_path = os.path.join(os.getcwd(), video_path.lstrip('./'))

        if not os.path.exists(video_path):
            await websocket.send_json({"log": f"❌ Video file not found: {video_path}"})
            return

        await websocket.send_json({"log": f"📹 Starting analysis on: {os.path.basename(video_path)}"})

        # 2. Create an async queue for thread-safe logging
        loop = asyncio.get_running_loop()
        log_queue = asyncio.Queue()

        def sync_log_callback(msg: str):
            """
            Callback function passed to main_watcher.
            Pushes logs from the synchronous video processing thread 
            into the async queue for WebSocket transmission.
            """
            try:
                loop.call_soon_threadsafe(log_queue.put_nowait, msg)
            except Exception as e:
                print(f"Error in log callback: {e}")

        # 3. Background task to send queued logs to WebSocket
        async def send_logs():
            while True:
                msg = await log_queue.get()
                if msg is None:  # None signals completion
                    break
                try:
                    await websocket.send_json({"log": msg})
                except Exception as e:
                    print(f"Error sending log: {e}")
                    break

        sender_task = asyncio.create_task(send_logs())

        # 4. Run the video processing in a thread pool executor
        # This prevents blocking the async event loop
        await loop.run_in_executor(
            None, 
            main_watcher, 
            video_path, 
            sync_log_callback
        )

        # 5. Signal completion and wait for sender to finish
        await log_queue.put(None)
        await sender_task
        
        await websocket.send_json({"log": "✅ Video analysis complete."})

    except WebSocketDisconnect:
        print("⚠️ Client disconnected during processing.")
    except Exception as e:
        error_msg = f"❌ Server Error: {str(e)}"
        print(error_msg)
        try:
            await websocket.send_json({"log": error_msg})
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass

@app.get("/")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "online", "service": "Crash Detection API"}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Crash Detection Server...")
    print("📡 WebSocket endpoint: ws://localhost:8000/ws/process")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)