import type { Metadata } from "next";
import { Outfit } from "next/font/google";
import "./globals.css";
import Sidebar from "./components/Sidebar";

const outfit = Outfit({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700", "800"],
  variable: "--font-outfit",
});

export const metadata: Metadata = {
  title: "JobPulse – UK Vacancy Demand Verification Tool",
  description: "Identify live UK vacancy demand for recruiter market search, powered by Playwright and FastAPI.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${outfit.variable} h-full antialiased dark`}>
      <body className="min-h-full flex bg-[#090d16] text-[#f3f4f6] font-sans">
        <Sidebar />
        <main className="flex-1 flex flex-col h-screen overflow-y-auto bg-[#090d16]">
          {children}
        </main>
      </body>
    </html>
  );
}
