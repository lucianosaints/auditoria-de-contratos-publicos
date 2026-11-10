"""Entrada stdio para clientes MCP externos; não carrega .env ou provedor de IA."""
import os
import site
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
site.addsitedir(str(ROOT / '.venv' / ('Lib/site-packages' if os.name == 'nt' else f'lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages')))

if __name__ == '__main__':
    from src.mcp_server import server
    server.run(transport='stdio')
