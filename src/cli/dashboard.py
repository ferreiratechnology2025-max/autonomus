"""
Dashboard Textual para Jarvis v3
Exibe health checks, budget, fila de tarefas e gerencia aprovação de ações HIGH/CRITICAL
"""

import asyncio
from typing import Optional

from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.widgets import Header, Footer, Log, DataTable, Label, Button
from textual.containers import Container, Horizontal, Vertical

from src.governance.models import RiskLevel


CSS = """
.status-box {
    border: solid $primary;
    padding: 1;
    margin: 1;
    height: 5;
}
.risk-panel {
    border: solid $error;
    background: $error 20%;
    padding: 1;
    margin: 1;
    height: 8;
}
.actions-table {
    height: 10;
    margin: 1;
}
.approve-btn {
    background: $success 60%;
    width: 20;
}
.deny-btn {
    background: $error 60%;
    width: 20;
}
Log {
    height: 10;
    margin: 1;
}
"""


class JarvisDashboard(App):
    """Aplicação principal do dashboard Jarvis v3"""

    CSS = CSS

    health_text = reactive("")
    budget_text = reactive("")
    queue_text = reactive("")

    def __init__(self):
        super().__init__()
        self._current_request = None
        self._approval_future = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Horizontal(
                Container(Label(self.health_text or "Health: --"), id="health", classes="status-box"),
                Container(Label(self.budget_text or "Budget: --"), id="budget", classes="status-box"),
                Container(Label(self.queue_text or "Queue: --"), id="queue", classes="status-box"),
            ),
            Container(
                Label("ACAO DE RISCO AGUARDANDO APROVACAO", id="risk-title"),
                Label("Nenhuma acao pendente", id="risk-detail"),
                classes="risk-panel",
            ),
            DataTable(id="actions-table", classes="actions-table"),
            Horizontal(
                Button("Aprovar", variant="primary", id="approve", classes="approve-btn", disabled=True),
                Button("Negar", variant="error", id="deny", classes="deny-btn", disabled=True),
            ),
            Log(id="log"),
        )
        yield Footer()

    async def on_mount(self):
        table = self.query_one("#actions-table")
        table.add_columns("Horario", "Acao", "Alvo", "Risco")
        self.log_event("Dashboard iniciado. Aguardando tarefas...")

    def log_event(self, message: str):
        log = self.query_one("#log")
        log.write_line(f"[{asyncio.get_event_loop().time():.1f}] {message}")

    async def request_approval(self, action_type: str, target: str, risk_level: RiskLevel, reason: str) -> bool:
        """
        Solicita aprovacao do usuario para uma acao de alto risco.
        Retorna True se aprovado, False se negado.
        """
        self._approval_future = asyncio.Future()

        self.query_one("#risk-title").update(f"RISCO {risk_level.value.upper()} - ACAO REQUER APROVACAO")
        self.query_one("#risk-detail").update(f"Acão: {action_type}\nAlvo: {target}\nMotivo: {reason}")

        approve_btn = self.query_one("#approve")
        deny_btn = self.query_one("#deny")
        approve_btn.disabled = False
        deny_btn.disabled = False

        result = await self._approval_future

        self.query_one("#risk-title").update("ACAO DE RISCO AGUARDANDO APROVACAO")
        self.query_one("#risk-detail").update("Nenhuma acao pendente")
        approve_btn.disabled = True
        deny_btn.disabled = True

        self.log_event(f"Acao {'APROVADA' if result else 'NEGADA'}: {action_type} em {target}")
        return result

    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "approve" and self._approval_future and not self._approval_future.done():
            self._approval_future.set_result(True)
        elif event.button.id == "deny" and self._approval_future and not self._approval_future.done():
            self._approval_future.set_result(False)

    def update_stats(self, health: str, budget: float, queue_size: int):
        self.health_text = f"Saude: {health}"
        self.budget_text = f"Budget: ${budget:.2f} / $2.00"
        self.queue_text = f"Fila: {queue_size} tarefas"

    def add_action_log(self, timestamp: str, action: str, target: str, risk: str):
        table = self.query_one("#actions-table")
        self.call_from_thread(table.add_row, timestamp, action, target, risk)


def launch_dashboard():
    """Inicia o dashboard Textual com orquestrador em background"""
    from src.core.config import load_settings
    from src.core.approval import ApprovalHandler
    from src.core.orchestrator import JarvisOrchestrator
    import threading
    import asyncio

    approval_handler = ApprovalHandler()
    dashboard = JarvisDashboard()
    approval_handler.set_dashboard(dashboard)

    async def run_orchestrator():
        settings = load_settings()
        orchestrator = JarvisOrchestrator(settings, approval_handler=approval_handler)
        await orchestrator.initialize()
        health = await orchestrator.health_check()
        dashboard.update_stats(health["status"], 0.0, 0)
        while True:
            await asyncio.sleep(1)

    loop = asyncio.new_event_loop()

    def run_async():
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_orchestrator())

    orch_thread = threading.Thread(target=run_async, daemon=True)
    orch_thread.start()
    dashboard.run()
