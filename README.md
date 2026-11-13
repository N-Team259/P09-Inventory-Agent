# 📦 P09 - Autonomous Inventory Tracking Agent

An AI-powered warehouse and inventory management system built with **Google Gemini (2.5 Flash)**, **FastAPI**, **SQLite**, and a responsive **Tailwind CSS** dashboard.

## 📁 Repository Structure
- `prototype/` — Complete working prototype containing the database layer (`database/`), AI tools (`agent/`), FastAPI server & Tailwind UI (`app/`), and `requirements.txt`.

## 🚀 Quick Start
1. `cd prototype`
2. `python3 -m venv .venv && source .venv/bin/activate`
3. `pip install -r requirements.txt`
4. Add `GEMINI_API_KEY=your_api_key` to `.env`
5. `uvicorn app.server:app --reload --port 8000`
6. Open `http://127.0.0.1:8000`
