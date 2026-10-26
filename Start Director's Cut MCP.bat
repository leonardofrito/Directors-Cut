@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" directors_cut_mcp.py --transport streamable-http
