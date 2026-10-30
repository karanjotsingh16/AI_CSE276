import { RadarFrame, RadarState } from '../types/radar';

export async function fetchRainViewerMetadata(): Promise<{
  host: string;
  frames: RadarFrame[];
  lastUpdated: string | null;
}> {
  const url = 'https://api.rainviewer.com/public/weather-maps.json';

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 7000);
    const res = await fetch(url, { signal: controller.signal });
    clearTimeout(timeout);

    if (!res.ok) {
      throw new Error(`RainViewer metadata HTTP ${res.status}`);
    }

    const data = await res.json();
    const host = data.host || 'https://tilecache.rainviewer.com';
    const pastFrames: RadarFrame[] = (data.radar?.past || []).map((f: { time: number; path: string }) => ({
      time: f.time,
      path: f.path
    }));

    const lastTime = pastFrames.length > 0 ? pastFrames[pastFrames.length - 1].time : null;
    const lastUpdatedIso = lastTime ? new Date(lastTime * 1000).toISOString() : null;

    return {
      host,
      frames: pastFrames,
      lastUpdated: lastUpdatedIso
    };
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Radar connection error';
    throw new Error(msg);
  }
}

export function getRadarTileUrl(host: string, path: string): string {
  // RainViewer tile format: {host}{path}/256/{z}/{x}/{y}/2/1_1.png
  // 2 = color scheme 2 (Universal Blue), 1_1 = smooth with snow
  return `${host}${path}/256/{z}/{x}/{y}/2/1_1.png`;
}
