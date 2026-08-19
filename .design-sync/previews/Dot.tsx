import { Dot } from 'caos-frontend';

export function Severities() {
  return (
    <div style={{ display: 'flex', gap: 16, alignItems: 'center', padding: 14, color: 'var(--caos-text)', fontSize: 12 }}>
      {['success', 'warning', 'critical', 'idle'].map((s) => (
        <span key={s} style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <Dot sev={s} /> {s}
        </span>
      ))}
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
        <Dot sev="success" pulse /> running
      </span>
    </div>
  );
}
