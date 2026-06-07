import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import AuthGate from './components/AuthGate';

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata = {
  title: 'TheImageBuilder Platform',
  description: 'AI-Agent Orchestration UI',
};

export default function RootLayout({ children }) {
  return (
     <html lang="en" suppressHydrationWarning={true}>
      <body className="bg-slate-950 text-slate-100">
        <AuthGate>
          {children} {/* ◄── Everything inside your app router is now locked behind the gate */}
        </AuthGate>
      </body>
    </html>
  );
}


