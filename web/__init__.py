"""
Submódulo Web de Brackets: Servidor local y frontend PWA.
"""

from web.service import BracketsWebService
from web.server import run_web_server

__all__ = ["BracketsWebService", "run_web_server"]
