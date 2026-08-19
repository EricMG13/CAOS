# REF_CP-4_EDGAR | EDGAR Covenant Source-Retrieval Map
# Version: 1.0 | Date: 2026-06-15
# Parent System: CP Agents — Credit Analysis Co-Pilot
# Purpose: A free, primary-source acquisition lane for covenant/legal documents via SEC EDGAR

---

## 1. Purpose

`REF_CP-4_EDGARCovenantSourceMap.md` defines how to **locate and acquire**
controlling legal documents (credit agreements, indentures, supplements,
intercreditor agreements, covenant descriptions) from **SEC EDGAR** — a free,
public, primary source requiring **no paid API or key**.

It exists to give the **Legal File Gate (Step 1, `REF_CP-4_01`)** a sourcing path
when an executed governing document is *missing*, so the gate can attempt free
acquisition before declaring **Blocked**. It does **not** replace the Covenant
Feature Register (Step 3) or the deep-dive steps (4–8) — it feeds them with
better-provenanced source material.

Works alongside:

- `REF_CP-4_01_LegalFileGateSourceQuality.md` (Step 1 — consumes this)
- `REF_CP-4_02_ControllingDocumentsSourceAuthority.md` (Step 2 — ranks what this returns)
- `REF_CP-4_03_CovenantFeatureRegister.md` (Step 3 — built from the executed text)
- `caos/docs/AGENT_SKILLS_REVIEW.md` §2–§3 (why EDGAR over a paid aggregator)

> **Provenance note:** the *filing → covenant-document* taxonomy in §3 is lifted
> from the open (MIT) Octagon SEC skill methodology. Only the **free methodology**
> is used — **not** Octagon's paid data API. The data path here is EDGAR direct,
> which is also a *primary* source and therefore higher-authority than any
> aggregator's read of it.

---

## 2. Core Principle (provenance gate)

EDGAR may **inform, bootstrap, or locate** a document, but a covenant claim is
only as good as the **executed exhibit it resolves to**:

1. A full-text **search hit** or filing-index entry, before the exhibit is pulled
   and ingested, is a **pointer only** — flagged `external · unverified`. It
   **cannot** satisfy the Step-1 BLOCKING gate and **cannot** be cited in the
   Covenant Feature Register.
2. Once the **actual exhibit document** is fetched and ingested (vault → chunks),
   it becomes an **executed primary source** with a real **E-xx Evidence ID**,
   eligible for Authority Rank 1–4 (§5) and able to clear **CP-5 / CP-5B**.
3. **Never** quote a covenant term, basket, threshold, or definition from an
   EDGAR full-text *snippet* — pull and vault the exhibit, then read the clause.

This is the same gate CAOS applies everywhere: *a number with no source trace is
exactly what the platform prevents.* EDGAR satisfies it more cleanly than an
aggregator could — re-vaulting the primary document is trivial when the source
already **is** the primary document.

---

## 3. Filing → Controlling-Document Map (the taxonomy)

Where each covenant-bearing document is filed on EDGAR. Only **reporting issuers**
file (see §6 limitations).

| Controlling Document | EDGAR Exhibit | Carrier Forms | Notes |
|---|---|---|---|
| **Credit agreement** (TLA/TLB, revolver) | **Ex-10.x** (material contract) | **8-K** (Item 1.01 entry / Item 2.03 obligation), then **10-Q / 10-K** | Conformed executed copy; primary for first-lien/loan covenants |
| **Amended & restated / amendment** to a credit agreement | Ex-10.x | **8-K** (Item 1.01/2.03) | A&E, repricings, incremental joinders |
| **Indenture** (notes) | **Ex-4.x** | **8-K** (Item 1.01/2.03), **S-1 / S-4**, **10-K** | Primary for bond covenants |
| **Supplemental indenture** (new notes, amendments, guarantor accession) | Ex-4.x | **8-K** | Tracks covenant changes over time |
| **Indenture (unregistered, TIA-qualified)** | filed with the form | **Form T-3** | Common in **exchange offers / LME / restructurings** |
| **Covenant description** ("Description of Notes") | body of prospectus | **424B** (registered notes), **S-4** (A/B exchange of 144A notes) | The free EDGAR proxy for a 144A **OM** covenant section |
| **Intercreditor / collateral agency agreement** | Ex-10.x / Ex-4.x | **8-K**, S-1/S-4 | Controls lien priority & enforcement (Authority Rank 2) |
| **Security / pledge / guarantee agreement** | Ex-10.x / Ex-4.x | **8-K**, exhibits to CA/indenture | Collateral package, guarantor coverage |
| **Compliance certificate / covenant schedule** | Ex-10.x / Ex-99.x | occasionally **8-K / 10-Q** | Rarely filed; treat as Rank 3 when present |
| **Investor deck / press release** (terms summary) | Ex-99.x | **8-K** (Item 7.01/2.02) | Marketing only — Authority Rank 6 |

**Key leveraged-finance insight:** for **144A high-yield** where the offering
memorandum is *not* public, the **S-4 exchange-offer prospectus "Description of
Notes"** is the free EDGAR equivalent of the OM covenant description — and any
**registered** notes carry it in the **424B**.

---

## 4. EDGAR Retrieval Methods (free, no key)

1. **Full-text search (EFTS)** — filings 2001–present. Query the public endpoint
   `efts.sec.gov/LATEST/search-index?q="..."` (the same API the EDGAR FTS UI
   calls); filter by `forms=8-K,S-4,10-K` and date. Useful queries: issuer name +
   `"Credit Agreement"` / `"Indenture"` / `"Supplemental Indenture"` /
   `"Description of Notes"` / a known tranche name.
2. **Submissions API** — `data.sec.gov/submissions/CIK##########.json` (10-digit
   zero-padded CIK): the issuer's full filing history; filter to the carrier forms
   in §3.
3. **Company browse** — `sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=…&type=8-K`
   to list filings by type.
4. **Exhibit pull** — each filing's index at
   `sec.gov/Archives/edgar/data/{cik}/{accession}/` lists exhibits; fetch the
   specific **Ex-4.x / Ex-10.x** document, not the cover 8-K.

**Fair-access (mandatory):** send a descriptive `User-Agent` (name + contact
email) and stay **≤ 10 requests/second**. No key, no cost.

---

## 5. Source-Authority Mapping (to the CP-4 6-rank hierarchy)

EDGAR documents enter the existing Step-1/Step-2 authority hierarchy **after**
they are fetched and vaulted (§2):

| EDGAR document (vaulted) | CP-4 Authority Rank |
|---|---|
| Executed credit agreement / indenture / supplemental indenture (Ex-10.x / Ex-4.x; incl. T-3 indenture) | **Rank 1** |
| Executed intercreditor agreement (Ex-10.x) | **Rank 2** |
| Compliance certificate / covenant schedule (where filed) | **Rank 3** |
| "Description of Notes" in 424B / S-4 prospectus | **Rank 4** (summary — verify against the executed indenture) |
| Investor deck / press-release terms (Ex-99.x) | **Rank 6** |

Filed exhibits are typically **conformed executed copies** (`/s/` signatures) and
are authoritative for provision-level analysis. An unfetched FTS hit has **no
rank** — it is an `external · unverified` pointer until ingested.

---

## 6. Coverage & Limitations (leveraged-finance reality)

EDGAR is a strong **free** lane for a meaningful subset of the universe — not all
of it:

- **Reporting issuers only.** The issuer must file with the SEC (registered
  securities, or reporting obligations under §15(d) / an indenture reporting
  covenant). Many LBO borrowers **do** file because their HY notes were registered
  via an A/B exchange or their documents require SEC-style reporting.
- **Pure-private gaps.** Sponsor-owned borrowers with **144A-for-life** debt (no
  registration rights) and no public reporting may **not** appear on EDGAR — and
  their **offering memoranda are generally not on EDGAR** at all.
- **Pre-2001** filings are outside EDGAR full-text search (browse still works).
- EDGAR **supplements**, never replaces, analyst-uploaded executed documents. The
  Step-1 BLOCKING rule stands: at least one **executed** governing document
  (uploaded *or* EDGAR-vaulted) must exist, or Module Status = **Blocked**.

---

## 7. Wiring (which steps consume this)

| Step | Use |
|---|---|
| **Step 1 — Legal File Gate** (`REF_CP-4_01`) | Before declaring **Blocked** for a missing governing doc, attempt the EDGAR lane (§3–§4). A vaulted exhibit can satisfy the gate; a search hit cannot. |
| **Step 2 — Controlling Documents** (`REF_CP-4_02`) | Rank EDGAR-vaulted documents via §5 and the 6-rank hierarchy. |
| **Step 3 — Covenant Feature Register** (`REF_CP-4_03`) | Populate from the executed EDGAR text with exact clause/section + E-xx Evidence ID. |
| **CP-5 / CP-5B** | Validate that every EDGAR-derived covenant claim resolves to a vaulted exhibit (not a snippet) with a real E-xx; flag `external · unverified` pointers as orphan-claim candidates. |
| **CP-MON** | A new 8-K (Item 1.01/2.03) or supplemental indenture on EDGAR is a covenant-amendment **trigger** → route to CP-4 / CP-4C / CP-3D. |

**Implementation status:** this lane is wired, not just described. The CAOS server
exposes it at `/api/edgar/*` (`caos/server/edgar.py` + `caos/server/routes/edgar.py`)
— `search` / `filings` / `exhibits` return pointers; `vault-exhibit` fetches an
exhibit and runs it through the standard ingest path (→ E-xx eligible). An MCP
wrapper (`caos/mcp/edgar/`) surfaces the same four tools to an agent. Off until
`EDGAR_USER_AGENT` is set (SEC fair-access; no key, no cost).

---

## 8. Version History

| Version | Date | Notes |
|---|---|---|
| 1.0 | 2026-06-15 | Initial EDGAR covenant source-retrieval map. Free (no-paid-services constraint); lifts the open Octagon SEC filing→covenant taxonomy; binds it to the CP-4 6-rank authority hierarchy and the CP-5/CP-5B provenance gate. See `caos/docs/AGENT_SKILLS_REVIEW.md`. |
