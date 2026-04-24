import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Muslin",
  description: "The expert sewing friend you don't have.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
