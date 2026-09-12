import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata={title:"Between Sessions",description:"Consent-first companion demo."};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="es"><body>{children}</body></html>}
