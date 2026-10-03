import React, { useState } from 'react';
import { MemoryEpisode } from '../types';

interface EditLogicModalProps {
  episode: MemoryEpisode;
  onClose: () => void;
  onSave: (updatedEp: MemoryEpisode) => void;
}

export default function EditLogicModal({ episode, onClose, onSave }: EditLogicModalProps) {
  const [comment, setComment] = useState(episode.logicComment);
  const [context, setContext] = useState(episode.learnedPattern.context);
  const [heuristic, setHeuristic] = useState(episode.learnedPattern.heuristic);
  const [successRate, setSuccessRate] = useState(episode.learnedPattern.successRate);

  const handleUpdate = (e: React.FormEvent) => {
    e.preventDefault();

    const updated: MemoryEpisode = {
      ...episode,
      logicComment: comment,
      learnedPattern: {
        ...episode.learnedPattern,
        context,
        heuristic,
        successRate: Number(successRate),
      },
    };

    onSave(updated);
  };

  return (
    <div className="fixed inset-0 bg-[#000000]/85 z-50 flex items-center justify-center p-4 backdrop-blur-xs select-none">
      <div className="bg-[#0c0c0c] border border-[#ffffff10] max-w-lg w-full flex flex-col p-6 shadow-2xl relative">
        <div className="absolute top-0 left-0 right-0 h-0.5 bg-[#c5a059]" />

        <div className="flex justify-between items-center pb-3 border-b border-[#ffffff10] mb-4">
          <h2 className="text-[#c5a059] font-serif text-[16px] font-normal tracking-tight uppercase flex items-center gap-2">
            <span className="material-symbols-outlined text-[20px]">terminal</span>
            Editar Lógica Integrada: {episode.id}
          </h2>
          <button onClick={onClose} className="text-[#888888] hover:text-white transition-colors">
            <span className="material-symbols-outlined text-[22px] block">close</span>
          </button>
        </div>

        <form onSubmit={handleUpdate} className="flex flex-col gap-4">
          {/* Commentary Area */}
          <div>
            <label className="block text-[9px] font-mono font-bold text-[#888888] uppercase tracking-wider mb-1.5">
              Comentário da Lógica de Resolução (OCR)
            </label>
            <input
              type="text"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              className="w-full bg-[#080808] border border-[#ffffff10] text-[#e0e0e0] text-xs p-2.5 focus:outline-none focus:border-[#c5a059]"
            />
          </div>

          {/* Trigger Context */}
          <div>
            <label className="block text-[9px] font-mono font-bold text-[#888888] uppercase tracking-wider mb-1.5">
              Seletor de Contexto Ativo (Trigger)
            </label>
            <textarea
              rows={2}
              value={context}
              onChange={(e) => setContext(e.target.value)}
              className="w-full bg-[#080808] border border-[#ffffff10] text-[#e0e0e0] text-xs p-2.5 focus:outline-none focus:border-[#c5a059] resize-none"
            />
          </div>

          {/* Heuristic Formula */}
          <div>
            <label className="block text-[9px] font-mono font-bold text-[#888888] uppercase tracking-wider mb-1.5">
              Fórmula de Heurística de Remediação
            </label>
            <textarea
              rows={2}
              value={heuristic}
              onChange={(e) => setHeuristic(e.target.value)}
              className="w-full bg-[#080808] border border-[#ffffff10] text-[#e0e0e0] text-xs p-2.5 focus:outline-none focus:border-[#c5a059] resize-none"
            />
          </div>

          {/* Metrics rate */}
          <div>
            <label className="block text-[9px] font-mono font-bold text-[#888888] uppercase tracking-wider mb-1.5">
              Taxa de Sucesso Experimental (%)
            </label>
            <input
              type="number"
              min={0}
              max={100}
              value={successRate}
              onChange={(e) => setSuccessRate(Number(e.target.value))}
              className="w-full bg-[#080808] border border-[#ffffff10] text-[#e0e0e0] text-xs p-2.5 focus:outline-none focus:border-[#c5a059]"
            />
          </div>

          <div className="flex gap-3 justify-end mt-4 border-t border-[#ffffff10] pt-4">
            <button
              type="button"
              onClick={onClose}
              className="py-1.5 px-4 border border-[#ffffff10] text-[#888888] hover:text-white hover:bg-[#141414] font-mono text-[10px] uppercase tracking-wider text-center transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="py-1.5 px-4 bg-[#c5a059] text-[#050505] font-mono text-[10px] font-bold uppercase tracking-wider text-center hover:bg-[#d4b57a] active:scale-95 transition-all shadow-md"
            >
              Confirmar Edições (Aplicar Estado)
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
