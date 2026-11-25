import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = { title:'BharatMarket AI — Market Intelligence Terminal', description:'Indian equity market analytics, time-series research and market data terminal.' };
export default function RootLayout({children}:{children:React.ReactNode}) { return <html lang="en"><body suppressHydrationWarning>{children}</body></html>; }
