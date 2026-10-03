import React, { useState } from 'react';
import { MemoryEpisode } from '../types';

interface NewAutomationModalProps {
  onClose: () => void;
  onSave: (newEpisode: MemoryEpisode) => void;
}

export default function NewAutomationModal({ onClose, onSave }: NewAutomationModalProps) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [riskLevel, setRiskLevel] = useState<'SAFE' | 'CRITICAL' | 'WARNING'>('SAFE');
  const [category, setCategory] = useState<'UI BREAKAGE' | 'RESOLVED PATHS'>('RESOLVED PATHS');
  const [contextInput, setContextInput] = useState('Target: Chrome v112+, Element: Fixed Overlay, Property: opacity > 0.9');
  const [heuristicInput, setHeuristicInput] = useState('Initiate element visibility audit check before coordinate injection.');
  const [diffRemove, setDiffRemove] = useState('- <input class="hidden" name="token">');
  const [diffAdd, setDiffAdd] = useState('+ <input type="hidden" name="token" value="secure">');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title) return;

    const customId = `EP-${Math.floor(Math.random() * 900) + 7100}-${Math.random().toString(36).substring(2, 3).toUpperCase()}`;
    const timestamp = new Date().toTimeString().split(' ')[0] + '.' + Math.floor(Math.random() * 100);

    const newEp: MemoryEpisode = {
      id: customId,
      title,
      description,
      riskLevel,
      timestamp,
      similarityScore: parseFloat((Math.random() * 0.4 + 0.6).toFixed(4)),
      retrievalRank: '#1 Match (New)',
      category: category === 'UI BREAKAGE' ? 'UI BREAKAGE' : 'RESOLVED PATHS',
      // Public high contrast placeholder images
      beforeImage: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBAWMnvtK56ELtoUuAHTQa1m9M88I-wq7xxYscbE1INBnxzLiauS1wEk7oH_CtOqQDyFOIYMp2A5Wjk0XAdgXlfDJ5Pxjff912_leWpd1epaaQKAZMtpUYPNjTs-30n1BPrV6l9AO49woujWBbRbCCFJUuuyAyeZxCKiY5Vm4mIXt5xwxBTJPJCqIAMFgd_yYvUOFugW8clNZCgCo8JulyzCiNnPuw5k1OfNyYAL7c9YMMQez506J1b0zFBU4QamlRlm0t381PLecE',
      afterImage: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAk_23K2BGjaDzAuycci5W0O9NO_DvaQCR5SS81LlYAQ8_h9mP02xlncd0OI4F2_qef6SQtQhNW8GffoXVkidqw-fFnqlv4Emx3QxtHFHJK5FzvoAG40Iv4abtsL_hZ9rtw06nccX9bmOjPY0f8kyzhNgtWaRqcZmHo-vR-VWtM1MO18r8ZU4-q8EyNc2yOtzPkkdKg7dsDp-ua4XAi9zPDj1W8VZlmv5ulS0FToAYoIwJ5qlBG5gMyiAdVNyBZGEoEVB-gZT2Li3U',
      stateDiff: [
        { type: 'remove', lineNum: '101', content: diffRemove.replace(/^[-+]\s*/, '') },
        { type: 'add', lineNum: '101', content: diffAdd.replace(/^[-+]\s*/, '') }
      ],
      logicComment: `Rule generated dynamically for resolving target selector boundaries.`,
      learnedPattern: {
        context: contextInput,
        heuristic: heuristicInput,
        observedAgo: 'JUST NOW',
        successRate: 100,
        reliabilityLevel: 'High Confidence',
        reliabilityPercent: 98,
      },
      // Generate randomized 2D coordinate inside the standard region
      coordinates2D: {
        x: Math.floor(Math.random() * 60) + 20,
        y: Math.floor(Math.random() * 60) + 20,
      },
      // Generate standard coordinates for 3D projections
      coordinates3D: {
        x: Math.floor(Math.random() * 16) - 8,
        y: Math.floor(Math.random() * 16) - 8,
        z: Math.floor(Math.random() * 16) - 8,
      }
    };

    onSave(newEp);
  };

  return (
    <div className="fixed inset-0 bg-[#000000]/85 z-50 flex items-center justify-center p-4 backdrop-blur-xs select-none">
      <div className="bg-[#0c0c0c] border border-[#ffffff10] max-w-xl w-full flex flex-col p-6 shadow-2xl relative">
        {/* Header decoration */}
        <div className="absolute top-0 left-0 right-0 h-0.5 bg-[#c5a059]" />

        <div className="flex justify-between items-center pb-3 border-b border-[#ffffff10] mb-4">
          <h2 className="text-[#c5a059] font-serif text-[17px] font-normal tracking-tight uppercase flex items-center gap-2">
            <span className="material-symbols-outlined text-[20px]">smart_toy</span>
            Criar Nova Heurística de Automação
          </h2>
          <button onClick={onClose} className="text-[#888888] hover:text-white transition-colors">
            <span className="material-symbols-outlined text-[22px] block">close</span>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4 overflow-y-auto max-h-[75vh] pr-1">
          {/* Title Area */}
          <div>
            <label className="block text-[9px] font-mono font-bold text-[#888888] uppercase tracking-wider mb-1.5">
              Título da Resolução (Cenário)
            </label>
            <input
              required
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full bg-[#080808] border border-[#ffffff10] text-[#e0e0e0] text-xs p-2.5 focus:outline-none focus:border-[#c5a059]"
              placeholder="ex: Falha de foco automático no campo de pesquisa modal..."
            />
          </div>

          {/* Description Area */}
          <div>
            <label className="block text-[9px] font-mono font-bold text-[#888888] uppercase tracking-wider mb-1.5">
              Descrição Detalhada do Incidente
            </label>
            <textarea
              required
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full bg-[#080808] border border-[#ffffff10] text-[#e0e0e0] text-xs p-2.5 focus:outline-none focus:border-[#c5a059] resize-none"
              placeholder="ex: O script falhou ao injetar caracteres adequados por conta de encapsulamento do estado."
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* Risk Selector */}
            <div>
              <label className="block text-[9px] font-mono font-bold text-[#888888] uppercase tracking-wider mb-1.5">
                Risk Classification
              </label>
              <select
                value={riskLevel}
                onChange={(e) => setRiskLevel(e.target.value as any)}
                className="w-full bg-[#080808] border border-[#ffffff10] text-[#e0e0e0] text-xs p-2 focus:outline-none focus:border-[#c5a059]"
              >
                <option value="SAFE">SAFE (Aprovado)</option>
                <option value="WARNING">WARNING (Avaliação)</option>
                <option value="CRITICAL">CRITICAL (Anomalia)</option>
              </select>
            </div>

            {/* Category Selector */}
            <div>
              <label className="block text-[9px] font-mono font-bold text-[#888888] uppercase tracking-wider mb-1.5">
                Visual Category Projection
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value as any)}
                className="w-full bg-[#080808] border border-[#ffffff10] text-[#e0e0e0] text-xs p-2 focus:outline-none focus:border-[#c5a059]"
              >
                <option value="RESOLVED PATHS">RESOLVED PATHS (Cluster Ouro)</option>
                <option value="UI BREAKAGE">UI BREAKAGE (Anomalia Crimson)</option>
              </select>
            </div>
          </div>

          <div className="border-t border-[#ffffff10] pt-3">
            <h3 className="text-[#c5a059] text-[11px] font-mono uppercase tracking-wider font-bold mb-2">
              Regras e Heurísticas de Aprendizado
            </h3>
            
            <div className="flex flex-col gap-3">
              <div>
                <label className="block text-[8px] font-mono text-[#888888] uppercase tracking-wider mb-1">
                  Context Trigger Selector Check
                </label>
                <input
                  type="text"
                  value={contextInput}
                  onChange={(e) => setContextInput(e.target.value)}
                  className="w-full bg-[#080808] border border-[#ffffff10] text-[#e0e0e0] text-xs p-2 focus:outline-none focus:border-[#c5a059]"
                />
              </div>

              <div>
                <label className="block text-[8px] font-mono text-[#888888] uppercase tracking-wider mb-1">
                  Heuristic Remediation Method
                </label>
                <input
                  type="text"
                  value={heuristicInput}
                  onChange={(e) => setHeuristicInput(e.target.value)}
                  className="w-full bg-[#080808] border border-[#ffffff10] text-[#e0e0e0] text-xs p-2 focus:outline-none focus:border-[#c5a059]"
                />
              </div>
            </div>
          </div>

          <div className="border-t border-[#ffffff10] pt-3">
            <h3 className="text-[#c5a059] text-[11px] font-mono uppercase tracking-wider font-bold mb-2">
              Diferenças de Estado (OCR Snapshot)
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[8px] font-mono text-[#888888] mb-1">Antes (Linha Deletada)</label>
                <input
                  type="text"
                  value={diffRemove}
                  onChange={(e) => setDiffRemove(e.target.value)}
                  className="w-full bg-rose-950/20 border border-rose-900/40 text-rose-300 font-mono text-[11px] p-2 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-[8px] font-mono text-[#888888] mb-1">Depois (Linha Adicionada)</label>
                <input
                  type="text"
                  value={diffAdd}
                  onChange={(e) => setDiffAdd(e.target.value)}
                  className="w-full bg-emerald-950/20 border border-emerald-900/40 text-emerald-300 font-mono text-[11px] p-2 focus:outline-none"
                />
              </div>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex gap-3 justify-end mt-4 border-t border-[#ffffff10] pt-4 select-none">
            <button
              type="button"
              onClick={onClose}
              className="py-2 px-4 border border-[#ffffff10] text-[#888888] hover:text-white hover:bg-[#141414] font-mono text-[11px] uppercase tracking-wider text-center transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="py-2 px-4 bg-[#c5a059] text-[#050505] font-mono text-[11px] font-bold uppercase tracking-wider text-center hover:bg-[#d4b57a] active:scale-95 transition-all shadow-md"
            >
              Gravar Automação (Injetar Memória)
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
