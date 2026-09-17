// Mảnh giao diện dùng chung cho các trang ngoài không gian học: trang giới
// thiệu, đăng nhập, thư viện.

import { motion } from "motion/react";
import { Link } from "react-router";
import { EASE } from "./motion";

/** Chữ lồng thay cho logo: đơn sắc, không phải một icon trang trí. */
export function Brand({ to = "/" }) {
  return (
    <Link to={to} className="flex items-center gap-2.5">
      <span className="grid size-7 shrink-0 place-items-center rounded-lg bg-neutral-900 text-[13px] font-semibold text-white">
        G
      </span>
      <span className="text-[14px] font-semibold tracking-tight text-neutral-900">Giảng lại</span>
    </Link>
  );
}

/** Lưới chấm mờ dần ra rìa — nền của các phần đầu trang. Chấm chứ không phải
 *  mảng màu: vẫn đơn sắc, chỉ đủ để trang không phẳng lì. */
export function DotGrid({ className = "" }) {
  return (
    <div
      aria-hidden="true"
      className={`pointer-events-none absolute inset-0 bg-[radial-gradient(rgb(0_0_0/0.09)_1px,transparent_1px)] [background-size:22px_22px] [mask-image:radial-gradient(ellipse_at_center,black_20%,transparent_70%)] ${className}`}
    />
  );
}

/** Hiện ra khi cuộn tới: nhoè rồi rõ, cùng nhịp với phần còn lại của app. */
export function Reveal({ children, delay = 0, className = "", as = "div" }) {
  const Tag = motion[as];
  return (
    <Tag
      className={className}
      initial={{ opacity: 0, y: 16, filter: "blur(8px)" }}
      whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.7, delay, ease: EASE }}
    >
      {children}
    </Tag>
  );
}

/** Nút dạng link — cùng kích thước và màu với Button trong ui.jsx. */
export function LinkButton({ to, href, variant = "primary", size = "md", className = "", children }) {
  const look = {
    primary: "bg-neutral-900 text-white hover:bg-neutral-700",
    normal: "bg-white text-neutral-800 ring-1 ring-inset ring-neutral-200 hover:bg-neutral-50",
    inverse: "bg-white text-neutral-900 hover:bg-neutral-200",
    quiet: "text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900",
  }[variant];
  const sizing = { md: "h-9 px-3.5 text-[13px]", lg: "h-11 px-5 text-[14px]" }[size];
  const classes = `inline-flex items-center justify-center whitespace-nowrap rounded-full font-medium transition-colors ${sizing} ${look} ${className}`;
  return href ? (
    <a href={href} className={classes}>
      {children}
    </a>
  ) : (
    <Link to={to} className={classes}>
      {children}
    </Link>
  );
}
