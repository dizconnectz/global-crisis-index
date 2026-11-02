import type { Metadata, Viewport } from "next";
import { JetBrains_Mono, Sarabun } from "next/font/google";
import "./globals.css";

// Sarabun is a looped Thai face (letters keep their heads), easier to read than loopless sans.
const thai = Sarabun({
  subsets: ["thai", "latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-thai",
  display: "swap",
});
const mono = JetBrains_Mono({ subsets: ["latin"], weight: ["500", "700"], variable: "--font-num", display: "swap" });

export const metadata: Metadata = {
  title: "Global Crisis Index — ดัชนีวิกฤตเชิงระบบของโลก",
  description:
    "ดัชนี 0-100 วัดระดับผลกระทบเชิงระบบต่อโลก จากเศรษฐกิจ ภูมิรัฐศาสตร์ ภัยธรรมชาติ และสุขภาพ/โครงสร้างพื้นฐาน อัปเดตทุก 6 ชั่วโมง คำนวณแบบโปร่งใสตรวจสอบได้",
};

export const viewport: Viewport = { themeColor: "#f4f4f5" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="th" className={`${thai.variable} ${mono.variable}`}>
      <body className="min-h-screen font-sans">{children}</body>
    </html>
  );
}
