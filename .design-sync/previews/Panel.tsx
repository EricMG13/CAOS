import { Panel } from 'caos-frontend';

const row = (k: string, v: string) => (
  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', fontSize: 12 }}>
    <span style={{ color: 'var(--caos-muted)' }}>{k}</span>
    <span style={{ fontVariantNumeric: 'tabular-nums', color: 'var(--caos-text)' }}>{v}</span>
  </div>
);

export function CapitalStructure() {
  return (
    <div style={{ width: 440, height: 200 }}>
      <Panel title="Capital Structure">
        <div style={{ padding: 12 }}>
          {row('1L Term Loan', '$1,250m · S+425')}
          {row('2L Senior Notes', '$400m · 8.50%')}
          {row('Total Debt', '$1,650m')}
          {row('Net Leverage', '4.1x')}
        </div>
      </Panel>
    </div>
  );
}

export function WithHeaderMeta() {
  return (
    <div style={{ width: 440, height: 150 }}>
      <Panel
        title="Covenant Compliance"
        right={<span style={{ fontSize: 10, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--caos-success)' }}>● Pass</span>}
      >
        <div style={{ padding: 12, fontSize: 12, color: 'var(--caos-muted)' }}>
          Net leverage 4.1x vs 6.0x springing covenant — 32% headroom at Q2.
        </div>
      </Panel>
    </div>
  );
}
