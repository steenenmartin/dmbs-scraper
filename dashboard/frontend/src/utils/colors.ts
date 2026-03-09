function hexToRgb(hex: string): [number, number, number] {
  hex = hex.replace("#", "");
  return [
    parseInt(hex.substring(0, 2), 16),
    parseInt(hex.substring(2, 4), 16),
    parseInt(hex.substring(4, 6), 16),
  ];
}

function rgbToHex(r: number, g: number, b: number): string {
  return (
    "#" +
    [r, g, b]
      .map((v) =>
        Math.round(v)
          .toString(16)
          .padStart(2, "0")
      )
      .join("")
  );
}

export function colorGradient(count: number): string[] {
  if (count <= 0) return [];
  if (count === 1) return ["#00008b"];

  const startRgb = hexToRgb("#00008b"); // darkblue
  const endRgb = hexToRgb("#34a1fa"); // light blue

  return Array.from({ length: count }, (_, i) => {
    const t = i / (count - 1);
    return rgbToHex(
      startRgb[0] + (endRgb[0] - startRgb[0]) * t,
      startRgb[1] + (endRgb[1] - startRgb[1]) * t,
      startRgb[2] + (endRgb[2] - startRgb[2]) * t
    );
  });
}
