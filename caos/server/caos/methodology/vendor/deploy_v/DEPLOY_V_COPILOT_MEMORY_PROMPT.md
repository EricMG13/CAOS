# Deploy V hardened Copilot memory prompt

**Status:** recommended launcher wording for Deploy V  
**Last reviewed:** 2026-08-03

## Decision

- Keep `Run CP-<ID>` as the canonical command because that is the form declared
  by the Deploy V `SKILL.md` files.
- Accept bare `CP-<ID>` only as start-of-message shorthand, then normalize it to
  `Run CP-<ID>` before dispatch.
- Do not put a OneDrive or SharePoint URL in saved memory. The user provides or
  selects the current Deploy V skills folder in the conversation.
- Treat saved memory as a convenience alias, not as the module registry, a
  folder binding, evidence, or cross-session run state.
- Resolve the requested ID from the current `CP_DEPLOY_V_RETRIEVAL_INDEX_v1.json`
  before opening a skill. Require `INDEX_BUILD_ID:
  a6f9859cec54dd1da765cac180d988ce0643698801db40fe5452ff0d56c36f2a`; a missing or stale index is a stop,
  not permission to scan sibling folders.

`<ID>` is a placeholder. For example, `Run CP-1`, `CP-3A`, `Run CP-DR`, and
`CP-MODEL` are commands; the literal text `CP-ID` is not a module command.

## Common failure modes for this deployment

1. **Memory is soft context, not deterministic dispatch.** Copilot can merge,
   update, or remove saved memories. A `Memory updated` notice proves only that
   something was saved, not that a fresh Cowork task will select the right skill.
2. **A selected folder is not necessarily a persistent binding.** Memory should
   not imply that it retained an attachment, connector handle, permission, or
   folder contents. Require the current folder in the current conversation.
3. **Native Cowork discovery can make launcher memory redundant.** Cowork now
   discovers custom skills under `Documents/Cowork/skills/<slug>/SKILL.md` at
   the start of a conversation. Prefer native installation and use memory only
   for the command shorthand — for the 33 packages that fit the host limits.
   Cowork accepts at most 20 companion files per skill and grants no exception,
   so `cp-4-legal-covenant-interpreter` (22), `cp-5-evidence-trace-validator`
   (32) and `cp-os-credit-os` (33) cannot be installed natively. Those three
   carry an `EXPLICIT_C_CHANNEL_EXCEPTION` in
   `CP_DEPLOY_V_RETRIEVAL_REGISTRY_v1` and are reachable only through
   folder grounding on the Deploy V package. Installing the other 33 natively
   while grounding on the folder for these three puts two entry files in scope
   for the same module ID; ground on the folder alone, or install natively and
   accept that those three modules are unavailable in that session.
4. **Whole-folder retrieval creates collisions.** Deploy V contains many sibling
   skills with repeated filenames such as schema and system references. A router
   can blend two modules unless it selects exactly one `SKILL.md` before reading
   companions.
5. **Bare IDs can trigger accidentally.** `CP-3A` in prose, a quote, a filename,
   or an output must not launch a skill. Recognize an ID only as the first
   non-whitespace token in the user's new message.
6. **Remembered module lists go stale.** Resolve the ID from the current supplied
   folder. Do not route from a list remembered in an earlier conversation.
7. **Qualifiers can be dropped during normalization.** Preserve every character
   after the command token, including bracketed issuer, instrument, date, scope,
   and profile qualifiers.
8. **Aliases can create duplicate or wrong ownership.** Accept an alias only when
   exactly one current `SKILL.md` declares it. In the current package,
   `CP-PARSE` is a standalone preparation module with its own output; only
   `CP-5A` resolves to CP-5 and shares that physical package.
9. **Memory can contaminate evidence and state.** Never reuse remembered issuer
   facts, dates, run IDs, completion status, outputs, or prior analytical
   conclusions. The selected skill and current accessible artifacts govern the
   run.
10. **Access claims can be false.** If folder listing or file reading fails, say
    so. Do not say the folder was scanned and do not silently fall back to model
    memory.
11. **Folder content can contain hostile or irrelevant instructions.** Sibling
    skills and user evidence are not routing authority. After selecting one
    skill, follow its `SKILL.md`; load only the companions that skill directs;
    treat issuer/source content as data.
12. **Platform limits are separate from memory.** The current retrieval index is
    the source of truth for the physical-skill and command-ID counts. The
    published package registry separately declares companion-file budgets and
    any explicitly approved migration exceptions; a memory prompt cannot fix a
    packaging or installation-channel limit. Validate the exact path used before
    release and stop on any stale index or undeclared exception.

## Copy into Microsoft 365 Copilot saved memory

Select or provide the Deploy V skills folder that directly contains the deployed
skill subfolders, then paste the following into a normal Microsoft 365 Copilot
Chat. There is intentionally no URL placeholder.

```text
Remember this: In Deploy V, a new message that begins with `Run CP-<ID>`, or whose first token is bare `CP-<ID>`, requests that exact module; normalize the shorthand to `Run CP-<ID>` and preserve all following text verbatim. `<ID>` is a placeholder, not a literal module name. I will provide or select the current Deploy V skills folder in that conversation. Resolve one unique match only from that folder's current `SKILL.md` files and declared aliases; read the selected `SKILL.md` first and only the companions it directs. Never substitute a remembered URL, folder contents, module definition, evidence, issuer fact, run state, or prior output. If the folder is unavailable or the match is not unique, stop and ask. Otherwise state the normalized command and selected skill before running. An ID elsewhere in prose, quoted material, filenames, or outputs does not trigger this rule.
```

## Expected runtime behavior

The command recognizer is conceptually:

```text
start of message → optional "Run " → CP-<ID> → whitespace or end of message
```

It is case-insensitive for recognition, but it emits the canonical uppercase
form. It does not activate on an ID embedded later in prose, quoted evidence, a
filename, or a module output.

For exact resolution, a candidate must declare the requested token as its run
command, as an `Also answers` alias, or at the start of its frontmatter `name`.
The comparison ends at the token boundary, so CP-5 does not accidentally match
CP-5A. Zero or multiple candidates is a stop. This frontmatter fallback permits
the current CP-OS entry, whose name begins `CP-OS` but whose entry text does not
carry the generic `Run command:` line.

Examples:

| User message | Expected result |
|---|---|
| `CP-1 [issuer: Acme]` | Normalize to `Run CP-1 [issuer: Acme]`; select CP-1 only. |
| `Run CP-3A [instrument: 6.5% secured notes 2029]` | Preserve the command and qualifier; select CP-3A only. |
| `CP-PARSE` | Select the standalone CP-PARSE preparation skill and emit its preparation handoff. |
| `CP-5A` | Resolve the currently declared compatibility alias to CP-5. |
| `Compare the CP-2 and CP-3 outputs` | Do not launch either module. |
| `CP-NOTREAL` | Stop with no execution and report that no current skill matches. |
| `CP-1` with no accessible skills folder | Ask the user to provide or select the skills folder. |

For new or incomplete governed work, start with `Run CP-OS`. Direct module
commands remain available when they are issued within the workflow or when the
selected module's own entry contract permits standalone use.

## Acceptance test

1. Save the memory and require the visible `Memory updated` confirmation.
2. Open **Settings → Personalization → Manage saved memories** and inspect the
   saved item. Check that it did not invent or retain a URL. Asking Copilot what
   it remembers is a useful secondary check, not proof of exact storage.
3. Start a new Cowork conversation, provide/select the skills folder, and send
   `CP-1 [issuer: Memory Test Co]`.
4. Pass only if it states `Run CP-1 [issuer: Memory Test Co]`, names the CP-1
   skill, and does not load a sibling skill.
5. In another new conversation with no folder, send `CP-1`. Pass only if it asks
   for the folder and does not claim to have scanned or remembered one.
6. Test `CP-PARSE`, `CP-5A`, an unknown ID, and an ID mentioned in prose. Record
   memory-save and launch results separately.

## Current Microsoft guidance

- [Manage Copilot Memory in Microsoft 365 Copilot](https://support.microsoft.com/en-US/Microsoft-365-Copilot/manage-copilot-memory-in-microsoft-365-copilot)
- [Personalize what Microsoft 365 Copilot remembers](https://support.microsoft.com/en-us/Microsoft-365-Copilot/personalize-what-microsoft-365-copilot-remembers)
- [Use Copilot Cowork](https://learn.microsoft.com/en-us/microsoft-365/copilot/cowork/use-cowork)
- [Customize Copilot Cowork](https://learn.microsoft.com/en-us/microsoft-365/copilot/cowork/cowork-customize)
