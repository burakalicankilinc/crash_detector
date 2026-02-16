import cv2
import base64
import os
import json
from typing import TypedDict, Any
from langgraph.graph import StateGraph, END
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Environment Setup
os.environ["NVIDIA_API_KEY"] = "ADD API"

def encode_image(image):
    """Compress and encode frame to base64."""
    _, buffer = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
    return base64.b64encode(buffer).decode("utf-8")

# State and Schema Definitions
class AgentState(TypedDict):
    frame_b64: str          
    frame_b642: str
    initial_trigger: str    
    incident_report: str    
    critique_score: str     
    final_decision: str
    log_callback: Any
    timestamp: str  # Added for better tracking

class AccidentReport(BaseModel):
    is_accident: bool = Field(description="Is there definitely a crash?")
    what_type: str = Field(description="e.g. Multi-Car Collision, Rollover, Rear-End")
    severity: str = Field(description="Low, Medium, or High")
    hazards: str = Field(description="e.g. Traffic Obstruction, Fuel Leak, Potential Fire")
    description: str = Field(description="Brief visual summary")
    location_bbox: list[int] = Field(description="Estimated [x1, y1, x2, y2]. [0,0,0,0] if unclear.", default=[0,0,0,0])

VISION_MODEL = "nvidia/nemotron-nano-12b-v2-vl"

# Agent Nodes
def reporter_agent(state: AgentState):
    log = state.get("log_callback", print)
    log("\n[NODE: Investigator] 🔍 Analyzing crash dynamics...")
    
    llm = ChatNVIDIA(model=VISION_MODEL)
    structured_llm = llm.with_structured_output(AccidentReport)
    
    prompt = """
    You are a 911 Emergency Dispatch AI. Analyze this image of a traffic accident.
    CRITICAL PROTOCOL: Assume potential injuries in ANY vehicle damage.
    You MUST recommend dispatching emergency units for any crash.
    Never say "No action required."
    """
    
    msg = HumanMessage(content=[
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{state['frame_b64']}"}}
    ])
    
    try:
        response = structured_llm.invoke([msg])
        report = response.model_dump()
        
        # Log structured report for frontend
        log(f"[Investigator] Accident Type: {report['what_type']}")
        log(f"[Investigator] Severity: {report['severity']}")
        log(f"[Investigator] Hazards: {report['hazards']}")
        
        return {"incident_report": response.model_dump_json()}
    except Exception as e:
        log(f"[ERROR] Reporter Agent failed: {e}")
        return {"incident_report": json.dumps({"is_accident": False, "what_type": "Unknown", "severity": "Unknown", "hazards": "Analysis Failed", "description": str(e), "location_bbox": [0,0,0,0]})}

def critic_agent(state: AgentState):
    log = state.get("log_callback", print)
    log(f"[NODE: Critic] ⚖️ Validating evidence...")
    
    llm = ChatNVIDIA(model=VISION_MODEL)
    
    prompt = f"""
    You are a Safety Supervisor. Goal: PREVENT MISSED ACCIDENTS.
    REPORT TO VALIDATE: "{state['incident_report']}"
    
    DECISION RULES:
    1. If you see ANY vehicle damage, debris, or cars stopped at odd angles -> APPROVED.
    2. If the scene is ambiguous -> APPROVED (Safety first).
    3. Only REJECT if it is 100% normal flowing traffic.
    
    Answer strictly: APPROVED or REJECTED
    """
    
    msg = HumanMessage(content=[
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{state['frame_b642']}"}}
    ])
    
    try:
        response = llm.invoke([msg])
        score = response.content.strip().upper()
        
        final_score = "APPROVED" if "APPROVED" in score else "REJECTED"
        log(f"[NODE: Critic] Verdict: {final_score}")
        return {"critique_score": final_score}
    except Exception as e:
        log(f"[ERROR] Critic Agent failed: {e}")
        return {"critique_score": "REJECTED"}

def dispatcher_agent(state: AgentState):
    log = state.get("log_callback", print)
    
    try:
        # Parse the incident report
        report = json.loads(state['incident_report'])
        
        # Create formatted emergency dispatch
        dispatch_info = {
            "EmergencyType": f"{report['severity']} Severity {report['what_type']}",
            "ActionRequired": True,
            "ConfidenceScore": "High" if report['is_accident'] else "Medium",
            "Reason": report['description'],
            "Location": f"Camera Feed - Timestamp: {state.get('timestamp', 'Unknown')}",
            "Hazards": report['hazards'],
            "Units": [
                {"Type": "Fire & Rescue", "Count": 2 if report['severity'] == "High" else 1},
                {"Type": "Ambulance", "Count": 2 if report['severity'] in ["High", "Medium"] else 1},
                {"Type": "Police", "Count": 2}
            ]
        }
        
        # Log formatted JSON for the frontend to parse and display nicely
        log(json.dumps(dispatch_info, indent=2))
        
        log("\n" + "█"*60)
        log("🚨  EMERGENCY RESPONSE DISPATCHED  🚨")
        log("█"*60)
        log(f"Type: {dispatch_info['EmergencyType']}")
        log(f"Location: {dispatch_info['Location']}")
        log(f"Hazards: {dispatch_info['Hazards']}")
        log("█"*60 + "\n")
        
        return {"final_decision": "DISPATCHED"}
    except Exception as e:
        log(f"[ERROR] Dispatcher Agent failed: {e}")
        return {"final_decision": "ERROR"}

# Graph Construction
workflow = StateGraph(AgentState)
workflow.add_node("reporter", reporter_agent)
workflow.add_node("critic", critic_agent)
workflow.add_node("dispatcher", dispatcher_agent)

workflow.set_entry_point("reporter")
workflow.add_edge("reporter", "critic")

def router(state: AgentState):
    log = state.get("log_callback", print)
    if state["critique_score"] == "APPROVED":
        return "dispatcher"
    log("[System] False alarm discarded. Continuing surveillance...")
    return END

workflow.add_conditional_edges("critic", router, {"dispatcher": "dispatcher", END: END})
workflow.add_edge("dispatcher", END)
sentinel_app = workflow.compile()

# Main Surveillance Logic
def main_watcher(video_path, log_callback=print):
    """
    Main video surveillance function with real-time logging.
    """
    if not os.path.exists(video_path):
        log_callback(f"❌ Video not found at {video_path}.")
        return

    watcher_llm = ChatNVIDIA(model=VISION_MODEL)
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    if fps == 0 or fps is None:
        log_callback("❌ Error reading video stream. Invalid FPS.")
        return

    step_frames = int(fps * 2.0)  # Sample every 2 seconds
    curr_frame = 0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    log_callback("━"*60)
    log_callback("🚔 NEMOTRON SENTINEL ACTIVE")
    log_callback(f"📹 Video: {os.path.basename(video_path)}")
    log_callback(f"⏱️  Duration: {int(total_frames/fps)} seconds | FPS: {fps:.1f}")
    log_callback(f"🔍 Scanning every 2 seconds")
    log_callback("━"*60 + "\n")

    while cap.isOpened():
        cap.set(cv2.CAP_PROP_POS_FRAMES, curr_frame)
        ret, frame = cap.read()
        if not ret: 
            break

        timestamp = f"{int(curr_frame/fps//60):02}:{int(curr_frame/fps%60):02}"
        progress = int((curr_frame / total_frames) * 100)
        log_callback(f"⏰ [{timestamp}] Progress: {progress}% - Analyzing frame...")
        
        b64_img = encode_image(frame)
        
        trigger_prompt = """
        Look for a SEVERE CAR ACCIDENT.
        Reply strictly: "DETECTED: YES" or "DETECTED: NO"
        """
        
        msg = HumanMessage(content=[
            {"type": "text", "text": trigger_prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
        ])
        
        try:
            trigger_res = watcher_llm.invoke([msg]).content.strip().upper()
            
            if "YES" in trigger_res:
                log_callback(f"\n💥 ⚠️  IMPACT DETECTED AT {timestamp} ⚠️ 💥")
                log_callback("🚨 Initiating Emergency Protocol...")

                # Capture a second frame for validation (0.5s later)
                next_frame_pos = min(curr_frame + int(fps * 0.5), total_frames - 1)
                cap.set(cv2.CAP_PROP_POS_FRAMES, next_frame_pos)
                ret_next, frame_next = cap.read()
                b64_img_2 = encode_image(frame_next if ret_next else frame)
                
                inputs = {
                    "frame_b64": b64_img,
                    "frame_b642": b64_img_2, 
                    "initial_trigger": "Security Event",
                    "incident_report": "",
                    "critique_score": "",
                    "final_decision": "",
                    "timestamp": timestamp,
                    "log_callback": log_callback 
                }
                
                sentinel_app.invoke(inputs)
                
                log_callback("\n✅ Emergency protocol completed. Stopping surveillance.")
                break 

            else: 
                log_callback(f"✓ Status: All clear at {timestamp}")
                
        except Exception as e:
            log_callback(f"⚠️  [Skip {timestamp}] API Error: {e}")

        curr_frame += step_frames
        
        # Exit if we've processed the entire video
        if curr_frame >= total_frames:
            break

    cap.release()
    log_callback("\n━"*60)
    log_callback("🏁 Surveillance session ended.")
    log_callback("━"*60)

if __name__ == "__main__":
    target_video = "/Users/burakalicankilinc/Desktop/nvidia/crash.mp4"
    main_watcher(target_video)