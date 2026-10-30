export interface RadarFrame {
  time: number;
  path: string;
}

export interface RadarState {
  isActive: boolean;
  isPlaying: boolean;
  frames: RadarFrame[];
  currentFrameIndex: number;
  lastUpdated: string | null;
  isLoading: boolean;
  error: string | null;
  host: string;
}
