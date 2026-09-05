'use client';

import { FormEvent, useEffect, useState } from 'react';

type Profile = { name: string; email: string; notifications: boolean };
const defaultProfile: Profile = { name: 'Admin Operator', email: 'aniketsupermails2005@gmail.com', notifications: true };

export default function AccountCenter({ onLogout }: { onLogout: () => void }) {
  const [open, setOpen] = useState(false);
  const [profile, setProfile] = useState<Profile>(defaultProfile);
  useEffect(() => { const saved = localStorage.getItem('groute-profile'); if (saved) setProfile({ ...defaultProfile, ...JSON.parse(saved) }); }, []);
  function save(event: FormEvent) { event.preventDefault(); localStorage.setItem('groute-profile', JSON.stringify(profile)); setOpen(false); }
  function logout() { localStorage.removeItem('groute-authenticated'); onLogout(); }
  return <><button className="profile-control" type="button" aria-label="Open account center" onClick={() => setOpen(true)}><span /></button>{open && <div className="account-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setOpen(false); }}><section className="account-center" role="dialog" aria-modal="true" aria-labelledby="account-title"><button className="account-close" type="button" onClick={() => setOpen(false)} aria-label="Close account center">×</button><p className="eyebrow">Operator account</p><h2 id="account-title">Account center</h2><p className="account-subtitle">Customize your GRoute command profile.</p><form onSubmit={save}><label>Display name<input value={profile.name} onChange={(event) => setProfile({ ...profile, name: event.target.value })} /></label><label>Email<input type="email" value={profile.email} onChange={(event) => setProfile({ ...profile, email: event.target.value })} /></label><label className="account-toggle"><input type="checkbox" checked={profile.notifications} onChange={(event) => setProfile({ ...profile, notifications: event.target.checked })} /><span>Operational alert notifications</span></label><button className="account-save" type="submit">Save profile</button></form><button className="account-logout" type="button" onClick={logout}>Log out</button></section></div>}</>;
}
