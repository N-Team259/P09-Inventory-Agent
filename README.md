# 📦 P09 - Autonomous Inventory Tracking Agent

An AI-powered warehouse and inventory management system built with **Google Gemini (2.5 Flash)**, **FastAPI**, **SQLite**, and a responsive **Tailwind CSS** dashboard.

## ✨ Features
- **Natural Language Operations:** Add warehouses, register items, record stock movements (`IN`, `OUT`, `ADJUST`), and query low-stock alerts via conversational AI.
- **Autonomous Tool Calling:** Powered by `google-genai` function calling connected directly to a local SQLite database.
- **Live Executive Dashboard:** Real-time KPI cards and interactive tables for items, low-stock alerts, transaction logs, and warehouses.

## 🚀 Quick Start
1. Create and activate virtual environment: `python3 -m venv .venv && source .venv/bin/activate`
2. Install dependencies: `pip install -r requirements.txt`
3. Create `.env` file and add: `GEMINI_API_KEY=your_api_key_here`
4. Run server: `uvicorn app.server:app --reload --port 8000`
5. Open browser at `http://127.0.0.1:8000`
