import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from agent.inventory_tools import (
    add_warehouse,
    add_item,
    record_transaction,
    get_inventory,
    get_low_stock_items,
    get_warehouses,
)

load_dotenv()

SYSTEM_INSTRUCTION = """
أنت وكيل ذكي متخصص في إدارة ومتابعة المخازن (Inventory Tracking Agent).
مهمتك مساعدة المستخدم في إدارة المخازن، إضافة الأصناف، تسجيل حركات الإدخال والصرف، وفحص النواقص بدقة.
- استخدم الأدوات المتاحة لك دائماً لتنفيذ العمليات أو جلب البيانات الحقيقية من قاعدة البيانات، ولا تخمّن أي أرقام.
- قبل تسجيل حركة صرف (OUT) أو تعديل لصنف، تأكد من معرفة رقم الصنف (item_id) عبر البحث في المخزون أولاً إذا لم يذكره المستخدم.
- أجب باللغة التي يتحدث بها المستخدم وبأسلوب واضح ومنظم.
"""

TOOLS_LIST = [
    add_warehouse,
    add_item,
    record_transaction,
    get_inventory,
    get_low_stock_items,
    get_warehouses,
]

class InventoryAgent:
    def __init__(self, api_key: str | None = None):
        key = api_key or os.getenv("GEMINI_API_KEY")
        if not key or key == "YOUR_API_KEY_HERE":
            raise ValueError("يرجى توفير مفتاح GEMINI_API_KEY صالح في ملف .env أو من خلال الواجهة.")
        
        self.client = genai.Client(api_key=key)
        self.chat = self.client.chats.create(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                tools=TOOLS_LIST,
                temperature=0.2,
            ),
        )

    def ask(self, message: str) -> str:
        response = self.chat.send_message(message)
        return response.text or "تم تنفيذ العملية."
