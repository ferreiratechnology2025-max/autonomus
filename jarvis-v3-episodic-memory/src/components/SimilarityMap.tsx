import React, { useState, useEffect, useRef } from 'react';
import { MemoryEpisode } from '../types';

interface SimilarityMapProps {
  episodes: MemoryEpisode[];
  selectedEpisode: MemoryEpisode;
  onSelectEpisode: (episode: MemoryEpisode) => void;
}

export default function SimilarityMap({
  episodes,
  selectedEpisode,
  onSelectEpisode,
}: SimilarityMapProps) {
  const [projection, setProjection] = useState<'2D' | '3D'>('2D');
  const [rotationAngle, setRotationAngle] = useState(0);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Simple 3D orbit rotation effect!
  useEffect(() => {
    if (projection === '3D') {
      const interval = setInterval(() => {
        setRotationAngle((prev) => (prev + 0.02) % (Math.PI * 2));
      }, 30);
      return () => clearInterval(interval);
    }
  }, [projection]);

  // Handle background canvas digital rain effect
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animFrame: number;
    let width = (canvas.width = canvas.parentElement?.offsetWidth || 400);
    let height = (canvas.height = canvas.parentElement?.offsetHeight || 300);

    const characters = '01[]/<>';
    const fontSize = 10;
    const columns = Math.floor(width / fontSize);
    const drops: number[] = Array(columns).fill(0).map(() => Math.random() * -30);

    function draw() {
      ctx!.fillStyle = 'rgba(5, 5, 5, 0.1)';
      ctx!.fillRect(0, 0, width, height);

      ctx!.fillStyle = 'rgba(197, 160, 89, 0.08)';
      ctx!.font = `${fontSize}px "JetBrains Mono"`;

      for (let i = 0; i < drops.length; i++) {
        const text = characters.charAt(Math.floor(Math.random() * characters.length));
        ctx!.fillText(text, i * fontSize, drops[i] * fontSize);

        if (drops[i] * fontSize > height && Math.random() > 0.98) {
          drops[i] = 0;
        }
        drops[i] += 0.4;
      }
    }

    const animate = () => {
      draw();
      animFrame = requestAnimationFrame(animate);
    };

    animate();

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = canvas.parentElement?.offsetWidth || 400;
      height = canvas.height = canvas.parentElement?.offsetHeight || 300;
    };

    window.addEventListener('resize', handleResize);
    return () => {
      cancelAnimationFrame(animFrame);
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  // Compute node coordinates based on layout
  const getProjectedCoords = (episode: MemoryEpisode) => {
    if (projection === '2D') {
      return {
        x: episode.coordinates2D.x,
        y: episode.coordinates2D.y,
      };
    } else {
      // Rotate 3D coordinates using rotational matrices to give actual orbital floating!
      const cosA = Math.cos(rotationAngle);
      const sinA = Math.sin(rotationAngle);

      const cx = episode.coordinates3D.x;
      const cy = episode.coordinates3D.y;
      const cz = episode.coordinates3D.z;

      // Project the 3D values (x, y, z) into a rotating 2D space
      // Normalize values around Center (50, 50)
      const rotatedX = cx * cosA - cz * sinA;
      const rotatedZ = cx * sinA + cz * cosA;

      const scale = 1 + rotatedZ / 30; // depth perspective
      return {
        x: 50 + rotatedX * 4 * scale,
        y: 50 + cy * 4 * scale,
        scale,
      };
    }
  };

  // Get active selected point projections
  const activePoint = getProjectedCoords(selectedEpisode);

  return (
    <div className="col-span-12 lg:col-span-5 flex flex-col gap-2 h-full min-h-[400px]">
      <div className="flex justify-between items-center select-none">
        <h3 className="font-mono text-[10px] font-bold text-[#888888] tracking-wider uppercase">
          Similarity Map (TSNE Projection)
        </h3>
        <div className="flex gap-2">
          <button
            onClick={() => setProjection('2D')}
            className={`px-2.5 py-0.5 border font-mono text-[11px] font-bold tracking-wider hover:text-[#c5a059] transition-all uppercase ${
              projection === '2D'
                ? 'bg-[#1c1c1c] border-[#c5a059] text-[#c5a059]'
                : 'bg-[#0c0c0c] border-[#ffffff10] text-[#888888]'
            }`}
          >
            2D
          </button>
          <button
            onClick={() => setProjection('3D')}
            className={`px-2.5 py-0.5 border font-mono text-[11px] font-bold tracking-wider hover:text-[#c5a059] transition-all uppercase ${
              projection === '3D'
                ? 'bg-[#1c1c1c] border-[#c5a059] text-[#c5a059]'
                : 'bg-[#0c0c0c] border-[#ffffff10] text-[#888888]'
            }`}
          >
            3D
          </button>
        </div>
      </div>

      <div className="flex-1 bg-[#0c0c0c]/80 backdrop-blur-md border border-[#ffffff10] relative grid-bg overflow-hidden select-none">
        {/* Animated Scanline overlay */}
        <div className="scanline" />

        {/* Matrix background stream */}
        <canvas ref={canvasRef} className="absolute inset-0 w-full h-full pointer-events-none opacity-[0.25] z-0" />

        {/* SVG relationships lines */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none z-10">
          {episodes.map((ep) => {
            if (ep.id === selectedEpisode.id) return null;
            const targetCoords = getProjectedCoords(ep);

            return (
              <line
                key={`line-${ep.id}`}
                x1={`${targetCoords.x}%`}
                y1={`${targetCoords.y}%`}
                x2={`${activePoint.x}%`}
                y2={`${activePoint.y}%`}
                stroke="#c5a059"
                strokeOpacity={projection === '3D' ? 0.25 : 0.35}
                strokeDasharray="4,4"
                strokeWidth="0.75"
                className="transition-all duration-500"
              />
            );
          })}
        </svg>

        {/* Render Map Legend */}
        <div className="absolute bottom-4 left-4 flex flex-col gap-1.5 pointer-events-none z-30 bg-[#050505]/90 p-2.5 border border-[#ffffff10] backdrop-blur-xs">
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 bg-rose-500 rounded-full animate-pulse" />
            <span className="font-mono text-[8px] font-bold text-[#888888] uppercase tracking-wide">
              UI BREAKAGE
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 bg-[#c5a059] rounded-full" />
            <span className="font-mono text-[8px] font-bold text-[#888888] uppercase tracking-wide">
              RESOLVED PATHS
            </span>
          </div>
        </div>

        {/* Selected tag label */}
        <div
          className="absolute bg-[#0c0c0c]/95 border border-[#c5a059]/40 px-2.5 py-1 font-mono text-[10px] text-[#c5a059] font-bold z-30 transition-all duration-500 shadow-md"
          style={{
            left: `calc(${activePoint.x}% + 12px)`,
            top: `calc(${activePoint.y}% - 14px)`,
            transform: 'translate(-5px, -5px)',
          }}
        >
          CURRENT: {selectedEpisode.id}
        </div>

        {/* Scatter Nodes */}
        {episodes.map((ep) => {
          const isSelected = ep.id === selectedEpisode.id;
          const coords = getProjectedCoords(ep);
          
          let nodeColor = 'bg-[#888888]';
          if (ep.riskLevel === 'CRITICAL') nodeColor = 'bg-rose-500';
          else if (ep.riskLevel === 'WARNING') nodeColor = 'bg-amber-400';
          else if (isSelected) nodeColor = 'bg-[#c5a059]';
          else if (ep.category === 'RESOLVED PATHS') nodeColor = 'bg-[#8c6d3d]';

          return (
            <button
              key={`node-${ep.id}`}
              onClick={() => onSelectEpisode(ep)}
              className={`absolute border border-black rounded-full cursor-pointer z-20 hover:scale-150 transition-all duration-500 ${nodeColor} ${
                isSelected
                  ? 'node-pulse w-3 h-3 shadow-[0_0_15px_rgba(197,160,89,0.8)] ring-1 ring-[#050505]'
                  : 'w-2 h-2 shadow-md hover:shadow-[0_0_8px_rgba(197,160,89,0.5)]'
              }`}
              style={{
                left: `calc(${coords.x}% - 6px)`,
                top: `calc(${coords.y}% - 6px)`,
              }}
              title={`${ep.id}: ${ep.title}`}
            />
          );
        })}
      </div>
    </div>
  );
}
