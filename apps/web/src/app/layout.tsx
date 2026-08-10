import type {
  Metadata,
} from "next";

import "./globals.css";


export const metadata: Metadata = {
  title: "Northstar Support | SupportPilot AI",
  description:
    "Northstar Commerce customer support powered by SupportPilot AI.",
};


export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        {children}
      </body>
    </html>
  );
}