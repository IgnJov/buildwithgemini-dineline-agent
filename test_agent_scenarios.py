import asyncio
import os
import dotenv

dotenv.load_dotenv(".env")
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
os.environ["GOOGLE_CLOUD_PROJECT"] = "qwiklabs-gcp-04-6a213cd4ec79"
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory import InMemoryMemoryService
from google.genai import types
from app.agent import root_agent

async def run_scenario(runner: Runner, user_id: str, session_id: str, prompt: str, label: str):
    print(f"\n=======================================================")
    print(f"🎬 {label}")
    print(f"👤 USER: {prompt}")
    print(f"=======================================================")
    
    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=prompt)],
    )
    
    response_texts = []
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=content,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.function_call:
                    print(f"  🔧 [TOOL CALL] {part.function_call.name}({part.function_call.args})")
                elif part.function_response:
                    resp_summary = str(part.function_response.response)[:160]
                    print(f"  📥 [TOOL RESPONSE] {resp_summary}...")
                elif part.text:
                    response_texts.append(part.text)
                    
    full_response = "".join(response_texts).strip()
    print(f"\n🤖 AGENT:\n{full_response}\n")
    return full_response

async def main():
    print("🚀 Initializing DineLine AI Test Runner...")
    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()
    memory_service = InMemoryMemoryService()
    
    runner = Runner(
        agent=root_agent,
        session_service=session_service,
        artifact_service=artifact_service,
        memory_service=memory_service,
        app_name="dineline_test_app",
    )
    
    user_id = "test_user_alex"
    session_id = "session_001"
    
    # Create session
    await session_service.create_session(
        app_name="dineline_test_app",
        user_id=user_id,
        session_id=session_id,
    )
    
    # 1. Check in to queue
    await run_scenario(
        runner,
        user_id,
        session_id,
        "Hi! I'd like to join the waitlist for a table for 4 under Alex Johnson. We'd prefer a booth, and we need a high chair.",
        "SCENARIO 1: Guest Check-in (Natural Language Concierge)",
    )
    
    # 2. Check menu
    await run_scenario(
        runner,
        user_id,
        session_id,
        "While we wait, what gluten-free appetizers or mains do you recommend from your menu, and what are their prices?",
        "SCENARIO 2: Verified Menu & Dietary Query",
    )
    
    # 3. Host seating recommendations
    host_session_id = "session_host_001"
    await session_service.create_session(
        app_name="dineline_test_app",
        user_id="host_manager",
        session_id=host_session_id,
    )
    
    await run_scenario(
        runner,
        "host_manager",
        host_session_id,
        "I'm the host on duty. Look at our available tables and waiting guests. Who should we seat next and where?",
        "SCENARIO 3: Host Intelligence & Seating Recommendations",
    )
    
    # 4. Generate visual preview
    await run_scenario(
        runner,
        user_id,
        session_id,
        "Can you show me what your Decadent Molten Lava Cake looks like?",
        "SCENARIO 4: Dish Image Generation & Cloud Storage",
    )

if __name__ == "__main__":
    asyncio.run(main())
