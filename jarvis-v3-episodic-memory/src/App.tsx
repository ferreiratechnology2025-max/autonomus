import React, { useState, useMemo, useEffect } from 'react';
import { MemoryEpisode, ActiveTask, PolicyRule, SystemMetrics } from './types';
import {
  sampleEpisodes as initialEpisodes,
  sampleActiveTasks as initialActiveTasks,
  samplePolicyRules as initialPolicyRules,
  initialSystemMetrics,
} from './data/episodes';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import SimilarityMap from './components/SimilarityMap';
import NewAutomationModal from './components/NewAutomationModal';
import EditLogicModal from './components/EditLogicModal';

export default function App() {
  // Navigation State
  const [activeTab, setActiveTab] = useState<'tasks' | 'memory' | 'policy' | 'settings'>('memory');

  // Simulated Database states
  const [episodes, setEpisodes] = useState<MemoryEpisode[]>(initialEpisodes);
  const [activeTasks, setActiveTasks] = useState<ActiveTask[]>(initialActiveTasks);
  const [policyRules, setPolicyRules] = useState<PolicyRule[]>(initialPolicyRules);
  const [metrics, setMetrics] = useState<SystemMetrics>(initialSystemMetrics);

  // Search and Filtering states
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedEpisode, setSelectedEpisode] = useState<MemoryEpisode>(initialEpisodes[0]);

  // Modals / Windows triggers
  const [isOpenNewAutomation, setIsOpenNewAutomation] = useState(false);
  const [isOpenEditLogic, setIsOpenEditLogic] = useState(false);
  const [isTerminalOpen, setIsTerminalOpen] = useState(false);

  // Notifications and system feedback states
  const [sysAlertMessage, setSysAlertMessage] = useState<string | null>(null);
  const [terminalLogs, setTerminalLogs] = useState<string[]>([
    'INF [17:01:15] JARVIS CORE v3.0.4 - Inicialização do cluster EP_CORE_V3 concluída.',
    'INF [17:01:16] Conexão com banco semântico t-SNE estabelecida: 14.229 episódios indexados.',
    'INF [17:01:17] Telemetria operacional de API: NOMINAL.',
    'INF [17:01:20] Monitoramento de threads de automação em execução nos clusters.'
  ]);

  // System Configurations (Modifiable in Settings)
  const [apiStatus, setApiStatus] = useState('NOMINAL');
  const [llmBudget, setLlmBudget] = useState(42);
  const [autoSyncOn, setAutoSyncOn] = useState(true);

  // Automatically select high latency or updated episode matching search
  const filteredEpisodes = useMemo(() => {
    if (!searchQuery.trim()) return episodes;
    return episodes.filter((ep) => {
      const q = searchQuery.toLowerCase();
      return (
        ep.id.toLowerCase().includes(q) ||
        ep.title.toLowerCase().includes(q) ||
        ep.description.toLowerCase().includes(q) ||
        ep.category.toLowerCase().includes(q) ||
        ep.learnedPattern.context.toLowerCase().includes(q)
      );
    });
  }, [episodes, searchQuery]);

  // Ensure selectedEpisode is kept updated with filtered results
  useEffect(() => {
    if (filteredEpisodes.length > 0) {
      const isStillInList = filteredEpisodes.some((ep) => ep.id === selectedEpisode.id);
      if (!isStillInList) {
        setSelectedEpisode(filteredEpisodes[0]);
      }
    }
  }, [filteredEpisodes, selectedEpisode]);

  const addTerminalLog = (message: string) => {
    const time = new Date().toTimeString().split(' ')[0];
    setTerminalLogs((prev) => [...prev, `${message} [${time}]`]);
  };

  // Actions trigger: Promote to Global
  const handlePromoteToGlobal = (episodeId: string) => {
    addTerminalLog(`INF Sincronizando padrão de heurística do episódio ${episodeId} para o cluster global de rede.`);
    setSysAlertMessage(`Sucesso: Heurística do episódio ${episodeId} promovida globalmente de forma segura.`);
    setTimeout(() => setSysAlertMessage(null), 5000);
  };

  // Actions trigger: Flag Anomaly
  const handleFlagAnomaly = (episodeId: string) => {
    addTerminalLog(`WRN Marcando episódio ${episodeId} como anomalia estatística não aprovada.`);
    setEpisodes((prev) =>
      prev.map((ep) => {
        if (ep.id === episodeId) {
          return {
            ...ep,
            riskLevel: 'CRITICAL',
            category: 'UI BREAKAGE',
            learnedPattern: {
              ...ep.learnedPattern,
              successRate: Math.max(0, ep.learnedPattern.successRate - 20),
              reliabilityPercent: Math.max(0, ep.learnedPattern.reliabilityPercent - 15),
            }
          };
        }
        return ep;
      })
    );
    setSysAlertMessage(`Aviso: Episódio ${episodeId} sinalizado como anomalia estrutural de comportamento.`);
    setTimeout(() => setSysAlertMessage(null), 5000);
  };

  // Action: Synchronize current to Core
  const handleSyncToCore = (episodeId: string) => {
    addTerminalLog(`INF Forçando atualização direta de índices de vetor para ${episodeId}.`);
    setSysAlertMessage(`Sucesso: Registro vetorial indexado localmente com as configurações ativas do Jarvis.`);
    setTimeout(() => setSysAlertMessage(null), 5000);
  };

  // Modal handler: Create new Automation
  const handleSaveNewAutomation = (newEp: MemoryEpisode) => {
    setEpisodes((prev) => [newEp, ...prev]);
    setSelectedEpisode(newEp);
    setIsOpenNewAutomation(false);
    
    // Update dashboard metrics
    setMetrics((prev) => ({
      ...prev,
      indexSize: `${(parseFloat(prev.indexSize) + 0.1).toFixed(1)}k Episodes`,
    }));

    addTerminalLog(`INF Registro de nova heurística ${newEp.id} compilado e injetado na árvore t-SNE.`);
    setSysAlertMessage(`Automação gravada: ${newEp.id} já está integrada ao fluxo operacional.`);
    setTimeout(() => setSysAlertMessage(null), 5000);
  };

  // Modal handler: Edit Heuristic Rules logic
  const handleSaveEditedLogic = (updatedEp: MemoryEpisode) => {
    setEpisodes((prev) => prev.map((ep) => (ep.id === updatedEp.id ? updatedEp : ep)));
    setSelectedEpisode(updatedEp);
    setIsOpenEditLogic(false);

    addTerminalLog(`INF Modificação de heurística aplicada para o padrão de resolução ${updatedEp.id}.`);
    setSysAlertMessage(`Sucesso: Lógica e parâmetros regulatórios do episódio ${updatedEp.id} atualizados.`);
    setTimeout(() => setSysAlertMessage(null), 5000);
  };

  // Active Tasks actions toggling
  const handleToggleTaskStatus = (taskId: string) => {
    setActiveTasks((prev) =>
      prev.map((tsk) => {
        if (tsk.id === taskId) {
          const nextStatus = tsk.status === 'running' ? 'paused' : 'running';
          addTerminalLog(`INF Status da tarefa de diagnóstico ${taskId} alterado para ${nextStatus.toUpperCase()}.`);
          return {
            ...tsk,
            status: nextStatus as any,
          };
        }
        return tsk;
      })
    );
  };

  const handleTerminateTask = (taskId: string) => {
    addTerminalLog(`WRN Forçando interrupção abrupta do runner ${taskId} por diretiva do administrador.`);
    setActiveTasks((prev) => prev.filter((tsk) => tsk.id !== taskId));
    setSysAlertMessage(`Alerta: Tarefa em background ${taskId} encerrada e removida das investigações.`);
    setTimeout(() => setSysAlertMessage(null), 5000);
  };

  // Inject sample sandbox tasks to prove fully interactive capabilities
  const handleLaunchDiagnosticsSandbox = () => {
    const sandboxId = `TSK-${Math.floor(Math.random() * 100) + 210}`;
    const newTask: ActiveTask = {
      id: sandboxId,
      title: 'Sandbox Diagnóstico de Redundância v3',
      description: 'Varredura exaustiva de seletores ambíguos para testar tempo de resposta e conexões do sistema.',
      progress: 0,
      status: 'running',
      latency: '24ms',
      severity: 'low',
      startedAt: 'Agora mesmo',
    };

    setActiveTasks((prev) => [newTask, ...prev]);
    addTerminalLog(`INF Executor de testes sandbox ${sandboxId} inicializado pelo administrador.`);
    
    // Simulate active task ticking progression!
    let currentProgress = 0;
    const interval = setInterval(() => {
      currentProgress += 10;
      setActiveTasks((prev) =>
        prev.map((t) => {
          if (t.id === sandboxId) {
            if (currentProgress >= 100) {
              clearInterval(interval);
              addTerminalLog(`INF Teste diagnóstico sandbox ${sandboxId} concluído com 100% de precisão.`);
              return { ...t, progress: 100, status: 'completed' };
            }
            return { ...t, progress: currentProgress };
          }
          return t;
        })
      );
    }, 1500);
  };

  // Settings: Policy toggler
  const handleTogglePolicyRule = (ruleId: string) => {
    setPolicyRules((prev) =>
      prev.map((rule) => {
        if (rule.id === ruleId) {
          const nextStatus = rule.status === 'active' ? 'disabled' : 'active';
          addTerminalLog(`INF Diretiva de proteção de segurança de dados ${ruleId} configurada como ${nextStatus.toUpperCase()}.`);
          return {
            ...rule,
            status: nextStatus,
          };
        }
        return rule;
      })
    );
  };

  const updateMetrics = (queryLength: number) => {
    const calculatedLatency = Math.max(2, 12 - Math.floor(queryLength * 0.7));
    const calculatedAccuracy = searchQuery ? '97.2%' : '94%';
    setMetrics((prev) => ({
      ...prev,
      queryLatency: `${calculatedLatency}ms`,
      retrievalAccuracy: calculatedAccuracy,
    }));
  };

  return (
    <div className="min-h-screen bg-[#050505] text-[#e0e0e0] select-none font-sans relative">
      {/* Dynamic alert bar banner */}
      {sysAlertMessage && (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 bg-[#0c0c0c] border border-[#c5a059] text-[#c5a059] px-6 py-3 font-mono text-xs tracking-wider uppercase animate-bounce shadow-xl shadow-black/80 flex items-center gap-3">
          <span className="material-symbols-outlined text-[16px] animate-spin">sync</span>
          {sysAlertMessage}
          <button onClick={() => setSysAlertMessage(null)} className="ml-4 hover:text-white">
            <span className="material-symbols-outlined text-[14px] font-bold block">close</span>
          </button>
        </div>
      )}

      {/* SideNavBar layout */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={(tab) => {
          setActiveTab(tab);
          addTerminalLog(`INF Transição de visualização do painel administrativo para: ${tab.toUpperCase()}`);
        }}
        onOpenNewAutomation={() => setIsOpenNewAutomation(true)}
      />

      {/* TopNavBar Header */}
      <Header
        uptime={metrics.uptime}
        taskStatus={activeTasks.filter((t) => t.status === 'running').length > 0 ? 'Analizando Redundâncias' : 'Idle'}
        llmBudget={llmBudget}
        apiStatus={apiStatus}
        terminalOpen={isTerminalOpen}
        onToggleTerminal={() => setIsTerminalOpen(!isTerminalOpen)}
      />

      {/* Content layout wrappers */}
      <main className="ml-[260px] mt-16 p-[12px] h-[calc(100vh-64px)] overflow-hidden flex flex-col gap-[12px]">
        {activeTab === 'memory' && (
          <>
            {/* Header section */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-2">
              <div>
                <h2 className="font-serif text-[24px] md:text-[28px] font-normal text-white tracking-tight leading-tight uppercase">
                  Episodic Memory{' '}
                  <span className="text-[#c5a059]/40 font-mono text-[11px] ml-4">EP_CORE_V3</span>
                </h2>
                <p className="font-sans text-[12px] text-[#888888] mt-1">
                  Consultando registros vetoriais compilados e padrões heurísticos do Jarvis V3.
                </p>
              </div>

              {/* Top Row metrics summary blocks */}
              <div className="flex gap-3 mt-2 md:mt-0">
                <div className="bg-[#0c0c0c] border border-[#ffffff10] p-2 px-4 flex flex-col items-center">
                  <span className="font-mono text-[9px] text-[#888888] tracking-wider uppercase">Query Latency</span>
                  <span className="font-mono text-[12px] text-[#c5a059] font-bold">{metrics.queryLatency}</span>
                </div>
                <div className="bg-[#0c0c0c] border border-[#ffffff10] p-2 px-4 flex flex-col items-center">
                  <span className="font-mono text-[9px] text-[#888888] tracking-wider uppercase">Index Size</span>
                  <span className="font-mono text-[12px] text-[#c5a059] font-bold">{metrics.indexSize}</span>
                </div>
                <div className="bg-[#0c0c0c] border border-[#ffffff10] p-2 px-4 flex flex-col items-center">
                  <span className="font-mono text-[9px] text-[#888888] tracking-wider uppercase">Accuracy</span>
                  <span className="font-mono text-[12px] text-[#c5a059] font-bold">{metrics.retrievalAccuracy}</span>
                </div>
              </div>
            </div>

            {/* Semantic Vector Search Bar */}
            <div className="w-full relative group">
              <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-[#c5a059] text-[20px]">
                search
              </span>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  updateMetrics(e.target.value.length);
                  addTerminalLog(`INF Consulta de vetor atualizada para: "${e.target.value}"`);
                }}
                className="w-full bg-[#0c0c0c]/80 backdrop-blur-xs border border-[#ffffff10] py-3.5 pl-12 pr-24 font-mono text-[12px] text-white focus:outline-none focus:border-[#c5a059] focus:ring-1 focus:ring-[#c5a059]/40 transition-all placeholder:text-[#888888]/50"
                placeholder="Busca Semântica: 'failed to click save button' ou 'auth flow disruption'..."
              />
              {searchQuery && (
                <button
                  onClick={() => {
                    setSearchQuery('');
                    updateMetrics(0);
                  }}
                  className="absolute right-20 top-1/2 -translate-y-1/2 text-[#888888] hover:text-white"
                >
                  <span className="material-symbols-outlined text-[18px] block">close</span>
                </button>
              )}
              <div className="absolute right-4 top-1/2 -translate-y-1/2 hidden sm:flex gap-1">
                <kbd className="bg-[#050505] border border-[#ffffff10] px-2 py-0.5 font-mono text-[9px] text-[#888888] rounded">
                  CMD
                </kbd>
                <kbd className="bg-[#050505] border border-[#ffffff10] px-2 py-0.5 font-mono text-[9px] text-[#888888] rounded">
                  K
                </kbd>
              </div>
            </div>

            {/* Recommendations Tags */}
            <div className="flex flex-wrap gap-2 items-center text-xs select-none">
              <span className="text-[#888888] font-mono text-[10px] uppercase tracking-wide">Filtros sugeridos:</span>
              <button
                onClick={() => {
                  setSearchQuery('z-index');
                  updateMetrics(7);
                  addTerminalLog('INF Filtro de pesquisa semântica selecionado: "z-index"');
                }}
                className="px-2 py-0.5 bg-[#0c0c0c] border border-[#ffffff10] hover:border-[#c5a059] font-mono text-[10px] text-[#888888] hover:text-white transition-colors"
              >
                z-index overlay
              </button>
              <button
                onClick={() => {
                  setSearchQuery('loop');
                  updateMetrics(4);
                  addTerminalLog('INF Filtro de pesquisa semântica selecionado: "loop"');
                }}
                className="px-2 py-0.5 bg-[#0c0c0c] border border-[#ffffff10] hover:border-[#c5a059] font-mono text-[10px] text-[#888888] hover:text-white transition-colors"
              >
                infinite hydration loops
              </button>
              <button
                onClick={() => {
                  setSearchQuery('timeout');
                  updateMetrics(7);
                  addTerminalLog('INF Filtro de pesquisa semântica selecionado: "timeout"');
                }}
                className="px-2 py-0.5 bg-[#0c0c0c] border border-[#ffffff10] hover:border-[#c5a059] font-mono text-[10px] text-[#888888] hover:text-white transition-colors"
              >
                latency failures
              </button>
              <button
                onClick={() => {
                  setSearchQuery('shadow DOM');
                  updateMetrics(10);
                  addTerminalLog('INF Filtro de pesquisa semântica selecionado: "shadow DOM"');
                }}
                className="px-2 py-0.5 bg-[#0c0c0c] border border-[#ffffff10] hover:border-[#c5a059] font-mono text-[10px] text-[#888888] hover:text-white transition-colors"
              >
                ambiguous DOM paths
              </button>
            </div>

            {/* Dashboard grid panel */}
            <div className="flex-1 grid grid-cols-12 gap-[12px] overflow-hidden min-h-0">
              {/* Col 1: Recent Episodes Feed */}
              <div className="col-span-12 lg:col-span-3 flex flex-col gap-2 overflow-y-auto custom-scrollbar pr-1">
                <div className="flex justify-between items-center select-none">
                  <h3 className="font-mono text-[10px] font-bold text-[#888888] tracking-wider uppercase">
                    Recent Episodes ({filteredEpisodes.length})
                  </h3>
                  <button
                    onClick={() => {
                      setEpisodes(initialEpisodes);
                      setSearchQuery('');
                      addTerminalLog('INF Redefinição completa da base local de episódios executada.');
                    }}
                    title="Redefinir Filtros / Base"
                    className="p-1 hover:text-[#c5a059] text-[#888888] transition-colors"
                  >
                    <span className="material-symbols-outlined text-[16px] block">refresh</span>
                  </button>
                </div>

                {filteredEpisodes.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-10 bg-[#0c0c0c]/50 border border-dashed border-[#ffffff10] p-4 text-center">
                    <span className="material-symbols-outlined text-[28px] text-[#888888] mb-2 animate-pulse">
                      error
                    </span>
                    <p className="font-mono text-[10px] text-[#888888] uppercase font-bold">Nenhum vetor localizado</p>
                    <p className="text-xs text-[#888888]/60 mt-1 leading-relaxed">
                      Sua análise de busca semântica para "{searchQuery}" retornou 0 instâncias.
                    </p>
                  </div>
                ) : (
                  <div className="flex flex-col gap-2">
                    {filteredEpisodes.map((ep) => {
                      const isSelected = selectedEpisode.id === ep.id;
                      return (
                        <div
                          key={ep.id}
                          onClick={() => setSelectedEpisode(ep)}
                          className={`card-hover-effect p-3 flex flex-col gap-1 cursor-pointer border relative select-none ${
                            isSelected
                              ? 'bg-[#141414] border-l-2 border-l-[#c5a059] border-y-[#ffffff10] border-r-[#ffffff10]'
                              : 'bg-[#0c0c0c]/90 border-[#ffffff10]'
                          }`}
                        >
                          <div className="flex justify-between items-start">
                            <span className={`font-mono text-[11px] font-bold ${isSelected ? 'text-[#c5a059]' : 'text-[#888888]'}`}>
                              ID: {ep.id}
                            </span>
                            <div className="flex items-center gap-1">
                              {ep.riskLevel === 'CRITICAL' ? (
                                <div className="flex items-center gap-1 px-1.5 py-0.5 bg-rose-950/20 border-l border-rose-500">
                                  <span className="material-symbols-outlined text-[10px] text-rose-500 font-bold block animate-pulse">
                                    priority_high
                                  </span>
                                  <span className="font-mono text-[9px] text-rose-400 uppercase font-bold tracking-wider">
                                    CRITICAL
                                  </span>
                                </div>
                              ) : ep.riskLevel === 'WARNING' ? (
                                <div className="flex items-center gap-1 px-1.5 py-0.5 bg-amber-955/20 border-l border-amber-500">
                                  <span className="font-mono text-[9px] text-amber-500 uppercase font-bold tracking-wider">
                                    WARNING
                                  </span>
                                </div>
                              ) : (
                                <div className="flex items-center gap-1 px-1.5 py-0.5 bg-[#c5a059]/10 border-l border-[#c5a059]">
                                  <span className="font-mono text-[9px] text-[#c5a059] uppercase font-bold tracking-wider">
                                    SAFE
                                  </span>
                                </div>
                              )}
                            </div>
                          </div>
                          
                          <p className={`font-sans text-[13px] leading-snug line-clamp-2 mt-1 ${isSelected ? 'text-white' : 'text-[#a0a0a0] hover:text-white'}`}>
                            {ep.title}
                          </p>
                          
                          <div className="flex justify-between items-center mt-2.5">
                            <span className="font-mono text-[10px] text-[#888888]/60">{ep.timestamp}</span>
                            <span className={`material-symbols-outlined text-[14px] transition-transform ${isSelected ? 'text-[#c5a059] translate-x-0.5' : 'text-[#888888]/40'}`}>
                              arrow_forward_ios
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Col 2: Dimensional Projection Similarity Map */}
              <SimilarityMap
                episodes={episodes}
                selectedEpisode={selectedEpisode}
                onSelectEpisode={setSelectedEpisode}
              />

              {/* Col 3: Details Episodic Deep Dive Panel */}
              <div className="col-span-12 lg:col-span-4 flex flex-col gap-2 overflow-y-auto custom-scrollbar pr-1">
                <h3 className="font-mono text-[10px] font-bold text-[#888888] tracking-wider uppercase select-none">
                  Episode Deep Dive
                </h3>

                <div className="bg-[#0c0c0c]/95 border border-[#ffffff10] p-4 flex flex-col gap-4 relative overflow-hidden">
                  {/* Decorative background overlay */}
                  <div className="absolute inset-0 bg-[#050505]/20 pointer-events-none" />

                  {/* Similarity Metrics header */}
                  <div className="flex justify-between items-center relative z-10 border-b border-[#ffffff10] pb-3">
                    <div>
                      <p className="font-mono text-[9px] font-bold text-[#888888] uppercase tracking-wider">Similarity Score</p>
                      <p className="font-serif text-[22px] font-normal text-[#c5a059] leading-none mt-1">
                        {selectedEpisode.similarityScore}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="font-mono text-[9px] font-bold text-[#888888] uppercase tracking-wider">Retrieval Rank</p>
                      <p className="font-sans text-[15px] font-bold text-white mt-1">
                        {selectedEpisode.retrievalRank}
                      </p>
                    </div>
                  </div>

                  {/* Summary Area */}
                  <div className="relative z-10">
                    <span className="font-mono text-[9px] font-bold text-[#888888] uppercase tracking-wider">Fato do Incidente</span>
                    <p className="text-xs text-[#e0e0e0] leading-relaxed mt-1 bg-[#080808] p-2.5 border border-[#ffffff10]">
                      {selectedEpisode.description}
                    </p>
                  </div>

                  {/* Visual Context (Before & After screenshot blocks matching images) */}
                  <div className="space-y-1.5 relative z-10">
                    <p className="font-mono text-[9px] font-bold text-[#888888] uppercase tracking-wider">
                      Visual Context (UIA Snapshot)
                    </p>
                    <div className="grid grid-cols-2 gap-2">
                      <div className="relative overflow-hidden group border border-[#ffffff10] bg-[#050505] h-[100px]">
                        <img
                          alt="Code Comparison Before"
                          referrerPolicy="no-referrer"
                          className="w-full h-full object-cover transition-all grayscale opacity-70 group-hover:grayscale-0 group-hover:opacity-100 duration-500 cursor-zoom-in"
                          src={selectedEpisode.beforeImage}
                        />
                        <div className="absolute top-1 left-2 bg-[#050505]/90 px-1.5 py-0.5 font-mono text-[8px] text-white border border-[#ffffff10] font-bold">
                          BEFORE
                        </div>
                      </div>
                      <div className="relative overflow-hidden group border border-[#ffffff10] bg-[#050505] h-[100px]">
                        <img
                          alt="Code Comparison After"
                          referrerPolicy="no-referrer"
                          className="w-full h-full object-cover transition-all hover:scale-105 duration-700 cursor-zoom-in"
                          src={selectedEpisode.afterImage}
                        />
                        <div className="absolute top-1 left-2 bg-[#c5a059] px-1.5 py-0.5 font-mono text-[8px] text-black border border-[#ffffff10] font-bold">
                          AFTER
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* State Comparison (OCR) */}
                  <div className="space-y-1.5 relative z-10">
                    <p className="font-mono text-[9px] font-bold text-[#888888] uppercase tracking-wider">
                      State Comparison (OCR Diff)
                    </p>
                    <div className="bg-[#050505] p-2.5 border border-[#ffffff10] font-mono text-[11px] leading-relaxed select-text">
                      {selectedEpisode.stateDiff.map((line, idx) => (
                        <div
                          key={idx}
                          className={`flex items-start gap-2 ${
                            line.type === 'remove'
                              ? 'text-rose-400 bg-rose-955/20'
                              : line.type === 'add'
                              ? 'text-[#56e5a9] bg-emerald-955/15'
                              : 'text-[#888888]/60'
                          }`}
                        >
                          <span className="opacity-40 select-none w-6">{line.lineNum}</span>
                          <span className="select-none w-3">{line.type === 'remove' ? '-' : line.type === 'add' ? '+' : ' '}</span>
                          <span className="flex-1 overflow-x-auto whitespace-pre">{line.content}</span>
                        </div>
                      ))}
                      <div className="text-[#888888] pt-2 border-t border-[#ffffff10] mt-2 italic text-[10px] leading-snug">
                        {selectedEpisode.logicComment}
                      </div>
                    </div>
                  </div>

                  {/* Learned Pattern Rule Indicator block */}
                  <div className="bg-[#c5a059]/5 border-l-2 border-[#c5a059] p-3 relative z-10 flex flex-col gap-3">
                    <div className="flex justify-between items-center border-b border-[#c5a059]/20 pb-2">
                      <p className="font-mono text-[10px] font-bold text-[#c5a059] flex items-center gap-1.5">
                        <span className="material-symbols-outlined text-[14px]">psychology</span>
                        DECISION PATTERN
                      </p>
                      <div className="flex flex-wrap gap-1">
                        <span className="px-1.5 py-0.5 bg-[#c5a059]/10 border border-[#c5a059]/30 text-[8px] font-mono text-[#c5a059] uppercase">
                          OBS: {selectedEpisode.learnedPattern.observedAgo}
                        </span>
                        <span className="px-1.5 py-0.5 bg-white/5 border border-white/10 text-[8px] font-mono text-white uppercase">
                          SUC: {selectedEpisode.learnedPattern.successRate}%
                        </span>
                      </div>
                    </div>

                    <div className="space-y-2.5">
                      <div className="flex gap-2">
                        <span className="material-symbols-outlined text-[#888888] text-[16px] mt-0.5 block">radar</span>
                        <div>
                          <p className="text-[8px] font-mono text-[#888888]/75 uppercase tracking-wide">Contexto</p>
                          <p className="font-sans text-[11px] text-[#e0e0e0] leading-relaxed">
                            {selectedEpisode.learnedPattern.context}
                          </p>
                        </div>
                      </div>

                      <div className="flex gap-2">
                        <span className="material-symbols-outlined text-[#888888] text-[16px] mt-0.5 block">hub</span>
                        <div>
                          <p className="text-[8px] font-mono text-[#888888]/75 uppercase tracking-wide">Fórmula de Heurística</p>
                          <p className="font-sans text-[11px] text-[#e0e0e0] leading-relaxed italic">
                            {selectedEpisode.learnedPattern.heuristic}
                          </p>
                        </div>
                      </div>

                      <div className="flex gap-2">
                        <span className="material-symbols-outlined text-[#888888] text-[16px] mt-0.5 block">verified</span>
                        <div>
                          <p className="text-[8px] font-mono text-[#888888]/75 uppercase tracking-wide font-bold">Reliability</p>
                          <div className="flex items-center gap-3 mt-0.5">
                            <p className="font-sans text-[11px] font-bold text-[#e0e0e0]">
                              {selectedEpisode.learnedPattern.reliabilityLevel}
                            </p>
                            <div className="flex-1 h-1 bg-[#141414] rounded-full w-24 overflow-hidden relative">
                              <div
                                className="bg-[#c5a059] h-full rounded-full transition-all duration-1000"
                                style={{ width: `${selectedEpisode.learnedPattern.reliabilityPercent}%` }}
                              />
                            </div>
                            <span className="font-mono text-[9px] text-[#c5a059]">
                              {selectedEpisode.learnedPattern.reliabilityPercent}%
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Integrated actions under rules */}
                    <div className="grid grid-cols-2 gap-2 mt-2 pt-2 border-t border-[#ffffff10]">
                      <button
                        onClick={() => handlePromoteToGlobal(selectedEpisode.id)}
                        className="glitch-hover py-1 bg-[#c5a059] hover:bg-[#d4b57a] text-black font-mono text-[9px] font-bold uppercase tracking-wider transition-all duration-300"
                      >
                        Promote to Global
                      </button>
                      <button
                        onClick={() => setIsOpenEditLogic(true)}
                        className="py-1 border border-[#c5a059]/50 text-[#c5a059] hover:bg-[#c5a059]/5 font-mono text-[9px] font-bold uppercase tracking-wider transition-all duration-300"
                      >
                        Edit Logic
                      </button>
                    </div>
                  </div>

                  {/* Bottom secondary controls */}
                  <div className="flex gap-2 mt-2 pt-3 border-t border-[#ffffff10] relative z-10 select-none">
                    <button
                      onClick={() => handleSyncToCore(selectedEpisode.id)}
                      className="glitch-hover flex-1 py-1.5 bg-[#141414] border border-[#ffffff10] text-[#e0e0e0] font-mono text-[10px] uppercase font-bold tracking-wider hover:bg-[#c5a059] hover:text-black transition-all"
                    >
                      SYNC TO CORE
                    </button>
                    <button
                      onClick={() => handleFlagAnomaly(selectedEpisode.id)}
                      className="flex-1 py-1.5 border border-[#ffffff10] text-[#888888] font-mono text-[10px] uppercase font-bold tracking-wider hover:bg-rose-955/20 hover:text-rose-400 hover:border-rose-700/50 transition-all text-center"
                    >
                      FLAG ANOMALY
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </>
        )}

        {/* ACTIVE TASKS View */}
        {activeTab === 'tasks' && (
          <div className="flex-1 flex flex-col gap-4 overflow-y-auto custom-scrollbar pr-1">
            <div className="flex justify-between items-end border-b border-[#ffffff10] pb-3 select-none">
              <div>
                <h2 className="font-serif text-[24px] font-normal text-white tracking-tight uppercase">
                  Active System Tasks
                </h2>
                <p className="text-xs text-[#888888] mt-1">
                  Gerenciando runners de automação paralelos executados nos clusters Jarvis CORE.
                </p>
              </div>
              <button
                onClick={handleLaunchDiagnosticsSandbox}
                className="py-2 px-4 bg-[#c5a059] text-black font-mono text-[10px] font-bold uppercase tracking-wider hover:bg-[#d4b57a] active:scale-95 transition-all w-fit"
              >
                Injetar Sandbox Diagnóstico
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 select-none">
              {activeTasks.length === 0 ? (
                <div className="col-span-2 py-12 text-center bg-[#0c0c0c] border border-[#ffffff10]">
                  <span className="material-symbols-outlined text-[36px] text-[#888888]/40 mb-2">dashboard_customize</span>
                  <p className="font-mono text-xs uppercase font-bold text-[#888888]/70">Sem Tarefas Ativas</p>
                  <p className="text-xs text-[#888888]/50 mt-1">Nenhum runner em background processando heurísticas.</p>
                </div>
              ) : (
                activeTasks.map((t) => (
                  <div key={t.id} className="bg-[#0c0c0c]/90 border border-[#ffffff10] p-4 flex flex-col gap-3 relative">
                    <div className="flex justify-between items-start">
                      <div>
                        <span className="px-2 py-0.5 bg-[#141414] border border-[#ffffff10] text-[#c5a059] font-mono text-[9px] uppercase font-bold tracking-wide rounded">
                          {t.id}
                        </span>
                        <h4 className="text-xs font-bold text-white mt-1.5">{t.title}</h4>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono text-[8px] text-[#888888]/80">LATENCY: {t.latency}</span>
                        {t.status === 'running' ? (
                          <span className="w-2 h-2 bg-[#c5a059] rounded-full animate-ping" />
                        ) : (
                          <span className="w-2 h-2 bg-amber-400 rounded-full" />
                        )}
                      </div>
                    </div>

                    <p className="text-xs text-[#888888] leading-relaxed">{t.description}</p>

                    <div>
                      <div className="flex justify-between items-center text-[10px] font-mono text-[#888888] mb-1">
                        <span>Progresso do Processo</span>
                        <span>{t.progress}%</span>
                      </div>
                      <div className="h-1.5 bg-[#050505] border border-[#ffffff10] w-full rounded-full overflow-hidden">
                        <div
                          className={`h-full transition-all duration-500 rounded-full ${
                            t.status === 'paused' ? 'bg-amber-400' : 'bg-[#c5a059]'
                          }`}
                          style={{ width: `${t.progress}%` }}
                        />
                      </div>
                    </div>

                    <div className="flex justify-between items-center mt-2 pt-3 border-t border-[#ffffff10] text-xs">
                      <span className="font-mono text-[9px] text-[#888888]/60 uppercase tracking-widest">
                        Started: {t.startedAt}
                      </span>
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleToggleTaskStatus(t.id)}
                          className={`py-1 px-3 font-mono text-[9px] uppercase font-bold tracking-wider transition-all border ${
                            t.status === 'running'
                              ? 'border-amber-500/50 text-amber-500 hover:bg-amber-500/5'
                              : 'border-[#c5a059]/50 text-[#c5a059] hover:bg-[#c5a059]/5'
                          }`}
                        >
                          {t.status === 'running' ? 'Pausar' : 'Processar'}
                        </button>
                        <button
                          onClick={() => handleTerminateTask(t.id)}
                          className="py-1 px-3 border border-rose-900/60 text-rose-400 hover:bg-rose-955/20 font-mono text-[9px] uppercase font-bold tracking-wider transition-all"
                        >
                          Encerrar
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* POLICY Directives Ledger View */}
        {activeTab === 'policy' && (
          <div className="flex-1 flex flex-col gap-4 overflow-y-auto custom-scrollbar pr-1 select-none">
            <div className="border-b border-[#ffffff10] pb-3">
              <h2 className="font-serif text-[24px] font-normal text-white uppercase">
                Policy Directives Ledger
              </h2>
              <p className="text-xs text-[#888888] mt-1">
                Regras regulatórias de mitigação estática. Automações criadas herdam estas diretivas antes da execução.
              </p>
            </div>

            <div className="flex flex-col gap-3">
              {policyRules.map((rule) => {
                const isActive = rule.status === 'active';
                return (
                  <div key={rule.id} className="bg-[#0c0c0c]/90 border border-[#ffffff10] p-4 flex flex-col gap-2 relative">
                    <div className="absolute top-0 right-0 p-3 flex gap-2">
                      <span className="font-mono text-[8px] text-[#888888]/60 mt-1 uppercase">Atualizado: {rule.lastModified}</span>
                      <button
                        onClick={() => handleTogglePolicyRule(rule.id)}
                        className={`text-xs px-2.5 py-0.5 font-mono uppercase font-black rounded ${
                          isActive ? 'bg-[#c5a059]/10 text-[#c5a059] border border-[#c5a059]/30' : 'bg-[#141414] text-[#888888]'
                        }`}
                      >
                        {rule.status}
                      </button>
                    </div>

                    <div>
                      <span className="font-mono text-[9px] text-[#c5a059] font-bold block">{rule.id}</span>
                      <h4 className="font-sans text-sm font-bold text-white mt-1 pr-16">{rule.title}</h4>
                      <p className="font-mono text-[10px] text-[#888888]/60 mt-0.5 uppercase tracking-wide">
                        Escopo: {rule.scope}
                      </p>
                    </div>

                    <p className="text-xs text-[#888888] leading-relaxed mt-2 bg-[#050505] p-2.5 border border-[#ffffff10]">
                      <span className="font-mono text-[9px] text-[#c5a059] uppercase tracking-wider block font-bold mb-1"> Diretriz de Segurança</span>
                      {rule.statement}
                    </p>

                    {rule.riskMitigation && (
                      <div className="font-sans text-xs text-[#c5a059] bg-[#c5a059]/5 border-l border-[#c5a059] p-2 mt-1 leading-snug">
                        <span className="font-mono text-[9px] font-black uppercase tracking-widest block mb-0.5">Mitigação do Risco</span>
                        {rule.riskMitigation}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* SETTINGS Configuration Panel View */}
        {activeTab === 'settings' && (
          <div className="flex-1 flex flex-col gap-4 overflow-y-auto custom-scrollbar pr-1 max-w-2xl select-none">
            <div className="border-b border-[#ffffff10] pb-3">
              <h2 className="font-serif text-[24px] font-normal text-white uppercase">
                System Administration
              </h2>
              <p className="text-xs text-[#888888] mt-1">
                Ajuste e controle operacional do núcleo cibernético Jarvis v3.
              </p>
            </div>

            {/* Config block 1 */}
            <div className="bg-[#0c0c0c] border border-[#ffffff10] p-4 flex flex-col gap-4">
              <h3 className="text-[#c5a059] text-[12px] font-mono uppercase font-black tracking-wider border-b border-[#ffffff10] pb-1.5">
                Configurações Quânticas Globais
              </h3>

              {/* Slider 1: LLM usage limits */}
              <div>
                <div className="flex justify-between font-mono text-[11px] text-[#888888] mb-1.5 uppercase font-bold">
                  <span>Limite de Alocação de Token LLM</span>
                  <span className="text-[#c5a059]">{llmBudget}%</span>
                </div>
                <input
                  type="range"
                  min="10"
                  max="100"
                  value={llmBudget}
                  onChange={(e) => {
                    const nextVal = Number(e.target.value);
                    setLlmBudget(nextVal);
                    addTerminalLog(`INF Orçamento máximo projetado de tokens atualizado para: ${nextVal}%`);
                  }}
                  className="w-full accent-[#c5a059]"
                />
                <span className="text-[10px] text-[#888888]/60 mt-1 block">
                  Regula o limite de buffers paralelos de processamento que podem rodar simultaneamente nos runners.
                </span>
              </div>

              {/* Select area: System level target */}
              <div>
                <label className="block font-mono text-[11px] text-[#888888] mb-1.5 uppercase font-bold">
                  Target API Estado da Rede
                </label>
                <select
                  value={apiStatus}
                  onChange={(e) => {
                    const nextVal = e.target.value;
                    setApiStatus(nextVal);
                    addTerminalLog(`WRN Flag de status operacional geral de rede reconfigurado para: ${nextVal}`);
                  }}
                  className="w-full bg-[#050505] border border-[#ffffff10] text-white text-xs p-2.5 focus:outline-none focus:border-[#c5a059]"
                >
                  <option value="NOMINAL">NOMINAL (Operando sob regras de normalidade)</option>
                  <option value="DEGRADADA">DEGRADADA (Alerta de restrição de latência AWS)</option>
                  <option value="OFFLINE">OFFLINE (Pausa completa em todas as automações)</option>
                </select>
              </div>

              {/* Toggle switch selectors */}
              <div className="flex justify-between items-center bg-[#050505] p-3 border border-[#ffffff10] mt-2">
                <div>
                  <span className="font-sans text-xs font-bold text-white block">Auto-Sync Core</span>
                  <span className="text-[10px] text-[#888888] leading-relaxed block mt-0.5">
                    Modificar heurísticas locais injetando modificações no núcleo t-SNE de memórias de forma automatizada.
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setAutoSyncOn(!autoSyncOn);
                    addTerminalLog(`INF Auto-Sync de memórias configurado como: ${(!autoSyncOn).toString().toUpperCase()}`);
                  }}
                  className={`px-3 py-1 font-mono text-[10px] uppercase font-bold tracking-wider rounded border ${
                    autoSyncOn ? 'bg-[#c5a059]/10 text-[#c5a059] border-[#c5a059]/30' : 'bg-[#141414] text-[#888888] border-[#ffffff10]'
                  }`}
                >
                  {autoSyncOn ? 'Ligado' : 'Desligado'}
                </button>
              </div>
            </div>

            {/* Simulated Workspace logs */}
            <div className="bg-[#0c0c0c] border border-[#ffffff10] p-4 flex flex-col gap-2 font-mono text-[10px]">
              <h3 className="text-[#c5a059] text-[12px] uppercase font-black border-b border-[#ffffff10] pb-1.5 mb-1.5">
                Workspace Identity Credentials
              </h3>
              <p className="flex justify-between"><span className="text-[#888888]/60">ADMINISTRADOR:</span> <span>erteafghj996@gmail.com</span></p>
              <p className="flex justify-between"><span className="text-[#888888]/60">DEVELOPMENT HUB:</span> <span>us-west1.run.app</span></p>
              <p className="flex justify-between"><span className="text-[#888888]/60">NÚCLEO REGULATÓRIO:</span> <span>Jarvis EP-V3-stable.build-2026</span></p>
            </div>
          </div>
        )}
      </main>

      {/* Persistent Terminal Developer Console logs at bottom drawer */}
      {isTerminalOpen && (
        <div className="fixed bottom-10 right-4 left-[272px] h-48 bg-[#0c0c0c] border-2 border-[#ffffff10] border-t-[#c5a059] border-t-4 z-40 p-3 shadow-2xl flex flex-col">
          <div className="flex justify-between items-center border-b border-[#ffffff10] pb-1.5 mb-2 select-none">
            <span className="font-mono text-[10px] font-bold text-[#c5a059] uppercase tracking-wider flex items-center gap-2">
              <span className="w-1.5 h-1.5 bg-[#c5a059] rounded-full animate-ping" />
              Diagnóstico de Eventos CORE_V3 stdout
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setTerminalLogs([])}
                className="hover:text-white font-mono text-[9px] uppercase tracking-wide text-[#888888]"
              >
                Limpar Logs
              </button>
              <button onClick={() => setIsTerminalOpen(false)} className="text-[#888888] hover:text-white">
                <span className="material-symbols-outlined text-[16px] block font-bold">close</span>
              </button>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto font-mono text-[11px] leading-relaxed text-[#888888] font-medium p-1 bg-black/40 custom-scrollbar select-text selection:bg-[#c5a059]/20">
            {terminalLogs.map((log, idx) => {
              let logStyle = 'text-[#888888]';
              if (log.includes('WRN')) logStyle = 'text-amber-400 font-bold';
              else if (log.includes('ERR')) logStyle = 'text-rose-500 font-bold';
              else if (log.includes('INF')) logStyle = 'text-[#c5a059]/90';
              return (
                <div key={idx} className={`${logStyle} py-0.5 hover:bg-white/5`}>
                  {log}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Footer bar matching original HTML design */}
      <footer className="fixed bottom-0 right-0 left-[260px] flex justify-between items-center px-6 py-2.5 z-30 bg-[#0c0c0c]/95 backdrop-blur-sm border-t border-[#ffffff10] select-none text-[10px] font-mono">
        <span className="font-bold text-[#888888]">© 2026 CYBERNETIC INDUSTRIAL SYSTEMS</span>
        <div className="flex gap-6">
          <a
            onClick={() => {
              addTerminalLog('ERR EMERGENCY STOP SIGNALS ACTIVATED!!! All automations paused.');
              setSysAlertMessage('EMERGENCY STOP COMPILER ACTIVE! Tópicos parados com segurança.');
              setApiStatus('OFFLINE');
              setTimeout(() => setSysAlertMessage(null), 5000);
            }}
            className="text-[#888888] hover:text-rose-500 transition-colors uppercase font-bold cursor-pointer"
          >
            Emergency Stop
          </a>
          <a
            onClick={() => setIsTerminalOpen(true)}
            className="text-[#888888] hover:text-[#c5a059] transition-colors uppercase font-bold cursor-pointer"
          >
            System Logs
          </a>
          <span className="text-[#888888]">
            API Status:{' '}
            <span
              className={`font-black ${
                apiStatus === 'NOMINAL'
                  ? 'text-[#c5a059]'
                  : apiStatus === 'DEGRADADA'
                  ? 'text-amber-400'
                  : 'text-rose-500'
              }`}
            >
              {apiStatus}
            </span>
          </span>
        </div>
      </footer>

      {/* Dialog: Create New Automation Heuristic rule */}
      {isOpenNewAutomation && (
        <NewAutomationModal
          onClose={() => setIsOpenNewAutomation(false)}
          onSave={handleSaveNewAutomation}
        />
      )}

      {/* Dialog: Edit logic details */}
      {isOpenEditLogic && (
        <EditLogicModal
          episode={selectedEpisode}
          onClose={() => setIsOpenEditLogic(false)}
          onSave={handleSaveEditedLogic}
        />
      )}
    </div>
  );
}
