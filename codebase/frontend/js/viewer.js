// Chọn trình xem theo loại bài, và cho phần còn lại của app một địa chỉ duy
// nhất để gọi.
//
// Không có lớp này thì mọi chỗ cần "nhảy tới nguồn" đều phải tự hỏi "bài này
// là slide hay code?" — rẽ nhánh rải khắp nơi, và thêm loại bài thứ ba là sửa
// lại từng chỗ.

let active = null;

export async function mount(lesson, hosts) {
  if (lesson.kind === "code") {
    active = await import("./code.js");
    hosts.slide.hidden = true;
    hosts.code.hidden = false;
    await active.loadCode(lesson, hosts.code);
  } else {
    active = await import("./slides.js");
    hosts.code.hidden = true;
    hosts.slide.hidden = false;
    await active.loadSlides(`${hosts.api}/slides.pdf`, lesson.spans);
  }
  return active;
}

export const isCode = () => Boolean(active?.currentCode);
export const currentCode = () => active?.currentCode?.() ?? "";

export const show = (page) => active?.show?.(page);
export const step = (delta) => active?.step?.(delta);
export const setZoom = (delta) => active?.setZoom?.(delta);
export const sourcePage = () => active?.sourcePage?.() ?? 1;
export const focusSpan = (spanId) => active?.focusSpan?.(spanId);
