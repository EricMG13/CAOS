import { StatCard } from 'caos-frontend';

export function Neutral() {
  return (
    <div style={{ width: 200, padding: 8 }}>
      <StatCard value="4.1x" label="Net Leverage" sub="vs 3.8x prior Q" />
    </div>
  );
}

export function Severities() {
  return (
    <div style={{ display: 'flex', gap: 10, padding: 8 }}>
      <StatCard value="6.2x" label="Gross Leverage" sev="critical" sub="above 6.0x covenant" />
      <StatCard value="1.8x" label="Interest Cover" sev="warning" />
      <StatCard value="32%" label="Covenant Headroom" sev="success" />
    </div>
  );
}
