import type { Metadata } from "next";
import { Noto_Sans, Noto_Sans_Devanagari, Noto_Sans_Gujarati, Noto_Serif } from "next/font/google";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import "../globals.css";
import { Footer } from "@/components/content-page";
import { Header } from "@/components/header";
import { I18nProvider } from "@/lib/i18n";
import { isLang, LANGS } from "@/lib/langs";
import en from "@/messages/en.json";
import gu from "@/messages/gu.json";
import hi from "@/messages/hi.json";

const notoSans = Noto_Sans({ subsets: ["latin"], variable: "--font-noto-sans", display: "swap" });
const notoGu = Noto_Sans_Gujarati({ subsets: ["gujarati"], variable: "--font-noto-gujarati", display: "swap" });
const notoHi = Noto_Sans_Devanagari({ subsets: ["devanagari"], variable: "--font-noto-devanagari", display: "swap" });
const notoSerif = Noto_Serif({ subsets: ["latin"], variable: "--font-noto-serif", display: "swap" });

const DICTS = { en, gu, hi };

export const metadata: Metadata = {
  title: "ClaimSathi",
  description: "Understand a cut or rejected health insurance claim and write to your insurer, with every rule you can check.",
};

export function generateStaticParams() {
  return LANGS.map((lang) => ({ lang }));
}

export default async function RootLayout({ children, params }: LayoutProps<"/[lang]">) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();
  return (
    <html lang={lang} className={`${notoSans.variable} ${notoGu.variable} ${notoHi.variable} ${notoSerif.variable}`}>
      <body>
        <I18nProvider lang={lang} dict={DICTS[lang]}>
          <a className="visually-hidden" href="#main">
            {DICTS[lang].common.skip}
          </a>
          <Suspense fallback={<div className="header" />}>
            <Header />
          </Suspense>
          <main id="main" tabIndex={-1}>
            {children}
          </main>
          <Footer />
        </I18nProvider>
      </body>
    </html>
  );
}
