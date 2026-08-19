import { SectionHeader } from 'caos-frontend';

const card = { width: 440, border: '1px solid var(--caos-border)', borderRadius: 6, background: 'var(--caos-panel)' };

export function WithMeta() {
  return (
    <div style={card}>
      <SectionHeader title="CP-1 · Reported Foundation" right="Verified" />
      <div style={{ padding: 12, fontSize: 12, color: 'var(--caos-muted)' }}>Reported leverage 6.2x · EBITDA $268m</div>
    </div>
  );
}

export function TitleOnly() {
  return (
    <div style={card}>
      <SectionHeader title="CP-4C · Covenant Calculations" />
    </div>
  );
}
