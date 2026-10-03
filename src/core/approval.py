"""
Sistema de aprovacao para acoes de alto risco no Jarvis v3.
Suporta dashboard Textual e fallback via CLI.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

from loguru import logger

from src.governance.models import RiskLevel

if TYPE_CHECKING:
    from src.cli.dashboard import JarvisDashboard


@dataclass
class ApprovalRequest:
    action_type: str
    target: str
    risk_level: RiskLevel
    reason: str
    context: dict = field(default_factory=dict)


class ApprovalHandler:
    """
    Gerencia aprovacoes de acoes de alto risco.
    Tenta usar o dashboard Textual primeiro; fallback para CLI.
    """

    def __init__(self) -> None:
        self._dashboard_instance: Optional["JarvisDashboard"] = None
        self._use_dashboard = False

    def set_dashboard(self, dashboard: "JarvisDashboard") -> None:
        self._dashboard_instance = dashboard
        self._use_dashboard = True

    async def request_approval(self, request: ApprovalRequest) -> bool:
        logger.warning(
            f"Aprovacao requerida: {request.action_type} em {request.target} "
            f"(risco={request.risk_level.value})"
        )

        if self._use_dashboard and self._dashboard_instance is not None:
            return await self._dashboard_instance.request_approval(
                action_type=request.action_type,
                target=request.target,
                risk_level=request.risk_level,
                reason=request.reason,
            )

        return await self._cli_approval(request)

    async def _cli_approval(self, request: ApprovalRequest) -> bool:
        print(f"\n=== ACAO DE {request.risk_level.value.upper()} RISCO ===")
        print(f"  Acao: {request.action_type}")
        print(f"  Alvo: {request.target}")
        print(f"  Motivo: {request.reason}")
        print("=" * 40)

        response = await asyncio.to_thread(
            lambda: input("Aprovar? (s/N): ").strip().lower()
        )
        return response in ("s", "sim", "y", "yes")

    def __repr__(self) -> str:
        mode = "dashboard" if self._use_dashboard else "CLI"
        return f"ApprovalHandler(mode={mode})"
