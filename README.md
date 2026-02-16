# Nemotron Sentinel: AI Crash Detector
Nemotron Sentinel is a multi-agent AI surveillance system designed to detect severe traffic accidents in video feeds. 
Powered by NVIDIA's Nemotron Vision Language Models (VLM) and LangGraph, it autonomously scans video streams, identifies crashes, verifies evidence to prevent false alarms, and generates structured emergency dispatch reports.

# Features
Real-time Surveillance: Scans video feeds at configurable intervals (default: every 2 seconds) to optimize token usage.
Multi-Agent Workflow:
- Reporter: Analyzes crash dynamics, hazards, and severity.
- Critic: Validates evidence to reject false positives (e.g., normal traffic, ambiguous scenes).
- Dispatcher: Formats verified incidents into actionable JSON dispatch data.
Structured Output: Uses Pydantic to ensure clean, parseable JSON reports for downstream integration.
Visual Logic: Utilizes nvidia/nemotron-nano-12b-v2-vl for high-fidelity image understanding.

