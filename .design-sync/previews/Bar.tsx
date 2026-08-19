import { Bar } from 'caos-frontend';

const meter = (label: string, pct: number, color: string) => (
  <div>
    <div style={{ fontSize: 11, color: 'var(--caos-muted)', marginBottom: 4 }}>{label}</div>
    <Bar pct={pct} color={color} />
  </div>
);

export function Levels() {
  return (
    <div style={{ width: 300, padding: 14, display: 'grid', gap: 12 }}>
      {meter('Covenant headroom 32%', 32, 'var(--caos-success)')}
      {meter('Leverage vs cap 88%', 88, 'var(--caos-warning)')}
      {meter('Liquidity drawn 100%', 100, 'var(--caos-critical)')}
    </div>
  );
}
