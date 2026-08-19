import { ScopeToggle } from 'caos-frontend';

export function Sector() {
  return (
    <div style={{ width: 220, padding: 10 }}>
      <ScopeToggle value="sector" onChange={() => {}} />
    </div>
  );
}

export function Issuer() {
  return (
    <div style={{ width: 220, padding: 10 }}>
      <ScopeToggle value="issuer" onChange={() => {}} label="Scope" />
    </div>
  );
}
