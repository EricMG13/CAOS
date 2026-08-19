import { Tag } from 'caos-frontend';

export function Severities() {
  return (
    <div style={{ display: 'flex', gap: 10, padding: 14, flexWrap: 'wrap' }}>
      <Tag sev="success">PASS</Tag>
      <Tag sev="warning">REVIEW</Tag>
      <Tag sev="critical">BREACH</Tag>
      <Tag sev="idle">PENDING</Tag>
    </div>
  );
}
