import './globals.css';
import 'maplibre-gl/dist/maplibre-gl.css';
import VoyagePromo from '../components/VoyagePromo';

export const metadata = { title: 'GRoute', description: 'Safer seas, smarter routes' };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><input className="theme-toggle-input" id="theme-toggle" type="checkbox" aria-label="Toggle dark mode" /><label className="theme-toggle" htmlFor="theme-toggle" title="Toggle dark mode">☼</label><button className="profile-control" type="button" aria-label="Open profile"><span /></button><VoyagePromo />{children}</body></html>;
}
