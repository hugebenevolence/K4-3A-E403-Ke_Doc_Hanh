// Xếp chỗ cho các đỉnh của đồ thị tri thức — lò xo và đẩy nhau, kiểu Obsidian.
//
// Tự viết thay vì kéo thêm d3-force: cả file này ngắn hơn phần d3 mà ta dùng
// tới, và app đang cố ý không nạp gì từ mạng lúc học (xem ghi chú font trong
// styles.css). Đồ thị của một học viên chỉ cỡ vài chục đỉnh, nên vòng lặp
// O(n²) chạy một lần trong vài mili giây là xong.
//
// TẤT ĐỊNH: vị trí ban đầu suy từ tên đỉnh chứ không phải Math.random(). Cùng
// một đồ thị thì lần nào mở ra cũng nằm đúng chỗ cũ — người học nhớ bản đồ của
// mình theo hình dạng, mà hình dạng nhảy mỗi lần tải lại thì không nhớ được.

const NGHI = 128;
/** Khoảng cách nghỉ của lò xo (px trong hệ toạ độ 900×620).
 *
 *  Đặt theo BỀ NGANG CỦA NHÃN chứ không phải theo bán kính đỉnh: hai chấm cách
 *  nhau 40px trông vẫn rời nhau, nhưng "attention" và "context" viết dưới chúng
 *  thì đã đè lên nhau rồi. 128px là chỗ hai nhãn dài vẫn thở được. */

/** Băm tên thành một số ổn định, để mỗi đỉnh có một chỗ khởi đầu riêng. */
function hash(text) {
  let h = 2166136261;
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return (h >>> 0) / 4294967295;
}

/**
 * @param nodes [{ id, weight }] — weight lớn thì đỉnh nặng, ít bị đẩy đi
 * @param links [{ source, target }]
 * @returns Map(id -> {x, y}) trong khung width×height
 */
export function layout(nodes, links, { width = 900, height = 620, iterations = 300 } = {}) {
  const pos = new Map();
  if (!nodes.length) return pos;

  const cx = width / 2;
  const cy = height / 2;
  // Bán kính lý tưởng giữa hai đỉnh: đủ thưa để chữ không đè nhau, đủ chặt để
  // cả đồ thị vẫn vừa một màn hình khi số đỉnh tăng.
  const k = Math.sqrt((width * height) / (nodes.length + 1)) * 0.62;

  nodes.forEach((n, i) => {
    const goc = (i / nodes.length) * Math.PI * 2;
    const r = (0.28 + hash(n.id) * 0.34) * Math.min(width, height);
    pos.set(n.id, { x: cx + Math.cos(goc) * r, y: cy + Math.sin(goc) * r, vx: 0, vy: 0 });
  });

  const canhs = links
    .map((l) => [pos.get(l.source), pos.get(l.target)])
    .filter(([a, b]) => a && b);

  for (let buoc = 0; buoc < iterations; buoc++) {
    // Nguội dần: bước đầu cho phép nhảy xa để gỡ rối, về sau chỉ chỉnh li ti.
    const nhiet = (1 - buoc / iterations) ** 1.5;

    // SỬA TẠI CHỖ, tuyệt đối không `pos.set(id, {...})`. Bản đầu tạo object mới
    // ở mỗi cặp, và hỏng hai lần cùng lúc: lực đẩy của đỉnh i bị ghi đè nên chỉ
    // còn lại cặp cuối cùng, còn `canhs` thì đang giữ tham chiếu tới những
    // object đã bị thay — nên lực lò xo của CẠNH không bao giờ tác dụng. Đo
    // được: bỏ hết cạnh đi mà toạ độ trả về vẫn y hệt, tức đồ thị xếp như thể
    // không ai nối gì với ai.
    for (let i = 0; i < nodes.length; i++) {
      const a = pos.get(nodes[i].id);
      for (let j = i + 1; j < nodes.length; j++) {
        const b = pos.get(nodes[j].id);
        let dx = a.x - b.x;
        let dy = a.y - b.y;
        let d2 = dx * dx + dy * dy;
        if (d2 < 0.01) {
          // Hai đỉnh trùng khít thì lực đẩy chia cho 0. Đẩy lệch một chút theo
          // hướng cố định để lần chạy sau vẫn ra đúng kết quả này.
          dx = 0.1;
          dy = 0.1;
          d2 = 0.02;
        }
        const day = (k * k) / d2;
        a.vx += dx * day;
        a.vy += dy * day;
        b.vx -= dx * day;
        b.vy -= dy * day;
      }
    }

    for (const [a, b] of canhs) {
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const d = Math.hypot(dx, dy) || 0.01;
      // Lò xo có KHOẢNG NGHỈ: gần hơn ngần này thì thôi kéo nữa. Lò xo kéo vô
      // điều kiện thì hai đỉnh có nối dính sát vào nhau và hai cái nhãn chồng
      // lên nhau — đo được ngay sau khi sửa lực lò xo: token và context còn
      // cách nhau ~30px, đọc không ra chữ nào.
      if (d <= NGHI) continue;
      const keo = ((d - NGHI) * (d - NGHI)) / k / d;
      a.vx += dx * keo * 0.5;
      a.vy += dy * keo * 0.5;
      b.vx -= dx * keo * 0.5;
      b.vy -= dy * keo * 0.5;
    }

    for (const n of nodes) {
      const p = pos.get(n.id);
      // Đỉnh nặng (giảng lại nhiều lần) ì hơn, nên nó nằm giữa và những đỉnh
      // mới học dạt ra rìa — bản đồ tự sắp theo mức vững của người học.
      const i = 1 / (1 + (n.weight ?? 1) * 0.6);
      const buocDi = Math.min(k * 0.55, Math.hypot(p.vx, p.vy)) * nhiet * i;
      const huong = Math.hypot(p.vx, p.vy) || 1;
      p.x += (p.vx / huong) * buocDi;
      p.y += (p.vy / huong) * buocDi;
      // Kéo nhẹ về tâm, nếu không các cụm rời nhau sẽ trôi ra vô tận.
      p.x += (cx - p.x) * 0.012;
      p.y += (cy - p.y) * 0.012;
      p.vx = 0;
      p.vy = 0;
    }
  }

  // Dời cả cụm về giữa khung. Không có bước này thì một đồ thị ít đỉnh nằm lệch
  // hẳn một góc, để trống nửa màn hình — nhìn như hỏng chứ không như thưa.
  const xs = [...pos.values()].map((p) => p.x);
  const ys = [...pos.values()].map((p) => p.y);
  const dx = cx - (Math.min(...xs) + Math.max(...xs)) / 2;
  const dy = cy - (Math.min(...ys) + Math.max(...ys)) / 2;

  const bo = 60;
  for (const p of pos.values()) {
    p.x = Math.max(bo, Math.min(width - bo, p.x + dx));
    p.y = Math.max(bo, Math.min(height - bo, p.y + dy));
  }
  return pos;
}

/**
 * Vùng tối xếp thành MỘT VÀNH đều quanh cụm sáng, không thả vào lò xo.
 *
 * Thả chung thì hai chuyện hỏng cùng lúc: nhãn của chúng đè lên nhau thành một
 * đám chữ không đọc được (đo thật: 33 đỉnh mờ, chữ chồng chữ), và chúng chen
 * vào giữa làm loãng đúng phần đáng nhìn. Vành ngoài thì không bao giờ chồng
 * nhau vì góc chia đều, và đọc lên đúng nghĩa: thứ mình đã dạy nằm trong, thứ
 * chưa chạm tới nằm ngoài rìa.
 */
export function ringLayout(ids, { width = 900, height = 620, radius = 0.42 } = {}) {
  const pos = new Map();
  const cx = width / 2;
  const cy = height / 2;
  const rx = width * radius;
  const ry = height * radius;
  ids.forEach((id, i) => {
    // Bắt đầu từ -90° cho đỉnh đầu nằm chính giữa phía trên, nhìn cân hơn.
    const goc = -Math.PI / 2 + (i / Math.max(ids.length, 1)) * Math.PI * 2;
    pos.set(id, { x: cx + Math.cos(goc) * rx, y: cy + Math.sin(goc) * ry });
  });
  return pos;
}
