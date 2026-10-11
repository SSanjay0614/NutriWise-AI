// Local-date helpers so "today" and meal times follow the user's own clock.
export function localDay(d = new Date()) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export function localDateTime(d = new Date()) {
  // ISO-ish local datetime (no timezone shift) for eaten_at / performed_at.
  const pad = (n) => String(n).padStart(2, '0');
  return `${localDay(d)}T${pad(d.getHours())}:${pad(d.getMinutes())}:00`;
}

export function nowHHMM(d = new Date()) {
  const pad = (n) => String(n).padStart(2, '0');
  return `${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// Combine a YYYY-MM-DD day and a HH:MM time into a local ISO datetime string.
export function combineDayTime(day, hhmm) {
  if (!hhmm) return null;
  return `${day}T${hhmm}:00`;
}

export function fmtTime(iso) {
  if (!iso) return '';
  const t = iso.includes('T') ? iso.split('T')[1] : iso;
  return (t || '').slice(0, 5);
}
