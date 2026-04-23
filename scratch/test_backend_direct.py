import asyncio
from google.genai import types
from smart_learning_agent.runner import workflow_runner as workflow_runner_mod

# 로깅 설정
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("test_runner")

async def test_workflow():
    session_id = "test_session_direct"
    query = "C언어 포인터에 대해 알려줘"
    
    # 세션 생성 및 콘텐츠 준비
    content = await workflow_runner_mod.prepare_content(query, None, session_id)
    
    print(f"--- Workflow Start: {session_id} ---")
    try:
        async for event in workflow_runner_mod.execute_agent_stream(session_id, content):
            node_info = getattr(event, "node_info", None)
            node_name = node_info.name if node_info else "unknown"
            print(f"Event: {type(event).__name__}, Node: {node_name}, Partial: {event.partial}")
            
            if event.content:
                for part in event.content.parts:
                    if part.text:
                        print(f"  Text: {part.text[:50]}...")
    except Exception as e:
        print(f"!!! Error Caught: {repr(e)}")
        import traceback
        traceback.print_exc()
    print("--- Workflow End ---")

if __name__ == "__main__":
    asyncio.run(test_workflow())
