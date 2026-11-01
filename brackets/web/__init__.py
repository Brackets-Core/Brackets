"""
Submódulo Web de Brackets: Servidor local y frontend PWA.
"""

from brackets.web.service import BracketsWebService
from brackets.web.server import run_web_server

__all__ = ["BracketsWebService", "run_web_server"]
