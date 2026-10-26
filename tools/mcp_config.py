"""Print portable MCP host configuration using this checkout's absolute paths."""
import json
import sys
from pathlib import Path

root=Path(__file__).resolve().parent.parent
print(json.dumps({'mcpServers':{'directors-cut':{'command':str(Path(sys.executable).resolve()),'args':[str(root/'directors_cut_mcp.py')],
                                            'env':{'DIRECTORS_CUT_URL':'http://127.0.0.1:7860'}}}},indent=2))
