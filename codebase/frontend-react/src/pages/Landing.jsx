// Trang giới thiệu: một câu nói sản phẩm làm gì, cho xem nó chạy, rồi vào học.
//
// Cố ý ngắn. Người mở trang là thành viên được gửi link để thử, không phải
// khách cần thuyết phục — mỗi đoạn chữ thêm vào là thêm một thứ đứng giữa họ
// và nút "Bắt đầu học".
//
// Nội dung minh hoạ (overfitting) là ví dụ tự viết, CỐ Ý không lấy từ slide của
// khoá: trang này công khai, tài liệu khoá học chỉ nằm sau đăng nhập.

import {
  AnimatePresence,
  motion,
  useInView,
  useMotionValueEvent,
  useReducedMotion,
  useScroll,
} from "motion/react";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "../auth";
import { blurIn, EASE } from "../motion";
import { Brand, LinkButton, Reveal } from "../site";
import { Kbd, LevelMeter, Stepper } from "../ui";

const STAGES = ["Chọn", "Giảng", "Trả lời", "Xem lại"];

export default function Landing() {
  return (
    <div className="min-h-screen bg-white font-sans text-neutral-900 antialiased">
      <Nav />
      <main>
        <Hero />
        <Steps />
        <Principles />
      </main>
      <Footer />
    </div>
  );
}

function Nav() {
  const { status } = useAuth();
  const { scrollY } = useScroll();
  const [scrolled, setScrolled] = useState(false);
  useMotionValueEvent(scrollY, "change", (y) => setScrolled(y > 8));

  return (
    <header
      className={`sticky top-0 z-40 border-b bg-white/85 backdrop-blur-md transition-colors ${
        scrolled ? "border-neutral-200" : "border-transparent"
      }`}
    >
      <div className="mx-auto flex h-14 max-w-6xl items-center gap-8 px-4 sm:px-6">
        <Brand />
        <nav className="hidden items-center gap-6 text-[13px] text-neutral-500 md:flex">
          <a href="#how" className="transition-colors hover:text-neutral-900">
            Cách hoạt động
          </a>
          <a href="#principles" className="transition-colors hover:text-neutral-900">
            Nguyên tắc
          </a>
        </nav>
        <div className="ml-auto">
          {status === "in" ? (
            <LinkButton to="/library">Vào thư viện</LinkButton>
          ) : (
            <LinkButton to="/login" variant="normal">
              Đăng nhập
            </LinkButton>
          )}
        </div>
      </div>
    </header>
  );
}

function Hero() {
  return (
    <section className="px-4 pt-20 sm:px-6 sm:pt-28">
      <div className="mx-auto max-w-3xl text-center">
        <motion.h1
          initial={{ opacity: 0, y: 10, filter: "blur(8px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          transition={{ duration: 0.8, ease: EASE }}
          className="m-0 text-[40px] leading-[1.04] font-semibold tracking-[-0.04em] text-balance sm:text-[64px]"
        >
          Hiểu bài bằng cách giảng lại.
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 8, filter: "blur(6px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          transition={{ duration: 0.7, delay: 0.12, ease: EASE }}
          className="mx-auto mt-5 mb-0 max-w-xl text-[16px] leading-relaxed text-balance text-neutral-500 sm:text-[18px]"
        >
          Chọn một phần trong slide và giảng lại bằng lời của bạn. Học trò AI hỏi vào đúng chỗ bạn chưa nắm chắc.
        </motion.p>
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.24, ease: EASE }}
          className="mt-9 flex flex-wrap items-center justify-center gap-2.5"
        >
          <LinkButton to="/library" size="lg">
            Bắt đầu học
          </LinkButton>
          <LinkButton href="#how" variant="normal" size="lg">
            Cách hoạt động
          </LinkButton>
        </motion.div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 32, filter: "blur(10px)" }}
        animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
        transition={{ duration: 1, delay: 0.3, ease: EASE }}
        className="mx-auto mt-16 max-w-5xl sm:mt-20"
      >
        <HeroDemo />
      </motion.div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Bản chạy thử: một vòng giảng đầy đủ, dựng đúng bằng giao diện của app.

/** Thời lượng từng cảnh (ms): chọn vùng · câu mở đầu · học viên giảng · đối
 *  chiếu · học trò hỏi lại · mở lại nguồn. */
const SCENES = [2200, 1800, 3000, 1500, 3800, 2600];
const STAGE_OF_SCENE = [0, 1, 1, 2, 2, 3];

function useScene(ref) {
  const inView = useInView(ref, { margin: "-10% 0px" });
  const reduce = useReducedMotion();
  const [scene, setScene] = useState(0);

  useEffect(() => {
    // Ra khỏi màn hình thì dừng: không đốt CPU cho thứ không ai xem.
    if (reduce || !inView) return;
    const id = setTimeout(() => setScene((s) => (s + 1) % SCENES.length), SCENES[scene]);
    return () => clearTimeout(id);
  }, [scene, inView, reduce]);

  // Giảm chuyển động: đứng yên ở cảnh nói được nhiều nhất.
  return reduce ? 4 : scene;
}

function HeroDemo() {
  const ref = useRef(null);
  const scene = useScene(ref);

  return (
    <div
      ref={ref}
      className="overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-[0_1px_2px_rgb(0_0_0/0.04),0_40px_80px_-40px_rgb(0_0_0/0.25)]"
    >
      <div className="grid md:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)]">
        <div className="order-2 h-[360px] border-neutral-200 md:order-none md:h-[420px] md:border-r">
          <DemoConversation scene={scene} />
        </div>
        <div className="order-1 flex flex-col border-b border-neutral-200 bg-neutral-50 md:order-none md:border-b-0">
          <div className="flex h-12 shrink-0 items-center justify-between border-b border-neutral-200 bg-white px-4">
            <span className="text-[13px] font-medium text-neutral-900">Overfitting</span>
            <span className="text-[12px] tabular-nums text-neutral-400">7 / 12</span>
          </div>
          <div className="grid flex-1 place-items-center p-5 sm:p-8">
            <DemoSlide scene={scene} />
          </div>
        </div>
      </div>
    </div>
  );
}

function Bars({ widths }) {
  return (
    <div className="space-y-1.5">
      {widths.map((w, i) => (
        <div key={i} className="h-1.5 rounded-full bg-neutral-200" style={{ width: `${w}%` }} />
      ))}
    </div>
  );
}

function DemoSlide({ scene }) {
  const covered = scene >= 1 && scene <= 4;
  const opened = scene === 5;

  return (
    <div className="aspect-[16/10] w-full rounded-lg bg-white p-[6%] shadow-[0_1px_3px_rgb(0_0_0/0.06)] ring-1 ring-neutral-200">
      <div className="h-2.5 w-1/3 rounded-full bg-neutral-800" />
      <div className="mt-2 h-1.5 w-1/2 rounded-full bg-neutral-200" />
      <div className="mt-[7%] grid grid-cols-2 gap-[7%]">
        <div className="space-y-4">
          <div className="relative">
            <div className="space-y-3">
              <Bars widths={[100, 90, 62]} />
              <Bars widths={[96, 74]} />
            </div>
            <AnimatePresence>
              {scene === 0 && (
                // Khung kéo mọc từ góc trên-trái xuống góc dưới-phải, như lúc kéo chuột thật.
                <motion.div
                  key="drag"
                  className="absolute -inset-2 rounded-md border border-neutral-900 bg-neutral-900/[0.04]"
                  initial={{ clipPath: "inset(0% 100% 100% 0%)" }}
                  animate={{ clipPath: "inset(0% 0% 0% 0%)" }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 1.1, delay: 0.4, ease: EASE }}
                />
              )}
              {covered && (
                <motion.div
                  key="cover"
                  className="cover absolute -inset-2 rounded-md"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0, filter: "blur(6px)" }}
                  transition={{ duration: 0.45, ease: EASE }}
                />
              )}
              {opened && (
                <motion.div
                  key="open"
                  className="absolute -inset-2 rounded-md bg-neutral-900/[0.04] ring-2 ring-neutral-900"
                  initial={{ opacity: 0, scale: 1.08 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.6, delay: 0.2, ease: EASE }}
                />
              )}
            </AnimatePresence>
          </div>
          <Bars widths={[88, 56]} />
        </div>
        <DemoChart />
      </div>
    </div>
  );
}

/** Hình tự vẽ: lỗi trên dữ liệu huấn luyện giảm mãi, lỗi trên dữ liệu mới giảm rồi tăng. */
function DemoChart() {
  return (
    <svg viewBox="0 0 120 80" className="h-full w-full" aria-hidden="true">
      <path d="M8 6 V72 H116" fill="none" stroke="#d4d4d4" strokeWidth="1.2" />
      <path d="M12 16 C 36 44, 60 60, 112 68" fill="none" stroke="#a3a3a3" strokeWidth="2" strokeLinecap="round" />
      <path
        d="M12 20 C 34 46, 52 54, 66 52 S 96 36, 112 22"
        fill="none"
        stroke="#171717"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

function DemoConversation({ scene }) {
  const [level, setLevel] = useState(0);
  const talking = scene === 2;

  useEffect(() => {
    if (!talking) return;
    const id = setInterval(() => setLevel(0.25 + Math.random() * 0.7), 140);
    return () => clearInterval(id);
  }, [talking]);

  return (
    <div className="flex h-full flex-col">
      <div className="shrink-0 border-b border-neutral-200 px-4 pt-3 pb-2.5">
        <Stepper steps={STAGES} current={STAGE_OF_SCENE[scene]} />
      </div>

      <div className="relative min-h-0 flex-1 overflow-hidden [mask-image:linear-gradient(to_bottom,transparent,black_18%)]">
        <div className="absolute inset-x-0 bottom-0 space-y-4 p-4">
          <AnimatePresence mode="popLayout" initial={false}>
            {scene === 0 && (
              <motion.div key="ready" {...blurIn} className="space-y-3">
                <div>
                  <p className="m-0 text-[12px] text-neutral-400">Slide 7 · 2 phần đã chọn</p>
                  <p className="m-0 mt-0.5 text-[16px] font-semibold tracking-tight text-neutral-900">Overfitting</p>
                </div>
                <span className="inline-flex h-9 items-center gap-2 rounded-lg bg-neutral-900 px-3.5 text-[13px] font-medium text-white">
                  Bắt đầu giảng
                </span>
              </motion.div>
            )}
            {scene >= 1 && (
              <motion.p key="opener" layout {...blurIn} className="m-0 text-[14px] leading-relaxed text-neutral-800">
                Overfitting là gì vậy bạn? Mình chưa hình dung được.
              </motion.p>
            )}
            {scene >= 2 && (
              <motion.div key="student" layout {...blurIn} className="flex justify-end">
                <p className="m-0 max-w-[88%] rounded-2xl rounded-br-md bg-neutral-100 px-3.5 py-2.5 text-[14px] leading-relaxed text-neutral-900">
                  Là khi mô hình học thuộc dữ liệu huấn luyện, nên gặp dữ liệu mới thì đoán sai.
                </p>
              </motion.div>
            )}
            {scene === 3 && (
              <motion.p key="thinking" layout {...blurIn} className="m-0 text-[12px]">
                <span className="shimmer font-medium">Đối chiếu với slide</span>
              </motion.p>
            )}
            {scene >= 4 && (
              <motion.div key="reply" layout {...blurIn} className="space-y-3">
                <div className="border-l-2 border-neutral-200 pl-3">
                  <p className="m-0 text-[12px] text-neutral-400">Mình hiểu là</p>
                  <p className="m-0 mt-0.5 text-[13px] text-neutral-600">Mô hình nhớ quá kỹ dữ liệu huấn luyện.</p>
                </div>
                <p className="m-0 text-[14px] leading-relaxed text-neutral-800">
                  Nhưng vì sao nhớ kỹ lại làm đoán kém đi?
                </p>
                <div className="flex items-center gap-2.5 rounded-xl border border-neutral-200 p-2">
                  <span className="grid size-8 place-items-center rounded-lg bg-neutral-100 text-[12px] font-semibold tabular-nums text-neutral-700">
                    7
                  </span>
                  <span className="min-w-0 flex-1 text-[13px] text-neutral-700">Chỗ cần xem lại</span>
                  <span
                    className={`rounded-md border px-2 py-0.5 text-[12px] font-medium transition-colors duration-300 ${
                      scene === 5 ? "border-neutral-900 bg-neutral-900 text-white" : "border-neutral-200 text-neutral-700"
                    }`}
                  >
                    Xem
                  </span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Ô trả lời chỉ có khi đã vào phiên, giống app. */}
      <div className={`shrink-0 border-t border-neutral-200 p-3 transition-opacity duration-300 ${scene === 0 ? "opacity-0" : ""}`}>
        <div
          className={`flex h-10 items-center justify-between rounded-xl border px-3 text-[13px] transition-colors ${
            talking ? "border-neutral-900" : "border-neutral-200 text-neutral-400"
          }`}
        >
          {talking ? <LevelMeter level={level} /> : <span>Nhập câu trả lời</span>}
          <Kbd>Space</Kbd>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------

function SectionHead({ eyebrow, title }) {
  return (
    <Reveal>
      <p className="m-0 text-[13px] font-medium text-neutral-400">{eyebrow}</p>
      <h2 className="m-0 mt-2 max-w-xl text-[30px] leading-[1.1] font-semibold tracking-[-0.03em] text-balance sm:text-[40px]">
        {title}
      </h2>
    </Reveal>
  );
}

const STEPS = [
  {
    title: "Chọn nội dung",
    body: "Kéo chọn một đoạn chữ hoặc sơ đồ. Phần đã chọn được che lại.",
    visual: <SelectVisual />,
  },
  {
    title: "Giảng lại",
    body: "Nói hoặc gõ lời giải thích của bạn, không nhìn slide.",
    visual: <SpeakVisual />,
  },
  {
    title: "Trả lời câu hỏi",
    body: "Học trò hỏi vào chỗ còn thiếu và chỉ ra vị trí cần xem lại.",
    visual: <SourceVisual />,
  },
];

function Steps() {
  return (
    <section id="how" className="scroll-mt-14 px-4 py-24 sm:px-6 sm:py-32">
      <div className="mx-auto max-w-5xl">
        <SectionHead eyebrow="Cách hoạt động" title="Ba bước để biết mình hiểu tới đâu." />
        <div className="mt-12 grid gap-4 md:grid-cols-3">
          {STEPS.map((step, i) => (
            <Reveal key={step.title} delay={i * 0.08}>
              <div className="h-full rounded-2xl border border-neutral-200 p-5">
                <div className="grid h-40 place-items-center rounded-xl bg-neutral-50">{step.visual}</div>
                <h3 className="m-0 mt-5 text-[16px] font-semibold tracking-tight">{step.title}</h3>
                <p className="m-0 mt-1 text-[14px] leading-relaxed text-neutral-500">{step.body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

function SelectVisual() {
  return (
    <div className="w-40 space-y-3">
      <Bars widths={[80, 60]} />
      <div className="relative">
        <Bars widths={[100, 92, 70]} />
        <motion.div
          className="absolute -inset-2 rounded-md border border-neutral-900 bg-neutral-900/[0.04]"
          initial={{ clipPath: "inset(0% 100% 100% 0%)" }}
          whileInView={{ clipPath: ["inset(0% 100% 100% 0%)", "inset(0% 0% 0% 0%)", "inset(0% 0% 0% 0%)"] }}
          transition={{ duration: 2.6, times: [0, 0.45, 1], repeat: Infinity, repeatDelay: 0.6, ease: EASE }}
        />
      </div>
      <Bars widths={[66]} />
    </div>
  );
}

function SpeakVisual() {
  return (
    <div className="w-40 space-y-3">
      <div className="cover h-11 rounded-md" />
      <div className="flex h-9 items-center justify-center gap-[3px] rounded-lg bg-white ring-1 ring-neutral-900">
        {Array.from({ length: 14 }, (_, i) => (
          <motion.span
            key={i}
            className="w-[3px] rounded-full bg-neutral-900"
            animate={{ height: [4, 6 + ((i * 7) % 11), 4] }}
            transition={{ duration: 0.9 + (i % 4) * 0.15, repeat: Infinity, ease: "easeInOut", delay: i * 0.05 }}
          />
        ))}
      </div>
    </div>
  );
}

function SourceVisual() {
  return (
    <div className="w-44 space-y-2">
      <div className="relative rounded-md bg-white p-2.5 ring-1 ring-neutral-200">
        <Bars widths={[70, 100, 84]} />
        <motion.div
          className="absolute inset-x-1.5 top-[38%] bottom-1.5 rounded ring-2 ring-neutral-900"
          animate={{ opacity: [0.2, 1, 0.2] }}
          transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
        />
      </div>
      <div className="flex items-center gap-2 rounded-md bg-white p-1.5 ring-1 ring-neutral-200">
        <span className="grid size-5 place-items-center rounded bg-neutral-100 text-[10px] font-semibold">7</span>
        <span className="flex-1 text-[10px] text-neutral-500">Chỗ cần xem lại</span>
        <span className="rounded bg-neutral-900 px-1.5 text-[10px] font-medium text-white">Xem</span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------

const PRINCIPLES = [
  ["Không trả lời thay", "Kể cả khi được hỏi thẳng, học trò chỉ đặt câu hỏi."],
  ["Bám sát tài liệu", "Lời giảng được đối chiếu với đúng phần slide bạn chọn."],
  ["Không lộ đáp án", "Học trò chỉ ra chỗ cần xem lại, không trích nguyên văn."],
  ["Chỉ thu âm khi bạn nói", "Mic chỉ hoạt động khi bạn giữ nút nói."],
];

const REFERENCES = [
  "Rozenblit & Keil, 2002",
  "Chase và cộng sự, 2009",
  "Chi & Wylie, 2014",
  "Jin và cộng sự, CHI 2024",
];

function Principles() {
  return (
    <section id="principles" className="scroll-mt-14 border-t border-neutral-200 px-4 py-24 sm:px-6 sm:py-32">
      <div className="mx-auto grid max-w-5xl gap-12 md:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        <SectionHead eyebrow="Nguyên tắc" title="Bạn tự hiểu. AI không làm thay." />
        <dl className="m-0 grid gap-x-10 gap-y-8 sm:grid-cols-2">
          {PRINCIPLES.map(([title, body], i) => (
            <Reveal key={title} delay={i * 0.06} className="border-t border-neutral-900 pt-4">
              <dt className="text-[15px] font-semibold tracking-tight">{title}</dt>
              <dd className="m-0 mt-1 text-[14px] leading-relaxed text-neutral-500">{body}</dd>
            </Reveal>
          ))}
        </dl>
      </div>
      <Reveal className="mx-auto mt-20 max-w-5xl text-[13px] text-neutral-400">
        Cơ sở nghiên cứu: {REFERENCES.join(" · ")}
      </Reveal>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-neutral-200">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-3 px-4 py-8 text-[13px] text-neutral-500 sm:px-6">
        <Brand />
        <p className="m-0 sm:ml-auto">Kẻ Độc Hành · VinUni AI20k</p>
      </div>
    </footer>
  );
}
