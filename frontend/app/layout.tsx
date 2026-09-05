import './globals.css';
import 'maplibre-gl/dist/maplibre-gl.css';

export const metadata = { title: 'GRoute', description: 'Safer seas, smarter routes' };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><input className="theme-toggle-input" id="theme-toggle" type="checkbox" aria-label="Toggle dark mode" /><label className="theme-toggle" htmlFor="theme-toggle" title="Toggle dark mode">☼</label>{children}</body></html>;
}
