import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Client Onboarding OS",
  description: "AI-powered Client Onboarding OS",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
