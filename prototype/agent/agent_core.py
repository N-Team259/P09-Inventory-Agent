import json
import time
import uuid
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import ollama
from database.db_manager import get_connection
from agent.smart_tools import (
    smart_cross_inventory_balancer,
    contextual_forecaster_and_simulator,
    anomaly_and_audit_investigator,
    perishability_and_cold_chain_guardian,
    safety_and_layout_optimizer,
)

# الكشف التلقائي عن النموذج المتاح محلياً في Ollama
def _resolve_local_model() -> str:
    try:
        models_resp = ollama.list()
        models = getattr(models_resp, "models", []) or models_resp.get("models", [])
        names = [getattr(m, "model", None) or m.get("name") or m.get("model") for m in models]
        for preferred in ["qwen2.5:3b", "qwen2.5:7b", "llama3.1:8b", "llama3.2:3b", "mistral"]:
            for n in names:
                if n and n.startswith(preferred.split(":")[0]):
                    return n
        if names:
            return names[0]
    except Exception:
        pass
    return "qwen2.5:3b"

OLLAMA_MODEL = _resolve_local_model()
MAX_AGENT_LOOPS = 5          # 03-NFR: حد أقصى 5 دورات للوكيل في الطلب الواحد
TOOL_TIMEOUT_SECONDS = 15.0  # 03-NFR: مهلة زمنية لكل أداة

TOOL_REGISTRY = {
    "smart_cross_inventory_balancer": smart_cross_inventory_balancer,
    "contextual_forecaster_and_simulator": contextual_forecaster_and_simulator,
    "anomaly_and_audit_investigator": anomaly_and_audit_investigator,
    "perishability_and_cold_chain_guardian": perishability_and_cold_chain_guardian,
    "safety_and_layout_optimizer": safety_and_layout_optimizer,
}

SYSTEM_PROMPT = """You are the P09 Autonomous Inventory Tracking Agent for N-Team.
You operate strictly offline via local Ollama across 4 departments:
1. GEN_TRADE (General Trade / التجارة العامة)
2. ECOMMERCE (E-commerce / التجارة الإلكترونية)
3. REFRIGERATION (Refrigeration / التبريد)
4. COMP_LABS (Computer Labs / مختبرات الحاسبات)

STRICT GOVERNANCE RULES:
1. SCOPE ONLY: Answer ONLY questions related to inventory, warehouses, labs, stock forecasting, audits, expiration (FEFO), and shelf safety. Politely refuse any general/unrelated questions.
2. NO GUESSING (01-NFR): If a user asks to analyze, balance, forecast, or optimize a department without specifying which of the 4 departments, DO NOT guess—ask the user explicitly to clarify the department first.
3. PROPOSAL ONLY (02-NFR): You NEVER execute purchases or modify stock directly. Your tools generate pending decision drafts (TRANSFER_ORDER, PURCHASE_REQUEST, AUDIT_ALERT, DISPOSAL_REPORT, LAYOUT_PLAN) for Human Manager approval.
4. GROUNDED NUMBERS ONLY (05-NFR): Cite exact SKUs, numbers, and pending_decision_ids returned by the tools. Never invent or fabricate numbers.
5. TRANSPARENT FAILURE (03-NFR): If a tool fails or times out, report the exact failure reason and never fabricate a substitute result.
6. Reply in the same language as the user (Arabic or English), clearly and concisely.
"""

def _log_execution(session_id: str, user_query: str, step: int, tool_name: str, tool_input: dict, tool_output: str, duration_ms: float, status: str):
    conn = get_connection()
    conn.execute("""
        INSERT INTO agent_execution_log (
            session_id, user_query, step_number, tool_name, tool_input, tool_output, duration_ms, status, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        session_id,
        user_query,
        step,
        tool_name,
        json.dumps(tool_input, ensure_ascii=False),
        tool_output,
        round(duration_ms, 2),
        status,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    conn.close()

def _execute_tool_with_timeout(func, kwargs: dict) -> tuple[str, str, float]:
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, **kwargs)
        try:
            result = future.result(timeout=TOOL_TIMEOUT_SECONDS)
            elapsed_ms = (time.perf_counter() - start) * 1000
            status = "VALIDATION_ERROR" if '"error":' in result else "SUCCESS"
            return result, status, elapsed_ms
        except FuturesTimeoutError:
            elapsed_ms = (time.perf_counter() - start) * 1000
            err = json.dumps({
                "error": f"03-NFR Timeout Error: Tool exceeded {TOOL_TIMEOUT_SECONDS}s limit.",
                "cause": "Execution timed out."
            }, ensure_ascii=False)
            return err, "TIMEOUT", elapsed_ms
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            err = json.dumps({
                "error": f"03-NFR Tool Execution Error: {str(e)}",
                "cause": type(e).__name__
            }, ensure_ascii=False)
            return err, "ERROR", elapsed_ms

def run_inventory_agent(user_message: str) -> dict:
    session_id = str(uuid.uuid4())[:8]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message}
    ]
    tools_list = list(TOOL_REGISTRY.values())
    executed_steps = []

    for step in range(1, MAX_AGENT_LOOPS + 1):
        try:
            response = ollama.chat(
                model=OLLAMA_MODEL,
                messages=messages,
                tools=tools_list,
                options={"temperature": 0.1}
            )
        except Exception as e:
            err_msg = f"⚠️ تعذر الاتصال بمحرك Ollama المحلي ({OLLAMA_MODEL}): {str(e)}"
            _log_execution(session_id, user_message, step, "ollama_llm", {}, err_msg, 0.0, "LLM_ERROR")
            return {"reply": err_msg, "session_id": session_id, "steps": executed_steps, "model": OLLAMA_MODEL}

        assistant_msg = response.message
        messages.append(assistant_msg)

        tool_calls = getattr(assistant_msg, "tool_calls", None)
        if not tool_calls:
            final_text = assistant_msg.content or "تمت المعالجة."
            return {"reply": final_text, "session_id": session_id, "steps": executed_steps, "model": OLLAMA_MODEL}

        for tc in tool_calls:
            fn_name = tc.function.name
            fn_args = tc.function.arguments or {}
            if fn_name not in TOOL_REGISTRY:
                out_str = json.dumps({"error": f"Unauthorized tool '{fn_name}' blocked by governance policy."})
                _log_execution(session_id, user_message, step, fn_name, fn_args, out_str, 0.0, "BLOCKED")
                messages.append({"role": "tool", "content": out_str})
                executed_steps.append({"step": step, "tool": fn_name, "status": "BLOCKED"})
                continue

            out_str, status, duration_ms = _execute_tool_with_timeout(TOOL_REGISTRY[fn_name], fn_args)
            _log_execution(session_id, user_message, step, fn_name, fn_args, out_str, duration_ms, status)
            executed_steps.append({
                "step": step,
                "tool": fn_name,
                "args": fn_args,
                "status": status,
                "duration_ms": round(duration_ms, 2)
            })
            messages.append({"role": "tool", "content": out_str})

    # 03-NFR: الوصول للحد الأقصى (5 دورات) دون إجابة نهائية
    limit_msg = (
        f"⚠️ تم إيقاف المعالجة تلقائياً بعد الوصول إلى الحد الأقصى المسموح به ({MAX_AGENT_LOOPS} دورات) "
        f"وفق متطلب الجودة (03-NFR). يرجى تضييق نطاق الطلب أو تحديد القسم والمادة بدقة."
    )
    _log_execution(session_id, user_message, MAX_AGENT_LOOPS, "MAX_LOOPS_GUARD", {}, limit_msg, 0.0, "MAX_LOOPS_REACHED")
    return {"reply": limit_msg, "session_id": session_id, "steps": executed_steps, "model": OLLAMA_MODEL}
