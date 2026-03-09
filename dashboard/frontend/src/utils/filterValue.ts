export function valuesMatch(
  selected: (string | number)[],
  rowValue: string | number
): boolean {
  const rowAsString = String(rowValue);
  return selected.some((value) => String(value) === rowAsString);
}
