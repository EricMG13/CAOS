import Link from "next/link";

export default function NotFound() {
  return <section className="panel"><div className="panel-body"><div className="eyebrow">ROUTE NOT FOUND</div><h2>Page not found</h2><p className="muted">This workspace destination does not exist.</p><Link className="button small" href="/cases">Return to Cases</Link></div></section>;
}
