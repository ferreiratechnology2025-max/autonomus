export interface StateDiffLine {
  type: 'remove' | 'add' | 'context';
  lineNum: string;
  content: string;
}

export interface LearnedPattern {
  context: string;
  heuristic: string;
  observedAgo: string;
  successRate: number;
  reliabilityLevel: string;
  reliabilityPercent: number;
}

export interface Coordinate2D {
  x: number; // percentage (0 to 100)
  y: number; // percentage (0 to 100)
}

export interface Coordinate3D {
  x: number;
  y: number;
  z: number;
}

export interface MemoryEpisode {
  id: string;
  title: string;
  description: string;
  riskLevel: 'SAFE' | 'CRITICAL' | 'WARNING';
  timestamp: string;
  similarityScore: number;
  retrievalRank: string;
  beforeImage: string;
  afterImage: string;
  stateDiff: StateDiffLine[];
  logicComment: string;
  learnedPattern: LearnedPattern;
  coordinates2D: Coordinate2D;
  coordinates3D: Coordinate3D;
  category: 'UI BREAKAGE' | 'RESOLVED PATHS' | 'WARNING TRIGGER';
}

export interface ActiveTask {
  id: string;
  title: string;
  description: string;
  progress: number; // 0 to 100
  status: 'running' | 'paused' | 'queued' | 'completed';
  latency: string;
  severity: 'low' | 'medium' | 'high';
  startedAt: string;
}

export interface PolicyRule {
  id: string;
  title: string;
  scope: string;
  statement: string;
  riskMitigation: string;
  status: 'active' | 'evaluating' | 'disabled';
  lastModified: string;
}

export interface SystemMetrics {
  uptime: string;
  taskStatus: string;
  llmBudget: number; // percentage e.g. 42
  queryLatency: string;
  indexSize: string;
  retrievalAccuracy: string;
}
