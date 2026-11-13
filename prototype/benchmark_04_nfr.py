import time
import statistics
import urllib.request
import json

BASE_URL = "http://127.0.0.1:8000"

QUERIES = [
    "وازن مخزون قسم COMP_LABS",
    "تنبأ بالاستهلاك للـ 30 يوم القادمة في قسم COMP_LABS",
    "نفذ تدقيق جنائي في قسم COMP_LABS",
    "افحص التخطيط المكاني والسلامة في قسم COMP_LABS",
    "افحص تواريخ صلاحية الدفعات وفق FEFO في قسم REFRIGERATION",
    "وازن مخزون قسم ECOMMERCE",
    "تنبأ بالاستهلاك للـ 30 يوم القادمة في قسم ECOMMERCE",
    "نفذ تدقيق جنائي في قسم ECOMMERCE",
    "افحص التخطيط المكاني والسلامة في قسم ECOMMERCE",
    "وازن مخزون قسم GEN_TRADE",
    "تنبأ بالاستهلاك للـ 30 يوم القادمة في قسم GEN_TRADE",
    "نفذ تدقيق جنائي في قسم GEN_TRADE",
    "افحص التخطيط المكاني والسلامة في قسم GEN_TRADE",
    "وازن مخزون قسم REFRIGERATION",
    "تنبأ بالاستهلاك للـ 30 يوم القادمة في قسم REFRIGERATION",
    "نفذ تدقيق جنائي في قسم REFRIGERATION",
    "افحص التخطيط المكاني والسلامة في قسم REFRIGERATION",
    "افحص الصلاحية خلال 15 يوم القادمة",
    "حاكي مضاعفة الطلب 2.5 مرة في قسم COMP_LABS",
    "وازن مخزون مختبرات الحاسبات"
]

def post_json(endpoint, payload):
    req = urllib.request.Request(
        f"{BASE_URL}{endpoint}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))

print("🚀 بدء اختبار الأداء (04-NFR): 20 طلباً متتالياً على RTX 4060...\n")
login_res = post_json("/api/login", {"username": "manager", "password": "1234"})
session_id = login_res["session_id"]

latencies = []
report_lines = [
    "====================================================================",
    "P09 - NFR-04 BENCHMARK REPORT (20 CONSECUTIVE REQUESTS ON RTX 4060)",
    "===================================================================="
]

for idx, q in enumerate(QUERIES, 1):
    t0 = time.perf_counter()
    res = post_json("/api/chat", {"session_id": session_id, "message": q})
    dt_ms = (time.perf_counter() - t0) * 1000
    latencies.append(dt_ms)
    line = f"[{idx:02d}/20] {dt_ms:7.1f} ms ({dt_ms/1000:.2f}s) | Query: {q}"
    print(line)
    report_lines.append(line)

avg_ms = statistics.mean(latencies)
min_ms = min(latencies)
max_ms = max(latencies)
p95_ms = sorted(latencies)[18]

summary = f"""
--------------------------------------------------------------------
SUMMARY METRICS (04-NFR COMPLIANCE):
  - Total Consecutive Requests : {len(latencies)}
  - Average Response Time      : {avg_ms:.1f} ms ({avg_ms/1000:.2f} s)
  - Fastest Response           : {min_ms:.1f} ms ({min_ms/1000:.2f} s)
  - Slowest Response           : {max_ms:.1f} ms ({max_ms/1000:.2f} s)
  - 95th Percentile (P95)      : {p95_ms:.1f} ms ({p95_ms/1000:.2f} s)
====================================================================
"""
print(summary)
report_lines.append(summary)

with open("NFR_04_BENCHMARK_RESULTS.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(report_lines))

print("✅ تم حفظ نتائج القياس الرسمية في: prototype/NFR_04_BENCHMARK_RESULTS.txt")
