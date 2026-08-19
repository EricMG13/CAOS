import { TextInput } from 'caos-frontend';

export function Placeholder() {
  return (
    <div style={{ width: 280, padding: 8 }}>
      <TextInput style={{ width: '100%', padding: '6px 8px', fontSize: 13 }} placeholder="Search issuers…" />
    </div>
  );
}

export function Filled() {
  return (
    <div style={{ width: 280, padding: 8 }}>
      <TextInput style={{ width: '100%', padding: '6px 8px', fontSize: 13 }} defaultValue="Altice France SA" />
    </div>
  );
}
