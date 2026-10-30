export function formatDistance(km: number): string {
  if (isNaN(km) || km == null) return 'N/A';
  return `${Number(km.toFixed(2))} km`;
}

export function splitDurationHoursMinutes(minutes: number): {
  hours: number;
  mins: number;
  formatted: string;
} {
  if (isNaN(minutes) || minutes == null || !Number.isFinite(minutes) || minutes < 0) {
    return { hours: 0, mins: 0, formatted: '0 hr 0 min' };
  }
  const totalMins = Math.max(1, Math.round(minutes));
  const hours = Math.floor(totalMins / 60);
  const mins = totalMins % 60;
  const formatted = `${hours} hr ${mins} min`;
  return { hours, mins, formatted };
}

export function formatDurationHoursMinutes(minutes: number): string {
  return splitDurationHoursMinutes(minutes).formatted;
}

export function formatDuration(minutes: number): string {
  if (isNaN(minutes) || minutes == null) return 'N/A';
  return `${formatDurationHoursMinutes(minutes)} (est.)`;
}

export function formatTimestamp(isoString?: string | null): string {
  if (!isoString) return 'Unavailable';
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return isoString;
    return (
      d.toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      }) +
      ' (' +
      d.toLocaleDateString([], { month: 'short', day: 'numeric' }) +
      ')'
    );
  } catch {
    return isoString;
  }
}

export function formatCoords(lat: number, lng: number): string {
  const latDir = lat >= 0 ? 'N' : 'S';
  const lngDir = lng >= 0 ? 'E' : 'W';
  return `${Math.abs(lat).toFixed(3)}°${latDir}, ${Math.abs(lng).toFixed(3)}°${lngDir}`;
}
