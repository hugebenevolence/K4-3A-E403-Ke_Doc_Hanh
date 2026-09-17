import { describe, expect, it } from "vitest";
import { layout } from "./graph-layout";

const NODES = [
  { id: "token", weight: 3 },
  { id: "attention", weight: 1 },
  { id: "context", weight: 1 },
  { id: "rlhf", weight: 2 },
];
const LINKS = [{ source: "token", target: "attention" }];

describe("bố cục đồ thị", () => {
  it("cho mỗi đỉnh một chỗ, nằm trong khung", () => {
    const pos = layout(NODES, LINKS, { width: 900, height: 600 });
    expect(pos.size).toBe(4);
    for (const p of pos.values()) {
      expect(p.x).toBeGreaterThanOrEqual(0);
      expect(p.x).toBeLessThanOrEqual(900);
      expect(p.y).toBeGreaterThanOrEqual(0);
      expect(p.y).toBeLessThanOrEqual(600);
      expect(Number.isFinite(p.x) && Number.isFinite(p.y)).toBe(true);
    }
  });

  it("chạy lại ra ĐÚNG chỗ cũ", () => {
    // Người học nhớ bản đồ của mình theo hình dạng; hình nhảy mỗi lần tải lại
    // thì không nhớ được, nên bố cục phải tất định.
    const a = layout(NODES, LINKS);
    const b = layout(NODES, LINKS);
    for (const [id, p] of a) {
      expect(b.get(id).x).toBeCloseTo(p.x, 9);
      expect(b.get(id).y).toBeCloseTo(p.y, 9);
    }
  });

  it("CẠNH thật sự kéo hai đỉnh lại gần nhau", () => {
    // So với chính đồ thị đó khi BỎ HẾT CẠNH, chứ không so hai cặp đỉnh khác
    // nhau. Bản test đầu so cặp-với-cặp và vẫn xanh khi lực lò xo hỏng hoàn
    // toàn — nó chỉ đang đo chỗ ngồi ban đầu do hàm băm sinh ra, nên bug "cạnh
    // không có tác dụng gì" lọt qua.
    const co = layout(NODES, LINKS, { width: 900, height: 600 });
    const khong = layout(NODES, [], { width: 900, height: 600 });
    const d = (p, a, b) => Math.hypot(p.get(a).x - p.get(b).x, p.get(a).y - p.get(b).y);
    expect(d(co, "token", "attention")).toBeLessThan(d(khong, "token", "attention"));
  });

  it("đồ thị rỗng không làm vỡ gì", () => {
    expect(layout([], []).size).toBe(0);
  });
});
