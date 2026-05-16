const KEY = "finance_selected_month";

export function saveMonth(d: Date): void {
  try {
    const val = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
    localStorage.setItem(KEY, val);
  } catch {}
}

export function loadMonth(): Date {
  try {
    const val = localStorage.getItem(KEY);
    if (val) {
      const [y, m] = val.split("-").map(Number);
      if (y && m) return new Date(y, m - 1, 1);
    }
  } catch {}
  return new Date();
}
