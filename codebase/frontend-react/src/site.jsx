// Mảnh giao diện dùng chung cho các trang ngoài không gian học: trang giới
// thiệu, đăng nhập, thư viện.

import { motion } from "motion/react";
import { Link } from "react-router";
import { EASE } from "./motion";

/** Dấu của V_KDH: chữ V và một vạch ngắn ở chân, đọc thành "V_".
 *
 *  CÙNG MỘT HÌNH với public/favicon.svg, vẽ bằng path chứ không bằng font —
 *  logo trên trang và icon trên tab trình duyệt phải là một, và chữ theo font
 *  thì mỗi máy render một kiểu. Sửa hình ở đây thì sửa cả favicon. */
export function BrandMark({ className = "size-7" }) {
  return (
    <svg viewBox="0 0 32 32" className={`shrink-0 ${className}`} aria-hidden="true">
      <rect width="32" height="32" rx="7" fill="#171717" />
      <path
        d="M6.5 9.5 12 22l5.5-12.5"
        fill="none"
        stroke="#fff"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <rect x="19.5" y="21" width="7" height="2.6" rx="1.3" fill="#fff" />
    </svg>
  );
}

/** Logo: dấu V_ và tên. Đơn sắc, không phải một icon trang trí. */
export function Brand({ to = "/" }) {
  return (
    <Link to={to} className="flex items-center gap-2.5" aria-label="V_KDH — về trang chủ">
      <BrandMark />
      <span className="text-[14px] font-semibold tracking-tight text-neutral-900">V_KDH</span>
    </Link>
  );
}

/** Hiện ra khi cuộn tới: nhoè rồi rõ, cùng nhịp với phần còn lại của app. */
export function Reveal({ children, delay = 0, className = "", as = "div" }) {
  const Tag = motion[as];
  return (
    <Tag
      className={className}
      initial={{ opacity: 0, y: 12, filter: "blur(6px)" }}
      whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.6, delay, ease: EASE }}
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
  const sizing = { md: "h-9 px-3.5 text-[13px]", lg: "h-11 px-5 text-[15px]" }[size];
  // Bo góc giống nút trong không gian học: trang giới thiệu và app là một sản phẩm.
  const classes = `inline-flex items-center justify-center whitespace-nowrap rounded-lg font-medium transition-colors ${sizing} ${look} ${className}`;
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
