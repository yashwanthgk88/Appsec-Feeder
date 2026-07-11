import { useState, useRef, useEffect } from "react";

// ---------------------------------------------------------------
// AppSec Feeder — Team Intelligence Briefings (POC v2)
// Each feed opens with a live top-10 index (researched from the
// web), and any item expands into a full analyst deep-dive.
// ---------------------------------------------------------------

const C = {
  ink: "#141414",
  paper: "#F1F2EF",
  card: "#FFFFFF",
  yellow: "#FFE600",
  gray: "#5A5D58",
  line: "#D9DBD4",
  softLine: "#E7E8E2",
  red: "#B3261E",
};

const MONO =
  "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace";
const SANS =
  "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif";

const SEV_COLORS = {
  CRITICAL: { bg: "#141414", fg: "#FFE600" },
  HIGH: { bg: "#B3261E", fg: "#FFFFFF" },
  NOTABLE: { bg: "#E7E8E2", fg: "#141414" },
  ADOPT: { bg: "#141414", fg: "#FFE600" },
  PILOT: { bg: "#5A5D58", fg: "#FFFFFF" },
  WATCH: { bg: "#E7E8E2", fg: "#141414" },
  SIGNAL: { bg: "#141414", fg: "#FFE600" },
  HYPE: { bg: "#E7E8E2", fg: "#141414" },
};

const FEEDS = {
  breach: {
    tag: "BREACH DEEP-DIVE",
    title: "Breach Deep-Dives",
    blurb:
      "The top 10 recent application-security-relevant breaches, ranked by how much an AppSec team should care. Pick one for the full autopsy: root cause, attack chain, business impact, detection, fix, POV.",
    povAngle:
      "Frame this breach as a case study in systemic failure, not an isolated event: what class of enterprise is exposed to the same failure, and why existing controls keep missing it.",
    placeholder: "Or research a specific breach, e.g. 'the MOVEit breach'",
    indexLoading: [
      "Scanning breach disclosures",
      "Ranking by AppSec relevance",
      "Compiling the top 10",
    ],
    loading: [
      "Searching incident reports",
      "Tracing the attack chain",
      "Assessing business impact",
      "Writing detection guidance",
      "Forming the practitioner POV",
    ],
    indexPrompt: `You are an application security intelligence analyst. Use web search to find the top 10 most significant breaches / security incidents relevant to application security from roughly the last 90 days (prioritize: exploited app vulnerabilities, supply chain, API abuse, leaked secrets, AI-related incidents — the richest AppSec lessons first).

Respond with ONLY a raw JSON array, no markdown fences, no preamble, exactly this shape:
[{"title":"short incident name","org":"victim org","date":"Mon YYYY","category":"e.g. Supply chain / API / AuthN / Ransomware / Secrets","severity":"CRITICAL|HIGH|NOTABLE","one_liner":"one sentence: what happened and why AppSec teams should care (max 25 words)"}]

Rules: exactly 10 items, real incidents only with real dates, never invent. Keep every field terse. JSON only.`,
    prompt: (topic) => `You are a principal application security analyst producing an internal intelligence briefing for a senior AppSec consulting team (they run SAST/DAST/threat modeling programs for banking, insurance and manufacturing clients). Use web search to research this breach/incident in depth: "${topic}".

Write a detailed markdown report with EXACTLY these sections, in this order:

## Executive Summary
3-4 sentences. Who was hit, how, and the single most important lesson.

## Incident Overview
What happened and the timeline of disclosure/exploitation.

## Root Cause
Be genuinely technical: vulnerability class (CWE if identifiable), CVE numbers if any, the attack chain step by step, what control was missing or failed.

## Technical Impact
Systems, data, and trust boundaries compromised.

## Business Impact
Records/customers affected, cost estimates, regulatory exposure (GDPR/DPDP/SEC etc.), stock/brand effects where reported.

## How to Detect
Concrete guidance: what log sources, queries, IOCs (where public), or scanner rules would surface this class of issue in a client environment.

## How to Fix & Prevent
Immediate remediation, then strategic controls mapped to the SSDLC (requirements, threat modeling, SAST/SCA/DAST, pipeline gates, runtime).

## Practitioner POV
4-5 sharp, opinionated takeaways for an AppSec consulting practice: what this changes about how we advise clients, where teams over/under-invest, what to bring up in the next client QBR.

## Sources
Bullet list of the sources you used with URLs.

Rules: be specific, technical and honest about what is confirmed vs. speculated. Never invent CVEs, numbers or quotes. Markdown only, no preamble.`,
  },
  tools: {
    tag: "TOOL RADAR",
    title: "Tool Radar",
    blurb:
      "The top 10 new or rising AppSec tools right now. Pick one for the full evaluation: capabilities, honest pros and cons, comparison against incumbents, and an adopt/pilot/watch/avoid verdict.",
    povAngle:
      "Frame this tool within the AppSec market consolidation story and buyer economics: platform vs point solution, incumbent displacement risk, and what it signals about where the category is heading.",
    placeholder: "Or evaluate a specific tool, e.g. 'Endor Labs vs Snyk'",
    indexLoading: [
      "Scanning vendor launches",
      "Reading practitioner buzz",
      "Compiling the top 10",
    ],
    loading: [
      "Scanning vendor releases",
      "Reading practitioner reviews",
      "Building the comparison matrix",
      "Weighing pros against cons",
      "Forming the fit / no-fit POV",
    ],
    indexPrompt: `You are an application security tooling analyst. Use web search to find the top 10 most notable new or significantly updated AppSec tools from roughly the last 6 months (SAST, SCA, DAST, secrets, ASPM, supply chain, AI-powered AppSec — rank by practitioner buzz and relevance to enterprise AppSec programs).

Respond with ONLY a raw JSON array, no markdown fences, no preamble, exactly this shape:
[{"title":"tool name","org":"vendor","date":"Mon YYYY","category":"e.g. SAST / SCA / ASPM / AI AppSec","severity":"ADOPT|PILOT|WATCH","one_liner":"one sentence: what it does and why it's notable (max 25 words)"}]

Rules: exactly 10 items, real tools only, never invent. severity is your quick verdict hint. Keep every field terse. JSON only.`,
    prompt: (topic) => `You are a principal application security analyst producing an internal tool-evaluation briefing for a senior AppSec consulting team that runs SAST, SCA, DAST, secrets scanning and ASPM programs for enterprise clients. Use web search to research this in depth: "${topic}".

Write a detailed markdown report with EXACTLY these sections, in this order:

## Executive Summary
What the tool is and the one-line verdict.

## What It Is
Category, vendor, maturity/funding stage, deployment model (SaaS / on-prem), pricing model if public.

## Key Capabilities
What it actually does, technically. Detection approach, language/ecosystem coverage, CI/CD and IDE integration.

## Pros
Honest strengths, with evidence from reviews/benchmarks where available.

## Cons
Honest weaknesses, gaps, and risks (lock-in, immaturity, noise, coverage holes).

## Comparison vs Incumbents
A markdown table comparing it against 2-3 established tools in the same category (e.g. Checkmarx, Snyk, Veracode, Semgrep, GitHub Advanced Security — pick the right peers). Rows: detection approach, coverage, false-positive handling, CI/CD integration, deployment options, pricing model, enterprise readiness.

## Where It Fits
Which client profile this suits (regulated on-prem bank vs. cloud-native startup), and where it does NOT fit.

## Practitioner POV
4-5 opinionated takeaways: adopt / pilot / watch / avoid recommendation, what it means for existing tool investments, negotiating leverage, consolidation angle.

## Sources
Bullet list of sources used with URLs.

Rules: be honest about marketing claims vs. verified capability. Never invent benchmarks or pricing. Markdown only, no preamble.`,
  },
  ai: {
    tag: "AI × APPSEC WATCH",
    title: "AI × AppSec Watch",
    blurb:
      "The top 10 developments at the AI-and-application-security intersection — AI-generated code risk, agentic AppSec, LLM/MCP security. Pick one for the full signal-vs-hype analysis and POV.",
    povAngle:
      "Frame this within the AI-vs-AppSec arms race and the gap between demo-stage capability and enterprise adoption reality: who wins, who is disrupted, and on what timeline.",
    placeholder: "Or research a specific topic, e.g. 'MCP server security'",
    indexLoading: [
      "Scanning AI security research",
      "Separating signal from hype",
      "Compiling the top 10",
    ],
    loading: [
      "Scanning AI security research",
      "Separating signal from hype",
      "Mapping threats and opportunities",
      "Drafting next-quarter actions",
      "Forming the practitioner POV",
    ],
    indexPrompt: `You are an AI-security intelligence analyst. Use web search to find the top 10 most significant recent developments (roughly last 60 days) at the intersection of AI and application security: AI-generated code security findings, agentic AppSec tooling, LLM/agent/MCP security research and attacks, relevant regulation.

Respond with ONLY a raw JSON array, no markdown fences, no preamble, exactly this shape:
[{"title":"short development name","org":"who published/shipped it","date":"Mon YYYY","category":"e.g. AI code risk / Agentic AppSec / LLM security / MCP / Regulation","severity":"SIGNAL|HYPE|WATCH","one_liner":"one sentence: what it is and why it matters (max 25 words)"}]

Rules: exactly 10 items, real developments only with real dates, never invent papers or products. severity = your signal-vs-hype call. Keep every field terse. JSON only.`,
    prompt: (topic) => `You are a principal application security analyst producing an internal AI-security intelligence briefing for a senior AppSec consulting team that is building AI-assisted AppSec tooling and advising enterprise clients on securing AI systems. Use web search to research this in depth: "${topic}".

Write a detailed markdown report with EXACTLY these sections, in this order:

## Executive Summary
What this development is and why it matters, in 3-4 sentences.

## What's New
The development explained concretely: who shipped/published what, with dates.

## Why It Matters
Separate real signal from vendor hype. What actually changes for AppSec work.

## Threats & Opportunities
New attack surface introduced vs. new defensive capability unlocked. Be specific (e.g. prompt-injection reachability, tool-poisoning in MCP, AI code review quality).

## Impact on AppSec Programs
What this means for SSDLC controls, tooling roadmaps, skills, and client conversations.

## Practitioner POV
4-5 sharp opinions: what to adopt now, what to pilot, what to ignore, and one contrarian take.

## Next Quarter Actions
Concrete steps an AppSec team should take in the next 90 days.

## Sources
Bullet list of sources used with URLs.

Rules: be specific with names and dates, honest about uncertainty. Never invent papers, products or quotes. Markdown only, no preamble.`,
  },
};

// ---------------- POV generation ----------------

const POV_LOADING = [
  "Researching the topic in depth",
  "Testing conventional wisdom",
  "Mapping sector implications",
  "Drafting firm positions",
  "Stress-testing the predictions",
  "Sharpening the bottom line",
];

function povPromptFor(feedKey, topic) {
  const angle = FEEDS[feedKey].povAngle;
  return `You are writing as EY's Application Security consulting team — a Big Four practice that delivers threat modeling, secure code review, SAST/SCA/DAST programs, DevSecOps transformation and SSDLC assessments for enterprise clients in banking, insurance and manufacturing. Produce a detailed internal Point of View (POV) document on: "${topic}". Use web search to ground every claim in current facts.

Voice: a trusted advisor speaking to client executives — confident, business-first, plain language a CFO can follow, with technical depth available where it earns its place. Write "our view", "we advise", "we have seen with clients". The quality bar: a skeptical CISO must learn something they could not get from a news article, and every single problem this document raises MUST be paired with a concrete fix — never leave an issue hanging without remediation guidance.

Write a markdown document with EXACTLY these sections, in this order:

## The Bottom Line
Our practice's position in one hard-hitting paragraph: what happened/what this is, what it means for business, and the one thing leadership must do. ${angle}

## Business Impact Assessment
The consultant's core section. Cover, concretely: revenue and operational disruption; direct costs (response, remediation, legal) with researched figures where available; regulatory exposure (GDPR, DPDP, SEC disclosure, DORA, sector regulators) with realistic penalty framing; customer trust and brand; third-party/contractual fallout. Then translate it per stakeholder: what the Board hears, what the CISO owns, what the CFO budgets.

## What Most Are Getting Wrong
2-3 contrarian observations: where vendor marketing, media coverage, or the typical enterprise response misses the point — and what the correct read is.

## Sector Implications
Sub-sections for Banking & Financial Services, Insurance, and Manufacturing: how this lands differently in each — regulatory exposure, legacy constraints, attack surface, buying behavior.

## How to Fix It — Our Remediation Roadmap
The heart of the POV. Take EVERY issue raised in the sections above and give the fix, organized in three horizons:
- **Immediate (0-30 days):** containment and quick wins — specific, actionable steps.
- **Near-term (30-90 days):** process and control fixes mapped to SSDLC stages (security requirements, threat modeling, SAST/SCA/DAST/secrets, pipeline gates, pen testing).
- **Strategic (6-18 months):** program-level change — operating model, tooling consolidation, developer enablement, metrics.
For each item: what to do, why it works, and how to verify it worked.

## Our Position
4-6 numbered firm stances our practice takes on this topic, each quotable, each with a one-line rationale — including a short outlook on where this goes in the next 12-24 months.

## How Our Team Helps
Map the remediation roadmap to concrete engagement plays: rapid assessment, threat modeling workshop, SSDLC/DevSecOps maturity assessment, managed AppSec testing, tool rationalization, developer security training. For each play: the client trigger, what we deliver, and the outcome. No empty selling — every play must trace back to a fix above.

## Client Conversation Starters
3-4 sharp questions or one-liners a consultant can use to open this topic in a QBR or steering committee, each designed to surface a gap the client didn't know they had.

## Sources
Bullet list of sources used with URLs.

Rules: every factual claim grounded in research; be honest about uncertainty; never invent statistics, penalties, quotes, CVEs or benchmarks — if a figure is an estimate, label it as one; opinionated but defensible; every problem paired with a fix. Markdown only, no preamble.`;
}

// ---------------- Anthropic API ----------------

async function callClaude(messages) {
  const response = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "claude-sonnet-4-6",
      max_tokens: 1000,
      messages,
      tools: [{ type: "web_search_20250305", name: "web_search" }],
    }),
  });
  if (!response.ok) throw new Error(`API returned ${response.status}`);
  const data = await response.json();
  const text = (data.content || [])
    .filter((b) => b.type === "text")
    .map((b) => b.text)
    .join("\n");
  if (!text.trim()) throw new Error("Empty response");
  return text;
}

function parseIndexJson(text) {
  let clean = text.replace(/```json|```/g, "").trim();
  const start = clean.indexOf("[");
  const end = clean.lastIndexOf("]");
  if (start === -1 || end === -1) throw new Error("No JSON array in response");
  clean = clean.slice(start, end + 1);
  const arr = JSON.parse(clean);
  if (!Array.isArray(arr) || arr.length === 0) throw new Error("Empty feed");
  return arr
    .filter((x) => x && x.title)
    .slice(0, 10)
    .map((x) => ({
      title: String(x.title || ""),
      org: String(x.org || ""),
      date: String(x.date || ""),
      category: String(x.category || ""),
      severity: String(x.severity || "").toUpperCase(),
      one_liner: String(x.one_liner || ""),
    }));
}

// ---------------- Minimal markdown renderer ----------------

function renderInline(text, keyBase) {
  const parts = [];
  let rest = text;
  let k = 0;
  const pattern = /(\*\*([^*]+)\*\*|`([^`]+)`|\[([^\]]+)\]\((https?:\/\/[^)\s]+)\))/;
  while (rest.length) {
    const m = rest.match(pattern);
    if (!m) {
      parts.push(rest);
      break;
    }
    if (m.index > 0) parts.push(rest.slice(0, m.index));
    if (m[2]) {
      parts.push(
        <strong key={`${keyBase}-b${k++}`} style={{ color: C.ink }}>
          {m[2]}
        </strong>
      );
    } else if (m[3]) {
      parts.push(
        <code
          key={`${keyBase}-c${k++}`}
          className="px-1 rounded"
          style={{
            fontFamily: MONO,
            fontSize: "0.85em",
            background: "#EFEFE9",
            border: `1px solid ${C.softLine}`,
          }}
        >
          {m[3]}
        </code>
      );
    } else if (m[4]) {
      parts.push(
        <a
          key={`${keyBase}-a${k++}`}
          href={m[5]}
          target="_blank"
          rel="noreferrer"
          className="underline break-all"
          style={{ color: C.ink, textDecorationColor: C.yellow, textDecorationThickness: 2 }}
        >
          {m[4]}
        </a>
      );
    }
    rest = rest.slice(m.index + m[0].length);
  }
  return parts;
}

function MarkdownBlock({ md }) {
  const lines = md.split("\n");
  const out = [];
  let i = 0;
  let key = 0;

  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) {
      i++;
      continue;
    }

    if (
      line.trim().startsWith("|") &&
      i + 1 < lines.length &&
      /^\s*\|?[\s:|-]+\|?\s*$/.test(lines[i + 1]) &&
      lines[i + 1].includes("-")
    ) {
      const header = line.split("|").map((c) => c.trim()).filter(Boolean);
      i += 2;
      const rows = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) {
        rows.push(
          lines[i]
            .split("|")
            .map((c) => c.trim())
            .filter((c, idx, arr) => !(c === "" && (idx === 0 || idx === arr.length - 1)))
        );
        i++;
      }
      out.push(
        <div key={`t${key++}`} className="overflow-x-auto my-4 rounded" style={{ border: `1px solid ${C.line}` }}>
          <table className="w-full text-sm" style={{ borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: C.ink }}>
                {header.map((h, hi) => (
                  <th
                    key={hi}
                    className="text-left px-3 py-2 whitespace-nowrap"
                    style={{ color: C.yellow, fontFamily: MONO, fontSize: 11, letterSpacing: "0.06em", textTransform: "uppercase" }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, ri) => (
                <tr key={ri} style={{ background: ri % 2 ? "#FAFAF7" : C.card, borderTop: `1px solid ${C.softLine}` }}>
                  {r.map((cell, ci) => (
                    <td key={ci} className="px-3 py-2 align-top" style={{ color: C.ink }}>
                      {renderInline(cell, `t${key}-${ri}-${ci}`)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      continue;
    }

    const h = line.match(/^(#{1,4})\s+(.*)/);
    if (h) {
      const level = h[1].length;
      const txt = h[2].replace(/\*\*/g, "");
      if (level <= 2) {
        out.push(
          <div key={`h${key++}`} className="mt-6 mb-2 flex items-center gap-2">
            <span style={{ width: 14, height: 14, background: C.yellow, border: `2px solid ${C.ink}`, flexShrink: 0 }} />
            <h3 className="font-bold uppercase" style={{ color: C.ink, fontFamily: MONO, fontSize: 13, letterSpacing: "0.1em" }}>
              {txt}
            </h3>
          </div>
        );
      } else {
        out.push(
          <h4 key={`h${key++}`} className="mt-4 mb-1 font-semibold" style={{ color: C.ink, fontSize: 15 }}>
            {txt}
          </h4>
        );
      }
      i++;
      continue;
    }

    if (/^(-{3,}|\*{3,})\s*$/.test(line.trim())) {
      out.push(<hr key={`r${key++}`} className="my-4" style={{ border: 0, borderTop: `1px solid ${C.line}` }} />);
      i++;
      continue;
    }

    const isBullet = (l) => /^\s*[-*+]\s+/.test(l);
    const isNum = (l) => /^\s*\d+[.)]\s+/.test(l);
    if (isBullet(line) || isNum(line)) {
      const ordered = isNum(line);
      const items = [];
      while (i < lines.length && (isBullet(lines[i]) || isNum(lines[i]))) {
        items.push(lines[i].replace(/^\s*([-*+]|\d+[.)])\s+/, ""));
        i++;
      }
      const ListTag = ordered ? "ol" : "ul";
      out.push(
        <ListTag key={`l${key++}`} className={`my-2 pl-5 space-y-1 ${ordered ? "list-decimal" : "list-disc"}`} style={{ color: C.ink }}>
          {items.map((it, ii) => (
            <li key={ii} className="text-sm leading-relaxed" style={{ color: "#2A2C28" }}>
              {renderInline(it, `l${key}-${ii}`)}
            </li>
          ))}
        </ListTag>
      );
      continue;
    }

    const para = [];
    while (
      i < lines.length &&
      lines[i].trim() &&
      !/^(#{1,4})\s/.test(lines[i]) &&
      !isBullet(lines[i]) &&
      !isNum(lines[i]) &&
      !lines[i].trim().startsWith("|")
    ) {
      para.push(lines[i]);
      i++;
    }
    out.push(
      <p key={`p${key++}`} className="my-2 text-sm leading-relaxed" style={{ color: "#2A2C28" }}>
        {renderInline(para.join(" "), `p${key}`)}
      </p>
    );
  }
  return <div>{out}</div>;
}

// ---------------- Loading ticker ----------------

function LoadingTicker({ messages, compact }) {
  const [idx, setIdx] = useState(0);
  const [dots, setDots] = useState("");
  useEffect(() => {
    const a = setInterval(() => setIdx((v) => (v + 1) % messages.length), 3200);
    const b = setInterval(() => setDots((d) => (d.length >= 3 ? "" : d + ".")), 450);
    return () => {
      clearInterval(a);
      clearInterval(b);
    };
  }, [messages.length]);
  return (
    <div className={`flex items-center gap-3 ${compact ? "py-3 px-4" : "py-6 px-5"}`}>
      <span className="inline-block animate-pulse" style={{ width: 12, height: 12, background: C.yellow, border: `2px solid ${C.ink}` }} />
      <span style={{ fontFamily: MONO, fontSize: 12, letterSpacing: "0.08em", color: C.gray, textTransform: "uppercase" }}>
        {messages[idx]}
        {dots}
      </span>
    </div>
  );
}

// ---------------- Severity chip ----------------

function Chip({ label }) {
  const s = SEV_COLORS[label] || { bg: "#E7E8E2", fg: "#141414" };
  return (
    <span
      className="px-2 py-1 inline-block"
      style={{ background: s.bg, color: s.fg, fontFamily: MONO, fontSize: 10, letterSpacing: "0.1em", fontWeight: 700 }}
    >
      {label || "—"}
    </span>
  );
}

// ---------------- Feed index (top 10 list) ----------------

function FeedIndex({ feedKey, state, onDeepDive, onRefresh, anyLoading }) {
  const feed = FEEDS[feedKey];
  return (
    <div className="mb-8" style={{ background: C.card, border: `1px solid ${C.line}` }}>
      <div className="flex items-center justify-between px-4 py-2" style={{ background: C.ink }}>
        <span style={{ fontFamily: MONO, fontSize: 11, letterSpacing: "0.14em", color: C.yellow }}>
          TOP 10 // {feed.tag} INDEX
        </span>
        <button
          onClick={() => !state.loading && onRefresh()}
          disabled={state.loading}
          style={{
            fontFamily: MONO,
            fontSize: 11,
            letterSpacing: "0.1em",
            color: state.loading ? "#6B6D67" : C.yellow,
            background: "transparent",
            border: "none",
            cursor: state.loading ? "not-allowed" : "pointer",
            textDecoration: "underline",
            textDecorationColor: C.yellow,
          }}
        >
          ↻ RESCAN
        </button>
      </div>

      {state.loading && <LoadingTicker messages={feed.indexLoading} />}

      {state.error && !state.loading && (
        <div className="px-5 py-4">
          <p className="text-sm mb-2" style={{ color: C.red }}>
            Couldn't build the index: {state.error}
          </p>
          <button
            onClick={onRefresh}
            className="px-4 py-2 text-xs font-bold"
            style={{ background: C.ink, color: C.yellow, fontFamily: MONO, letterSpacing: "0.08em" }}
          >
            RETRY
          </button>
        </div>
      )}

      {!state.loading &&
        !state.error &&
        state.items.map((item, idx) => (
          <div
            key={idx}
            className="flex gap-3 px-4 py-3 items-start flex-wrap sm:flex-nowrap"
            style={{ borderTop: idx === 0 ? "none" : `1px solid ${C.softLine}` }}
          >
            <span
              className="flex-shrink-0 pt-1"
              style={{ fontFamily: MONO, fontSize: 18, fontWeight: 800, color: idx < 3 ? C.ink : "#B8BAB4", width: 30 }}
            >
              {String(idx + 1).padStart(2, "0")}
            </span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap mb-1">
                <span className="font-bold text-sm" style={{ color: C.ink }}>
                  {item.title}
                </span>
                <Chip label={item.severity} />
                <span style={{ fontFamily: MONO, fontSize: 10, color: C.gray, letterSpacing: "0.06em" }}>
                  {[item.org, item.date, item.category].filter(Boolean).join(" · ").toUpperCase()}
                </span>
              </div>
              <p className="text-sm leading-snug" style={{ color: "#3A3C38" }}>
                {item.one_liner}
              </p>
            </div>
            <div className="flex-shrink-0 flex flex-col gap-1 self-center">
              <button
                onClick={() => !anyLoading && onDeepDive(item, "dive")}
                disabled={anyLoading}
                className="px-3 py-2 text-xs font-bold"
                style={{
                  fontFamily: MONO,
                  letterSpacing: "0.08em",
                  background: anyLoading ? "#E7E8E2" : C.yellow,
                  color: anyLoading ? "#9A9C96" : C.ink,
                  border: `2px solid ${anyLoading ? "#C9CBC4" : C.ink}`,
                  cursor: anyLoading ? "not-allowed" : "pointer",
                }}
              >
                DEEP-DIVE ▸
              </button>
              <button
                onClick={() => !anyLoading && onDeepDive(item, "pov")}
                disabled={anyLoading}
                className="px-3 py-2 text-xs font-bold"
                style={{
                  fontFamily: MONO,
                  letterSpacing: "0.08em",
                  background: anyLoading ? "#E7E8E2" : C.ink,
                  color: anyLoading ? "#9A9C96" : C.yellow,
                  border: `2px solid ${anyLoading ? "#C9CBC4" : C.ink}`,
                  cursor: anyLoading ? "not-allowed" : "pointer",
                }}
              >
                POV ▸
              </button>
            </div>
          </div>
        ))}
    </div>
  );
}

// ---------------- Briefing card ----------------

function BriefingCard({ briefing, num, onFollowUp, onPov }) {
  const [q, setQ] = useState("");
  const [collapsed, setCollapsed] = useState(false);
  const feed = FEEDS[briefing.feed];
  const isPov = briefing.kind === "pov";
  const time = new Date(briefing.ts).toLocaleString(undefined, {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div
      className="mb-6"
      style={{
        background: C.card,
        border: `1px solid ${C.line}`,
        borderLeft: isPov ? `6px double ${C.ink}` : `6px solid ${C.yellow}`,
      }}
    >
      <div
        className="flex items-center justify-between px-4 py-2 gap-2"
        style={{ background: C.ink, borderBottom: isPov ? `3px solid ${C.yellow}` : "none" }}
      >
        <span style={{ fontFamily: MONO, fontSize: 11, letterSpacing: "0.14em", color: C.yellow }}>
          {isPov ? "★ POV" : "BRIEFING"} Nº {String(num).padStart(3, "0")} // {feed.tag}
        </span>
        <div className="flex items-center gap-3">
          <span style={{ fontFamily: MONO, fontSize: 11, color: "#9A9C96" }}>{time}</span>
          <button
            onClick={() => setCollapsed((v) => !v)}
            style={{ fontFamily: MONO, fontSize: 11, color: C.yellow, background: "transparent", border: "none", cursor: "pointer" }}
          >
            {collapsed ? "▸ EXPAND" : "▾ COLLAPSE"}
          </button>
        </div>
      </div>

      {!collapsed && (
        <div className="px-5 pb-5">
          <div className="pt-4 pb-1" style={{ borderBottom: `1px solid ${C.softLine}` }}>
            <span style={{ fontFamily: MONO, fontSize: 11, color: C.gray, letterSpacing: "0.06em" }}>
              {isPov ? "POINT OF VIEW" : "REQUEST"} → {briefing.topic || "latest developments"}
            </span>
          </div>

          {briefing.status === "loading" && <LoadingTicker messages={isPov ? POV_LOADING : feed.loading} />}

          {briefing.status === "error" && (
            <div className="py-5">
              <p className="text-sm mb-3" style={{ color: C.red }}>
                Briefing failed: {briefing.error}. The research call didn't complete — this can happen on longer investigations.
              </p>
              <button
                onClick={() => onFollowUp(briefing.id, null, true)}
                className="px-4 py-2 text-sm font-semibold"
                style={{ background: C.ink, color: C.yellow, fontFamily: MONO, letterSpacing: "0.06em" }}
              >
                RETRY
              </button>
            </div>
          )}

          {briefing.exchanges.map((ex, xi) => (
            <div key={xi}>
              {xi > 0 && (
                <div className="mt-5 mb-1 px-3 py-2" style={{ background: "#FAFAF3", border: `1px dashed ${C.line}` }}>
                  <span style={{ fontFamily: MONO, fontSize: 11, color: C.gray, letterSpacing: "0.06em" }}>
                    FOLLOW-UP → {ex.q}
                  </span>
                </div>
              )}
              <MarkdownBlock md={ex.a} />
            </div>
          ))}

          {briefing.status === "done" && (
            <div className="mt-4 pt-4 flex gap-2" style={{ borderTop: `1px solid ${C.softLine}` }}>
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && q.trim()) {
                    onFollowUp(briefing.id, q.trim());
                    setQ("");
                  }
                }}
                placeholder="Drill deeper — ask a follow-up on this briefing…"
                className="flex-1 px-3 py-2 text-sm outline-none"
                style={{ border: `1px solid ${C.line}`, background: "#FCFCFA", fontFamily: SANS }}
              />
              <button
                onClick={() => {
                  if (q.trim()) {
                    onFollowUp(briefing.id, q.trim());
                    setQ("");
                  }
                }}
                className="px-4 py-2 text-xs font-bold"
                style={{ background: C.ink, color: C.yellow, fontFamily: MONO, letterSpacing: "0.08em" }}
              >
                ASK
              </button>
              {!isPov && (
                <button
                  onClick={() => onPov(briefing)}
                  className="px-4 py-2 text-xs font-bold"
                  style={{
                    background: C.ink,
                    color: C.yellow,
                    fontFamily: MONO,
                    letterSpacing: "0.08em",
                    border: `2px solid ${C.yellow}`,
                  }}
                  title="Generate a detailed partner-grade Point of View on this topic"
                >
                  ★ FULL POV
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------- App ----------------

export default function AppSecFeeder() {
  const [feed, setFeed] = useState("breach");
  const [topic, setTopic] = useState("");
  const [briefings, setBriefings] = useState([]);
  const [indexes, setIndexes] = useState({
    breach: { loading: false, items: [], error: null, loaded: false },
    tools: { loading: false, items: [], error: null, loaded: false },
    ai: { loading: false, items: [], error: null, loaded: false },
  });
  const counter = useRef(0);
  const reportRef = useRef(null);

  const patch = (id, fn) => setBriefings((prev) => prev.map((b) => (b.id === id ? fn(b) : b)));
  const patchIndex = (k, fn) => setIndexes((prev) => ({ ...prev, [k]: fn(prev[k]) }));

  async function loadIndex(feedKey) {
    patchIndex(feedKey, (s) => ({ ...s, loading: true, error: null }));
    try {
      const text = await callClaude([{ role: "user", content: FEEDS[feedKey].indexPrompt }]);
      const items = parseIndexJson(text);
      patchIndex(feedKey, () => ({ loading: false, items, error: null, loaded: true }));
    } catch (err) {
      patchIndex(feedKey, (s) => ({ ...s, loading: false, error: err.message, loaded: true }));
    }
  }

  // auto-load the index the first time a feed tab is opened
  useEffect(() => {
    if (!indexes[feed].loaded && !indexes[feed].loading) loadIndex(feed);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [feed]);

  async function generate(feedKey, rawTopic, kind = "dive") {
    const id = ++counter.current;
    const t = (rawTopic || "").trim();
    if (!t) return;
    const prompt = kind === "pov" ? povPromptFor(feedKey, t) : FEEDS[feedKey].prompt(t);
    const briefing = { id, num: id, feed: feedKey, topic: t, prompt, kind, status: "loading", error: null, exchanges: [], ts: Date.now() };
    setBriefings((prev) => [briefing, ...prev]);
    setTopic("");
    setTimeout(() => reportRef.current && reportRef.current.scrollIntoView({ behavior: "smooth", block: "start" }), 100);
    try {
      const text = await callClaude([{ role: "user", content: prompt }]);
      patch(id, (b) => ({ ...b, status: "done", exchanges: [{ q: null, a: text }] }));
    } catch (err) {
      patch(id, (b) => ({ ...b, status: "error", error: err.message }));
    }
  }

  async function followUp(id, question, isRetry = false) {
    const b = briefings.find((x) => x.id === id);
    if (!b) return;
    if (isRetry) {
      patch(id, (x) => ({ ...x, status: "loading", error: null }));
      try {
        const text = await callClaude([{ role: "user", content: b.prompt }]);
        patch(id, (x) => ({ ...x, status: "done", exchanges: [{ q: null, a: text }] }));
      } catch (err) {
        patch(id, (x) => ({ ...x, status: "error", error: err.message }));
      }
      return;
    }
    const history = [{ role: "user", content: b.prompt }];
    b.exchanges.forEach((ex) => {
      history.push({ role: "assistant", content: ex.a });
      if (ex.q) history.push({ role: "user", content: ex.q });
    });
    history.push({
      role: "user",
      content: `Follow-up question on the briefing above (use web search if needed, answer in markdown, stay technical and honest): ${question}`,
    });
    patch(id, (x) => ({ ...x, status: "loading" }));
    try {
      const text = await callClaude(history);
      patch(id, (x) => ({ ...x, status: "done", exchanges: [...x.exchanges, { q: question, a: text }] }));
    } catch (err) {
      patch(id, (x) => ({ ...x, status: "done" }));
    }
  }

  const active = FEEDS[feed];
  const visible = briefings.filter((b) => b.feed === feed);
  const anyLoading = briefings.some((b) => b.status === "loading");

  return (
    <div className="min-h-screen" style={{ background: C.paper, fontFamily: SANS }}>
      <header style={{ background: C.ink }}>
        <div className="max-w-4xl mx-auto px-5 py-5 flex items-end justify-between flex-wrap gap-3">
          <div>
            <div style={{ fontFamily: MONO, fontSize: 11, letterSpacing: "0.2em", color: C.yellow }}>
              APPSEC TEAM // INTERNAL INTELLIGENCE
            </div>
            <h1 className="font-black tracking-tight" style={{ color: "#FFFFFF", fontSize: 32, lineHeight: 1.1 }}>
              AppSec <span style={{ color: C.yellow }}>Feeder</span>
            </h1>
          </div>
          <div style={{ fontFamily: MONO, fontSize: 11, color: "#9A9C96", letterSpacing: "0.06em" }}>
            LIVE RESEARCH · AI-GENERATED · VERIFY BEFORE CLIENT USE
          </div>
        </div>
        <div className="max-w-4xl mx-auto px-5 flex gap-0 flex-wrap">
          {Object.entries(FEEDS).map(([k, f]) => {
            const on = k === feed;
            return (
              <button
                key={k}
                onClick={() => setFeed(k)}
                className="px-4 py-3 text-xs font-bold"
                style={{
                  fontFamily: MONO,
                  letterSpacing: "0.1em",
                  background: on ? C.paper : "transparent",
                  color: on ? C.ink : "#B8BAB4",
                  borderTop: on ? `3px solid ${C.yellow}` : "3px solid transparent",
                }}
              >
                {f.tag}
              </button>
            );
          })}
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-5 py-8">
        <div className="mb-6">
          <h2 className="font-black mb-1" style={{ color: C.ink, fontSize: 24 }}>
            {active.title}
          </h2>
          <p className="text-sm mb-4 max-w-2xl" style={{ color: C.gray }}>
            {active.blurb}
          </p>
          <div className="flex gap-2 max-w-2xl">
            <input
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && topic.trim() && !anyLoading) generate(feed, topic);
              }}
              placeholder={active.placeholder}
              className="flex-1 px-3 py-2 text-sm outline-none"
              style={{ border: `1px solid ${C.line}`, background: C.card }}
            />
            <button
              onClick={() => topic.trim() && !anyLoading && generate(feed, topic)}
              disabled={anyLoading}
              className="px-4 py-2 text-xs font-bold"
              style={{
                fontFamily: MONO,
                letterSpacing: "0.08em",
                background: C.ink,
                color: anyLoading ? "#6B6D67" : C.yellow,
                cursor: anyLoading ? "not-allowed" : "pointer",
              }}
            >
              RESEARCH
            </button>
          </div>
        </div>

        <FeedIndex
          feedKey={feed}
          state={indexes[feed]}
          onDeepDive={(item, kind) => generate(feed, `${item.title}${item.org ? ` (${item.org}` : ""}${item.date ? `, ${item.date})` : item.org ? ")" : ""}`, kind)}
          onRefresh={() => loadIndex(feed)}
          anyLoading={anyLoading}
        />

        <div ref={reportRef}>
          {visible.length > 0 && (
            <div className="mb-3" style={{ fontFamily: MONO, fontSize: 11, letterSpacing: "0.14em", color: C.gray }}>
              DEEP-DIVE BRIEFINGS ({visible.length})
            </div>
          )}
          {visible.map((b) => (
            <BriefingCard
              key={b.id}
              briefing={b}
              num={b.num}
              onFollowUp={followUp}
              onPov={(src) => !anyLoading && generate(src.feed, src.topic, "pov")}
            />
          ))}
        </div>
      </main>

      <footer className="max-w-4xl mx-auto px-5 pb-8">
        <div style={{ fontFamily: MONO, fontSize: 10, color: "#9A9C96", letterSpacing: "0.06em" }}>
          POC · BRIEFINGS ARE AI-RESEARCHED FROM PUBLIC SOURCES AND MAY CONTAIN ERRORS · SESSION-ONLY (NOT PERSISTED)
        </div>
      </footer>
    </div>
  );
}
