import html2canvas from "html2canvas";

export interface MilestoneCardData {
  snapshotImageUrl: string;
  milestoneLabel: string;
  date: string;
  sessionCount: number;
  diaryExcerpt?: string | null;
}

/**
 * Render a milestone card as an off-screen styled div, then
 * capture it with html2canvas and return the blob + data URL.
 */
export async function generateMilestoneCard(
  data: MilestoneCardData
): Promise<{ dataUrl: string; blob: Blob }> {
  const container = document.createElement("div");
  container.style.cssText =
    "position:fixed;left:-9999px;top:-9999px;width:600px;font-family:system-ui,-apple-system,sans-serif;";

  container.innerHTML = `
    <div style="
      width:600px;
      background:#F5F0EB;
      border-radius:16px;
      overflow:hidden;
      box-shadow:0 4px 24px rgba(0,0,0,0.08);
    ">
      <div style="width:600px;height:350px;background:#E8E0D6;overflow:hidden;">
        <img
          src="${data.snapshotImageUrl}"
          alt=""
          crossorigin="anonymous"
          style="width:100%;height:100%;object-fit:cover;"
        />
      </div>
      <div style="padding:20px 24px 24px;">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
          <span style="
            display:inline-flex;align-items:center;justify-content:center;
            width:28px;height:28px;border-radius:50%;
            background:#D4A574;color:white;font-size:14px;
          ">✦</span>
          <span style="font-size:16px;font-weight:600;color:#3D3229;">
            ${escapeHtml(data.milestoneLabel)}
          </span>
        </div>
        <div style="font-size:13px;color:#8B7355;margin-bottom:${data.diaryExcerpt ? "8" : "12"}px;">
          ${escapeHtml(data.date)}${data.sessionCount > 0 ? ` · ${data.sessionCount} sessions` : ""}
        </div>
        ${
          data.diaryExcerpt
            ? `<p style="font-size:13px;color:#8B7355;font-style:italic;margin:0 0 12px;">
            "${escapeHtml(data.diaryExcerpt)}"
          </p>`
            : ""
        }
        <div style="
          display:flex;align-items:center;gap:6px;
          padding-top:12px;border-top:1px solid #E0D5C7;
          font-size:11px;color:#A89680;
        ">
          <span>🪑</span>
          <span>Focus Squad</span>
        </div>
      </div>
    </div>
  `;

  document.body.appendChild(container);

  try {
    const canvas = await html2canvas(container.firstElementChild as HTMLElement, {
      scale: 2,
      useCORS: true,
      backgroundColor: null,
    });

    const dataUrl = canvas.toDataURL("image/png");
    const blob = await new Promise<Blob>((resolve) =>
      canvas.toBlob((b) => resolve(b!), "image/png")
    );

    return { dataUrl, blob };
  } finally {
    document.body.removeChild(container);
  }
}

export function downloadMilestoneCard(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export async function copyMilestoneCardToClipboard(blob: Blob): Promise<boolean> {
  try {
    await navigator.clipboard.write([new ClipboardItem({ "image/png": blob })]);
    return true;
  } catch {
    return false;
  }
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
