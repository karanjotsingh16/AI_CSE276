export async function fetchPointElevation(lat: number, lng: number): Promise<number | null> {
  const url = `https://api.open-meteo.com/v1/elevation?latitude=${lat.toFixed(4)}&longitude=${lng.toFixed(4)}`;
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 6000);
    const res = await fetch(url, { signal: controller.signal });
    clearTimeout(timeout);

    if (!res.ok) return null;
    const data = await res.json();
    if (data.elevation && Array.isArray(data.elevation) && data.elevation.length > 0) {
      return Math.round(data.elevation[0]);
    }
    return null;
  } catch {
    return null;
  }
}
