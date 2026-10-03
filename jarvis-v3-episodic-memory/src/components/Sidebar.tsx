import React from 'react';

interface SidebarProps {
  activeTab: 'tasks' | 'memory' | 'policy' | 'settings';
  setActiveTab: (tab: 'tasks' | 'memory' | 'policy' | 'settings') => void;
  onOpenNewAutomation: () => void;
}

export default function Sidebar({ activeTab, setActiveTab, onOpenNewAutomation }: SidebarProps) {
  return (
    <aside className="sidebar-entrance fixed left-0 top-0 h-screen flex flex-col p-4 z-40 bg-[#080808] border-r border-[#ffffff10] w-[260px] transition-transform duration-300">
      <div className="mb-8 flex items-center gap-3">
        <div className="w-9 h-9 bg-gradient-to-tr from-[#c5a059] to-[#8c6d3d] rounded-full flex items-center justify-center shadow-[0_0_12px_rgba(197,160,89,0.25)]">
          <span className="material-symbols-outlined text-[#050505] text-lg font-bold">bolt</span>
        </div>
        <div>
          <h1 className="font-serif text-[18px] font-normal text-[#c5a059] tracking-tight leading-none uppercase">
            JARVIS CORE
          </h1>
          <p className="font-mono text-[9px] text-[#888888] tracking-wider uppercase mt-1">
            v3.0.4-stable
          </p>
        </div>
      </div>

      <nav className="flex-1 flex flex-col gap-1">
        {/* Active Tasks Menu */}
        <button
          onClick={() => setActiveTab('tasks')}
          className={`flex items-center gap-3 p-3 w-full text-left rounded transition-all group ${
            activeTab === 'tasks'
              ? 'text-[#c5a059] font-bold bg-[#141414] border-l-2 border-l-[#c5a059]'
              : 'text-[#888888] hover:text-white hover:bg-[#0c0c0c]'
          }`}
        >
          <span className="material-symbols-outlined text-lg">assignment</span>
          <span className="font-mono text-[11px] font-bold uppercase tracking-wider group-hover:translate-x-0.5 transition-transform">
            Active Tasks
          </span>
        </button>

        {/* Memory Menu */}
        <button
          onClick={() => setActiveTab('memory')}
          className={`flex items-center gap-3 p-3 w-full text-left rounded transition-all group ${
            activeTab === 'memory'
              ? 'text-[#c5a059] font-bold bg-[#141414] border-l-2 border-l-[#c5a059]'
              : 'text-[#888888] hover:text-white hover:bg-[#0c0c0c]'
          }`}
        >
          <span className="material-symbols-outlined text-lg">database</span>
          <span className="font-mono text-[11px] font-bold uppercase tracking-wider group-hover:translate-x-0.5 transition-transform">
            Memory
          </span>
        </button>

        {/* Policy Menu */}
        <button
          onClick={() => setActiveTab('policy')}
          className={`flex items-center gap-3 p-3 w-full text-left rounded transition-all group ${
            activeTab === 'policy'
              ? 'text-[#c5a059] font-bold bg-[#141414] border-l-2 border-l-[#c5a059]'
              : 'text-[#888888] hover:text-white hover:bg-[#0c0c0c]'
          }`}
        >
          <span className="material-symbols-outlined text-lg">gavel</span>
          <span className="font-mono text-[11px] font-bold uppercase tracking-wider group-hover:translate-x-0.5 transition-transform">
            Policy
          </span>
        </button>

        {/* Settings Menu */}
        <button
          onClick={() => setActiveTab('settings')}
          className={`flex items-center gap-3 p-3 w-full text-left rounded transition-all group ${
            activeTab === 'settings'
              ? 'text-[#c5a059] font-bold bg-[#141414] border-l-2 border-l-[#c5a059]'
              : 'text-[#888888] hover:text-white hover:bg-[#0c0c0c]'
          }`}
        >
          <span className="material-symbols-outlined text-lg">settings</span>
          <span className="font-mono text-[11px] font-bold uppercase tracking-wider group-hover:translate-x-0.5 transition-transform">
            Settings
          </span>
        </button>
      </nav>

      {/* Button: NEW AUTOMATION */}
      <button
        onClick={onOpenNewAutomation}
        className="glitch-hover mt-4 w-full py-2.5 bg-[#c5a059] text-[#050505] font-mono text-[10px] font-bold tracking-widest hover:bg-[#d4b57a] active:scale-95 transition-all uppercase rounded-sm"
      >
        NEW AUTOMATION
      </button>

      {/* Support / Footer links */}
      <div className="mt-auto border-t border-[#ffffff10] pt-4 flex flex-col gap-1">
        <a
          href="#docs"
          className="flex items-center gap-3 p-2 text-[#888888] hover:text-white transition-all"
        >
          <span className="material-symbols-outlined text-lg">description</span>
          <span className="font-mono text-[10px] font-bold tracking-wider uppercase">Docs</span>
        </a>
        <a
          href="#support"
          className="flex items-center gap-3 p-2 text-[#888888] hover:text-white transition-all"
        >
          <span className="material-symbols-outlined text-lg">help</span>
          <span className="font-mono text-[10px] font-bold tracking-wider uppercase">Support</span>
        </a>
      </div>
    </aside>
  );
}
