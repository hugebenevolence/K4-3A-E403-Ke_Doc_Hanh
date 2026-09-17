// Trang giới thiệu: nói sản phẩm làm gì trong một câu, cho xem nó chạy, rồi
// đưa thẳng vào thư viện slide.
//
// Nội dung minh hoạ (khái niệm overfitting, câu hỏi của học trò) là ví dụ tự
// viết, CỐ Ý không lấy từ slide của khoá: trang này công khai, còn tài liệu
// khoá học chỉ nằm sau đăng nhập.

import {
  AnimatePresence,
  LayoutGroup,
  motion,
  useInView,
  useMotionValueEvent,
  useReducedMotion,
  useScroll,
  useTransform,
} from "motion/react";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "../auth";
import { blurIn, EASE } from "../motion";
import { Brand, DotGrid, LinkButton, Reveal } from "../site";
import { Kbd, LevelMeter, RotatingWords, WordsIn } from "../ui";

const TERMS = ["attention", "overfitting", "token", "embedding", "context window", "RLHF"];

export default function Landing() {
  return (
    <div className="min-h-screen bg-white font-sans text-neutral-900 antialiased">
      <Nav />
      <Hero />
      <HowItWorks />
      <Statement />
      <Research />
      <Principles />
      <Cta />
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
      className={`sticky top-0 z-40 border-b bg-white/80 backdrop-blur-md transition-colors ${
        scrolled ? "border-neutral-200" : "border-transparent"
      }`}
    >
      <div className="mx-auto flex h-14 max-w-6xl items-center gap-6 px-4 sm:px-6">
        <Brand />
        <nav className="hidden items-center gap-1 md:flex">
          {[
            ["#how", "Cách hoạt động"],
            ["#why", "Vì sao hiệu quả"],
            ["#rules", "Nguyên tắc"],
          ].map(([href, label]) => (
            <a
              key={href}
              href={href}
              className="rounded-full px-3 py-1.5 text-[13px] text-neutral-600 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
            >
              {label}
            </a>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-1.5">
          {status !== "in" && (
            <LinkButton to="/login" variant="quiet" className="hidden sm:inline-flex">
              Đăng nhập
            </LinkButton>
          )}
          <LinkButton to="/library">{status === "in" ? "Vào thư viện" : "Học thử"}</LinkButton>
        </div>
      </div>
    </header>
  );
}

function Hero() {
  return (
    <section className="relative overflow-hidden">
      <DotGrid className="h-[640px]" />
      <div className="relative mx-auto max-w-4xl px-4 pt-16 text-center sm:px-6 sm:pt-24">
        <motion.span
          {...blurIn}
          className="inline-flex items-center gap-2 rounded-full border border-neutral-200 bg-white px-3 py-1 text-[12px] text-neutral-600 shadow-[0_1px_2px_rgb(0_0_0/0.04)]"
        >
          <span className="pulse size-1.5 rounded-full bg-neutral-900" data-mode="listening" />
          Bản thử nghiệm nội bộ · Mini Hackathon AI Batch 04
        </motion.span>

        <motion.h1
          initial={{ opacity: 0, y: 12, filter: "blur(10px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          transition={{ duration: 0.8, delay: 0.05, ease: EASE }}
          className="m-0 mt-6 text-[34px] leading-[1.08] font-semibold tracking-[-0.035em] text-balance sm:text-[64px] sm:leading-[1.05]"
        >
          Giảng lại <RotatingWords words={TERMS} className="text-neutral-400" />
          <br />
          cho đến khi hiểu thật.
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 8, filter: "blur(6px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          transition={{ duration: 0.7, delay: 0.2, ease: EASE }}
          className="mx-auto mt-5 mb-0 max-w-xl text-[16px] leading-relaxed text-pretty text-neutral-500 sm:text-[17px]"
        >
          Chọn một phần trên slide và nói lại bằng lời của bạn. Học trò AI nghe, hỏi ngược đúng chỗ bạn giảng
          còn mỏng — và không bao giờ giảng hộ.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.32, ease: EASE }}
          className="mt-8 flex flex-wrap items-center justify-center gap-2.5"
        >
          <LinkButton to="/library" size="lg">
            Chọn slide để học
          </LinkButton>
          <LinkButton href="#how" variant="normal" size="lg">
            Xem cách hoạt động
          </LinkButton>
        </motion.div>
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.45 }}
          className="m-0 mt-4 flex items-center justify-center gap-1.5 text-[12px] text-neutral-400"
        >
          Giữ <Kbd>Space</Kbd> để nói · đang ngồi trong lớp thì gõ chữ
        </motion.p>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 40, filter: "blur(12px)" }}
        animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
        transition={{ duration: 1, delay: 0.35, ease: EASE }}
        className="relative mx-auto mt-14 max-w-5xl px-4 pb-8 sm:mt-16 sm:px-6"
      >
        <HeroDemo />
      </motion.div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Bản chạy thử trong khung trình duyệt: một vòng Feynman đầy đủ, lặp lại.

/** Thời lượng từng cảnh (ms): chọn vùng · mở bài · học viên giảng · đối chiếu ·
 *  học trò hỏi ngược · mở lại nguồn. */
const SCENES = [2000, 1700, 2800, 1600, 3800, 2600];

const PHASES = ["Chọn vùng", "Giảng lại", "Học trò hỏi", "Mở lại nguồn"];
const PHASE_OF_SCENE = [0, 1, 1, 2, 2, 3];

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
    <div ref={ref}>
      <div className="overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-[0_40px_100px_-40px_rgb(0_0_0/0.3)]">
        <div className="flex h-10 items-center gap-1.5 border-b border-neutral-200 bg-neutral-50 px-4">
          <span className="size-2.5 rounded-full bg-neutral-200" />
          <span className="size-2.5 rounded-full bg-neutral-200" />
          <span className="size-2.5 rounded-full bg-neutral-200" />
          <span className="mx-auto rounded-md bg-white px-3 py-0.5 text-[11px] text-neutral-400 ring-1 ring-neutral-200">
            Giảng lại · Slide 7
          </span>
        </div>
        <div className="grid md:grid-cols-[170px_minmax(0,1fr)_minmax(0,1.1fr)]">
          <DemoSidebar />
          <div className="order-2 h-[330px] border-neutral-200 md:order-none md:h-[380px] md:border-r">
            <DemoConversation scene={scene} />
          </div>
          <div className="order-1 border-b border-neutral-200 bg-neutral-50/60 p-4 sm:p-6 md:order-none md:border-b-0">
            <p className="m-0 text-[13px] font-semibold text-neutral-900">Overfitting</p>
            <p className="m-0 mb-3 text-[11px] text-neutral-400">Bài ví dụ · trang 7</p>
            <DemoSlide scene={scene} />
          </div>
        </div>
      </div>

      <LayoutGroup id="demo-phases">
        <div className="mt-5 flex flex-wrap justify-center gap-1">
          {PHASES.map((label, i) => {
            const on = PHASE_OF_SCENE[scene] === i;
            return (
              <span
                key={label}
                className={`relative rounded-full px-3 py-1 text-[12px] transition-colors duration-300 ${on ? "text-white" : "text-neutral-400"}`}
              >
                {on && (
                  <motion.span
                    layoutId="demo-phase"
                    className="absolute inset-0 rounded-full bg-neutral-900"
                    transition={{ duration: 0.45, ease: EASE }}
                  />
                )}
                <span className="relative tabular-nums">
                  {i + 1}. {label}
                </span>
              </span>
            );
          })}
        </div>
      </LayoutGroup>
    </div>
  );
}

function DemoSidebar() {
  return (
    <div className="hidden border-r border-neutral-200 bg-neutral-50/70 p-3 md:block">
      <p className="m-0 px-1.5 text-[11px] font-medium text-neutral-400">Slide</p>
      <ol className="m-0 mt-1.5 list-none space-y-0.5 p-0">
        {[62, 80, 54, 70, 48, 76, 58, 66].map((w, i) => {
          const active = i === 6;
          return (
            <li
              key={i}
              className={`flex items-center gap-2 rounded-md px-1.5 py-1.5 ${active ? "bg-white shadow-sm ring-1 ring-neutral-200" : ""}`}
            >
              <span className="w-3 text-right text-[10px] tabular-nums text-neutral-400">{i + 1}</span>
              <span
                className={`h-1.5 rounded-full ${active ? "bg-neutral-800" : "bg-neutral-200"}`}
                style={{ width: `${w}%` }}
              />
            </li>
          );
        })}
      </ol>
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
                // Khung kéo "mọc" từ góc trên-trái xuống góc dưới-phải, như lúc
                // học viên kéo chuột thật.
                <motion.div
                  key="drag"
                  className="absolute -inset-2 rounded-md border-[1.5px] border-dashed border-neutral-900 bg-neutral-900/[0.04]"
                  initial={{ clipPath: "inset(0% 100% 100% 0%)" }}
                  animate={{ clipPath: "inset(0% 0% 0% 0%)" }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 1.1, delay: 0.35, ease: EASE }}
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

/** Hình minh hoạ tự vẽ: lỗi trên dữ liệu huấn luyện giảm mãi, lỗi trên dữ liệu
 *  mới giảm rồi tăng lại. */
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
      <path d="M62 10 V70" stroke="#171717" strokeWidth="1" strokeDasharray="2 3" opacity="0.4" />
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
      <div className="flex h-10 shrink-0 items-center border-b border-neutral-200 px-4 text-[12px] font-medium text-neutral-900">
        {scene === 0 ? "Phiên giảng mới" : "Overfitting"}
      </div>

      <div className="relative min-h-0 flex-1 overflow-hidden [mask-image:linear-gradient(to_bottom,transparent,black_22%)]">
        <div className="absolute inset-x-0 bottom-0 space-y-3 p-4">
          <AnimatePresence mode="popLayout" initial={false}>
            {scene === 0 && (
              <motion.p key="hint" {...blurIn} className="m-0 text-[13px] text-neutral-400">
                Kéo khung trên slide để chọn phần bạn muốn giảng.
              </motion.p>
            )}
            {scene >= 1 && (
              <motion.div key="opener" layout {...blurIn} className="space-y-1">
                <p className="m-0 text-[11px] text-neutral-400">
                  Đã nghĩ trong 2s · <span className="font-medium text-neutral-600">Học trò AI</span>
                </p>
                <p className="m-0 text-[13px] leading-relaxed text-neutral-800">
                  Mình chưa hiểu phần này lắm. Bạn giảng giúp mình: overfitting là gì vậy?
                </p>
              </motion.div>
            )}
            {scene >= 2 && (
              <motion.div key="student" layout {...blurIn} className="flex justify-end">
                <p className="m-0 max-w-[88%] rounded-2xl rounded-br-md bg-neutral-100 px-3 py-2 text-[13px] leading-relaxed text-neutral-900">
                  <WordsIn text="Là khi mô hình học thuộc lòng dữ liệu huấn luyện, nên gặp dữ liệu mới thì đoán sai." />
                </p>
              </motion.div>
            )}
            {scene === 3 && (
              <motion.p key="thinking" layout {...blurIn} className="m-0 flex items-center gap-2 text-[11px]">
                <span className="shimmer font-medium">Đang đối chiếu với slide…</span>
                <span className="text-neutral-400">Người đối chiếu</span>
              </motion.p>
            )}
            {scene >= 4 && (
              <motion.div key="reply" layout {...blurIn} className="space-y-2">
                <p className="m-0 text-[11px] text-neutral-400">
                  Đã nghĩ trong 3s · <span className="font-medium text-neutral-600">Người đối chiếu</span>
                  <span className="text-neutral-300"> → </span>
                  <span className="font-medium text-neutral-600">Học trò AI</span>
                </p>
                <div className="rounded-lg bg-neutral-50 px-3 py-2">
                  <p className="m-0 text-[11px] font-medium text-neutral-500">Mình hiểu là</p>
                  <ul className="m-0 mt-0.5 list-none space-y-0.5 p-0 text-[12px] text-neutral-700">
                    <li>· Mô hình nhớ quá kỹ dữ liệu huấn luyện</li>
                    <li>· Nên đoán kém trên dữ liệu mới</li>
                  </ul>
                </div>
                <p className="m-0 text-[13px] leading-relaxed text-neutral-800">
                  Nhưng vì sao nhớ kỹ lại làm đoán kém đi? Mình tưởng nhớ càng nhiều càng tốt chứ?
                </p>
                <div className="flex items-center gap-2.5 rounded-lg border border-neutral-200 bg-white p-2">
                  <span className="grid size-7 place-items-center rounded-md bg-neutral-100 text-[11px] font-semibold text-neutral-700">
                    7
                  </span>
                  <span className="min-w-0 flex-1 leading-tight">
                    <span className="block text-[12px] font-medium text-neutral-900">Slide 7</span>
                    <span className="block truncate text-[11px] text-neutral-500">Chỗ học trò đang thắc mắc</span>
                  </span>
                  <span
                    className={`rounded-md border px-2 py-0.5 text-[11px] font-medium transition-colors duration-300 ${
                      scene === 5
                        ? "border-neutral-900 bg-neutral-900 text-white"
                        : "border-neutral-200 text-neutral-700"
                    }`}
                  >
                    Mở
                  </span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      <div className="shrink-0 border-t border-neutral-200 p-3">
        <div className="flex h-9 items-center justify-between rounded-xl border border-neutral-200 px-3 text-[12px] text-neutral-400">
          {talking ? <LevelMeter level={level} /> : <span>Giữ để nói</span>}
          <Kbd>Space</Kbd>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------

function SectionHead({ eyebrow, title, children }) {
  return (
    <Reveal className="mx-auto max-w-2xl text-center">
      <p className="m-0 text-[13px] font-medium text-neutral-400">{eyebrow}</p>
      <h2 className="m-0 mt-2 text-[30px] leading-[1.1] font-semibold tracking-[-0.03em] text-balance sm:text-[40px]">
        {title}
      </h2>
      {children && (
        <p className="m-0 mt-4 text-[15px] leading-relaxed text-pretty text-neutral-500 sm:text-[16px]">{children}</p>
      )}
    </Reveal>
  );
}

const STEPS = [
  {
    title: "Chọn phần muốn giảng",
    body: "Mở slide, kéo khung quanh đúng đoạn — chữ hay sơ đồ đều được. Không chọn gì thì giảng cả trang.",
    visual: <SelectVisual />,
  },
  {
    title: "Giảng khi phần đó bị che",
    body: "Vùng đã chọn được che lại. Bạn giảng bằng lời của mình, không nhìn slide mà đọc.",
    visual: <CoverVisual />,
  },
  {
    title: "Học trò hỏi đúng chỗ hổng",
    body: "Học trò AI nhắc lại ý bạn nói, rồi hỏi một câu “vì sao” hoặc “như thế nào” ở chỗ còn mỏng.",
    visual: <QuestionVisual />,
  },
  {
    title: "Mở lại nguồn, giảng lại",
    body: "Bí thì mở đúng vị trí trên slide mà học trò đang thắc mắc, đọc lại, rồi giảng lại lần nữa.",
    visual: <SourceVisual />,
  },
];

function HowItWorks() {
  return (
    <section id="how" className="scroll-mt-16 px-4 py-24 sm:px-6 sm:py-32">
      <SectionHead eyebrow="Cách hoạt động" title="Kỹ thuật Feynman, gói trong một màn hình">
        Đọc lại cho ta cảm giác đã hiểu. Giảng lại mới cho ta biết mình hiểu tới đâu — và học trò AI chỉ ra chỗ nào
        chưa tới.
      </SectionHead>

      <div className="mx-auto mt-14 grid max-w-6xl gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {STEPS.map((step, i) => (
          <Reveal key={step.title} delay={i * 0.08}>
            <motion.div
              whileHover={{ y: -3 }}
              transition={{ duration: 0.25, ease: EASE }}
              className="flex h-full flex-col rounded-2xl border border-neutral-200 bg-white p-5 transition-shadow hover:shadow-[0_12px_40px_-16px_rgb(0_0_0/0.18)]"
            >
              <div className="grid h-36 place-items-center overflow-hidden rounded-xl bg-neutral-50 ring-1 ring-inset ring-neutral-100">
                {step.visual}
              </div>
              <p className="m-0 mt-5 text-[12px] font-medium tabular-nums text-neutral-400">0{i + 1}</p>
              <h3 className="m-0 mt-1 text-[16px] font-semibold tracking-tight">{step.title}</h3>
              <p className="m-0 mt-1.5 text-[14px] leading-relaxed text-neutral-500">{step.body}</p>
            </motion.div>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

function SelectVisual() {
  return (
    <div className="relative w-36 space-y-3">
      <Bars widths={[80, 60]} />
      <div className="relative">
        <Bars widths={[100, 92, 70]} />
        <motion.div
          className="absolute -inset-2 rounded-md border-[1.5px] border-dashed border-neutral-900 bg-neutral-900/[0.04]"
          initial={{ clipPath: "inset(0% 100% 100% 0%)" }}
          whileInView={{ clipPath: ["inset(0% 100% 100% 0%)", "inset(0% 0% 0% 0%)", "inset(0% 0% 0% 0%)"] }}
          transition={{ duration: 2.6, times: [0, 0.45, 1], repeat: Infinity, repeatDelay: 0.6, ease: EASE }}
        />
      </div>
      <Bars widths={[66]} />
    </div>
  );
}

function CoverVisual() {
  return (
    <div className="w-36 space-y-3">
      <div className="cover h-12 rounded-md" />
      <div className="flex h-8 items-center justify-center gap-[3px] rounded-lg bg-white ring-1 ring-neutral-200">
        {Array.from({ length: 12 }, (_, i) => (
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

function QuestionVisual() {
  return (
    <div className="w-44 space-y-2">
      <div className="ml-auto w-32 rounded-xl rounded-br-sm bg-white px-2.5 py-2 ring-1 ring-neutral-200">
        <Bars widths={[100, 70]} />
      </div>
      <p className="m-0 text-[12px] leading-snug text-neutral-800">
        <span className="shimmer font-medium">Vì sao</span> nhớ kỹ lại làm đoán kém đi?
      </p>
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
          animate={{ opacity: [0.25, 1, 0.25] }}
          transition={{ duration: 2.2, repeat: Infinity, ease: "easeInOut" }}
        />
      </div>
      <div className="flex items-center gap-2 rounded-md bg-white p-1.5 ring-1 ring-neutral-200">
        <span className="grid size-5 place-items-center rounded bg-neutral-100 text-[10px] font-semibold">7</span>
        <span className="flex-1 text-[10px] text-neutral-500">Slide 7</span>
        <span className="rounded bg-neutral-900 px-1.5 text-[10px] font-medium text-white">Mở</span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------

const STATEMENT =
  "Đọc lại slide cho ta cảm giác đã hiểu. Chỉ khi phải giảng cho một người chưa biết gì, ta mới thấy mình hiểu tới đâu.";

/** Câu chữ sáng dần theo nhịp cuộn — người đọc đi cùng câu chữ, không lướt qua. */
function Statement() {
  const ref = useRef(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start 0.85", "end 0.5"] });
  const words = STATEMENT.split(" ");

  return (
    <section ref={ref} className="border-y border-neutral-100 bg-neutral-50/50 px-4 py-24 sm:px-6 sm:py-32">
      <p className="m-0 mx-auto max-w-4xl text-[28px] leading-[1.2] font-semibold tracking-[-0.03em] text-balance sm:text-[44px]">
        {words.map((word, i) => (
          <Word key={i} progress={scrollYProgress} range={[i / words.length, (i + 1) / words.length]}>
            {word}
          </Word>
        ))}
      </p>
    </section>
  );
}

function Word({ children, progress, range }) {
  const opacity = useTransform(progress, range, [0.15, 1]);
  return <motion.span style={{ opacity }}>{children} </motion.span>;
}

// ---------------------------------------------------------------------------

const STUDIES = [
  {
    cite: "Rozenblit & Keil, 2002 · Cognitive Science",
    title: "Ảo giác hiểu sâu",
    body: "Người ta thường tin mình hiểu một cơ chế rõ hơn thực tế — cho tới khi phải giải thích nó từng bước.",
  },
  {
    cite: "Chase, Chin, Oppezzo & Schwartz, 2009 · J. Sci. Educ. Technol.",
    title: "Hiệu ứng người được dạy",
    body: "Học viên chịu bỏ công nhiều hơn khi học để dạy lại cho một agent, so với khi chỉ học cho bản thân.",
  },
  {
    cite: "Chi & Wylie, 2014 · Educational Psychologist",
    title: "Khung ICAP",
    body: "Từ thụ động, chủ động, kiến tạo tới tương tác: mức tham gia càng cao thì hiểu càng sâu. Giảng lại và bị hỏi ngược nằm ở mức tương tác.",
  },
  {
    cite: "Jin, Lee, Shin & Kim, 2024 · CHI",
    title: "Học trò AI biết hỏi",
    body: "Một học trò dùng LLM được giữ ở đúng mức hiểu biết và chủ động đặt câu hỏi giúp người dạy nói ra nhiều lập luận hơn.",
  },
];

function Research() {
  return (
    <section id="why" className="scroll-mt-16 px-4 py-24 sm:px-6 sm:py-32">
      <SectionHead eyebrow="Vì sao hiệu quả" title="Dựa trên nghiên cứu về học bằng cách dạy" />
      <div className="mx-auto mt-14 grid max-w-5xl gap-4 md:grid-cols-2">
        {STUDIES.map((study, i) => (
          <Reveal key={study.title} delay={i * 0.06}>
            <div className="h-full rounded-2xl border border-neutral-200 p-6 transition-colors hover:border-neutral-300">
              <p className="m-0 text-[12px] text-neutral-400">{study.cite}</p>
              <h3 className="m-0 mt-3 text-[18px] font-semibold tracking-tight">{study.title}</h3>
              <p className="m-0 mt-2 text-[14px] leading-relaxed text-neutral-500">{study.body}</p>
            </div>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

const RULES = [
  ["Không bao giờ giảng hộ", "Kể cả khi bạn hỏi thẳng đáp án, học trò chỉ hỏi lại — phần hiểu phải là của bạn."],
  ["Chấm theo tài liệu khoá học", "Lời giảng được so với đúng vùng slide bạn chọn, không theo hiểu biết chung của mô hình."],
  ["Chỉ vị trí, không trích đáp án", "Học trò trỏ tới chỗ trên slide nó đang thắc mắc; bạn tự mở ra xem khi đã thử giảng."],
  ["Nhấn để nói", "Mic chỉ thu khi bạn giữ phím. Ngồi trong lớp thì bật chế độ im lặng và gõ chữ."],
];

function Principles() {
  return (
    <section id="rules" className="scroll-mt-16 border-t border-neutral-100 px-4 py-24 sm:px-6 sm:py-32">
      <SectionHead eyebrow="Nguyên tắc" title="Học trò AI được thiết kế để không làm bài hộ bạn" />
      <div className="mx-auto mt-14 grid max-w-5xl gap-x-10 sm:grid-cols-2">
        {RULES.map(([title, body], i) => (
          <Reveal key={title} delay={i * 0.06} className="border-t border-neutral-200 py-6">
            <div className="flex gap-4">
              <span className="pt-0.5 text-[13px] tabular-nums text-neutral-400">0{i + 1}</span>
              <div>
                <h3 className="m-0 text-[16px] font-semibold tracking-tight">{title}</h3>
                <p className="m-0 mt-1.5 text-[14px] leading-relaxed text-neutral-500">{body}</p>
              </div>
            </div>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

function Cta() {
  return (
    <section className="px-4 pb-24 sm:px-6">
      <Reveal className="relative mx-auto max-w-6xl overflow-hidden rounded-3xl bg-neutral-900 px-6 py-16 text-center text-white sm:py-20">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(rgb(255_255_255/0.12)_1px,transparent_1px)] [background-size:22px_22px] [mask-image:radial-gradient(ellipse_at_center,black_10%,transparent_65%)]"
        />
        <h2 className="relative m-0 text-[30px] leading-[1.1] font-semibold tracking-[-0.03em] sm:text-[44px]">
          Chọn một slide.
          <br />
          <span className="text-neutral-400">Giảng thử hai phút.</span>
        </h2>
        <div className="relative mt-8">
          <LinkButton to="/library" variant="inverse" size="lg">
            Vào thư viện slide
          </LinkButton>
        </div>
      </Reveal>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-neutral-200">
      <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-8 text-[12px] text-neutral-500 sm:flex-row sm:items-center sm:px-6">
        <Brand />
        <p className="m-0 sm:ml-4">Nhóm Kẻ Độc Hành · phòng E403 · Mini Hackathon AI Batch 04, VinUni AI20k</p>
        <p className="m-0 sm:ml-auto">Bản thử nghiệm nội bộ</p>
      </div>
    </footer>
  );
}
