/**
 * Capture the room grid as a base64 PNG string for timeline snapshots.
 *
 * Uses html2canvas to render the DOM element to a canvas, then exports
 * as a data URL. The returned string is the base64 portion only (no prefix).
 */
export async function captureRoomSnapshot(roomGridElement: HTMLElement): Promise<string> {
  const { default: html2canvas } = await import("html2canvas");
  const canvas = await html2canvas(roomGridElement, {
    backgroundColor: null,
    scale: 1,
    useCORS: true,
    logging: false,
  });

  const dataUrl = canvas.toDataURL("image/png");
  // Strip "data:image/png;base64," prefix
  return dataUrl.split(",")[1];
}
