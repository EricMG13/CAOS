import { StatusGlyph } from 'caos-frontend';

export function Glyphs() {
  return (
    <div style={{ display: 'flex', gap: 24, alignItems: 'center', padding: 14, fontSize: 12 }}>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: 'var(--caos-muted)' }}>
        <StatusGlyph kind="locked" size={14} /> Module locked
      </span>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: 'var(--caos-warning)' }}>
        <StatusGlyph kind="warning" size={14} /> Covenant warning
      </span>
    </div>
  );
}
