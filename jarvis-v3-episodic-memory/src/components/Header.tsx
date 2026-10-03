import React, { useState, useEffect } from 'react';

interface HeaderProps {
  uptime: string;
  taskStatus: string;
  llmBudget: number;
  apiStatus: string;
  onToggleTerminal?: () => void;
  terminalOpen?: boolean;
}

export default function Header({
  uptime,
  taskStatus,
  llmBudget,
  apiStatus,
  onToggleTerminalStyle,
  onToggleTerminal,
  terminalOpen,
}: HeaderProps & { onToggleTerminalStyle?: () => void }) {
  const [showNotifications, setShowNotifications] = useState(false);
  const [ticks, setTicks] = useState(0);

  // Live timer tick for high fidelity!
  useEffect(() => {
    const timer = setInterval(() => {
      setTicks((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const formatUptimeWithLiveSeconds = (originalUptime: string) => {
    const hours = Math.floor(ticks / 3600);
    const mins = Math.floor((ticks % 3600) / 60);
    const secs = ticks % 60;
    
    // e.g. "14d 2h + Live increments"
    if (secs === 0 && mins === 0 && hours === 0) return originalUptime;
    
    let suffix = ' ';
    if (hours > 0) suffix += `${hours}h `;
    if (mins > 0 || hours > 0) suffix += `${mins}m `;
    suffix += `${secs}s`;
    
    return `${originalUptime} (+${suffix.trim()})`;
  };

  const notificationAlerts = [
    {
      id: 1,
      title: 'Heurística aplicada com sucesso',
      desc: 'Bypass de overlay no EP-7729-A obteve 98% de precisão.',
      time: '2 minutos atrás',
      type: 'success',
    },
    {
      id: 2,
      title: 'Alerta Crítico Resolvido',
      desc: 'Loop de hidratação no EP-7724-B foi isolado temporariamente.',
      time: '20 minutos atrás',
      type: 'warning',
    },
    {
      id: 3,
      title: 'Indexação Vetorial de Episódios',
      desc: '15 novas instâncias consolidadas no banco t-SNE de memórias.',
      time: '1 hora atrás',
      type: 'info',
    },
  ];

  return (
    <header className="fixed top-0 right-0 left-[260px] h-16 flex justify-between items-center px-6 z-30 bg-[#050505] border-b border-[#ffffff10] select-none">
      <div className="flex items-center gap-6">
        <span className="font-serif text-[20px] font-normal tracking-tight text-[#c5a059]">
          JARVIS V3
        </span>
        <div className="hidden md:flex items-center gap-4">
          <span className="text-[#c5a059] font-medium border-b border-[#c5a059]/40 pb-0.5 font-mono text-[10px] tracking-wide uppercase">
            Uptime: {formatUptimeWithLiveSeconds(uptime)}
          </span>
          <span className="text-[#888888] font-medium font-mono text-[10px] tracking-wide uppercase">
            Task: <span className="text-[#e0e0e0] font-bold">{taskStatus}</span>
          </span>
          <span className="text-[#888888] font-medium font-mono text-[10px] tracking-wide uppercase">
            LLM Usage: <span className="text-[#c5a059]">{llmBudget}%</span>
          </span>
        </div>
      </div>

      <div className="flex items-center gap-4 relative">
        {/* API Status Badge */}
        <div className="hidden xl:flex items-center gap-2 px-2.5 py-1 bg-[#0c0c0c] border border-[#ffffff10] rounded font-mono text-[10px] uppercase font-bold text-[#c5a059]">
          <span className="w-1.5 h-1.5 bg-[#c5a059] rounded-full animate-pulse" />
          API Status: {apiStatus}
        </div>

        {/* Diagnostic Logs / Terminal Trigger */}
        <button
          onClick={onToggleTerminal}
          title="Terminal de Diagnósticos"
          className={`p-1.5 rounded hover:bg-[#141414] transition-colors border ${
            terminalOpen ? 'border-[#c5a059] text-[#c5a059] bg-[#0c0c0c]' : 'border-[#ffffff10] text-[#888888]'
          }`}
        >
          <span className="material-symbols-outlined block text-[20px]">terminal</span>
        </button>

        {/* Notifications Popover */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className={`p-1.5 rounded hover:bg-[#141414] transition-colors border ${
              showNotifications ? 'border-[#c5a059] text-[#c5a059] bg-[#0c0c0c]' : 'border-[#ffffff10] text-[#888888]'
            }`}
          >
            <span className="material-symbols-outlined block text-[20px]">notifications</span>
            <span className="absolute top-1 right-1 w-1.5 h-1.5 bg-rose-500 rounded-full" />
          </button>

          {showNotifications && (
            <>
              <div
                className="fixed inset-0 z-40"
                onClick={() => setShowNotifications(false)}
              />
              <div className="absolute right-0 mt-3 w-80 bg-[#0c0c0c] border border-[#ffffff10] shadow-2xl p-4 rounded-sm z-50 animate-fade-in">
                <div className="flex justify-between items-center border-b border-[#ffffff10] pb-2.5 mb-2.5">
                  <span className="text-[#c5a059] font-mono text-[11px] font-bold uppercase tracking-wider">
                    Alertas do Sistema
                  </span>
                  <button
                    onClick={() => setShowNotifications(false)}
                    className="text-[#888888] hover:text-white"
                  >
                    <span className="material-symbols-outlined text-[16px] block">close</span>
                  </button>
                </div>
                <div className="flex flex-col gap-2 max-h-64 overflow-y-auto">
                  {notificationAlerts.map((n) => (
                    <div
                      key={n.id}
                      className="p-2.5 bg-[#080808] hover:bg-[#141414] border-l border-[#c5a059] transition-colors"
                    >
                      <div className="flex justify-between items-center mb-1">
                        <span className="font-sans text-[11px] font-bold text-[#e0e0e0]">
                          {n.title}
                        </span>
                        <span className="font-mono text-[8px] text-[#888888]">{n.time}</span>
                      </div>
                      <p className="font-sans text-[10px] text-[#888888] leading-relaxed">
                        {n.desc}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Profile Headshot Image block */}
        <img
          alt="System Administrator Profile"
          className="w-8 h-8 rounded-full bg-[#1c1c1c] border border-[#ffffff10] cursor-pointer hover:border-[#c5a059] transition-colors"
          src="https://lh3.googleusercontent.com/aida-public/AB6AXuBhc1Xsi4Yl6grFPHSlSR-aVqt886tKp8M_O_e3ydtC086eDvKR7eRzzXMB2AH5tPJFwJ8wB3mhk1H1EC-VAEFYoMdbxsV7LbY1OVecm3JkkWjUswjXBa1fw89_adKqEDPIdMLU1WQDHMmEwfiQmS6Mcbf4vUvgmirCbOlVeAAVI9XI5P7GSOvD03CzNBKCF8K_fJL7x-LAxV79mRJjaC9njTboZ3XV_EYrCS5j8qzSVDmdYDmyVQPnCkWQRiQKU2RCWw1koX9Ye9E"
        />
      </div>
    </header>
  );
}
