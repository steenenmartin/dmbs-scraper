export async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Kunne ikke hente data (${response.status}). Kontrollér databaseforbindelsen.`);
  return response.json();
}
