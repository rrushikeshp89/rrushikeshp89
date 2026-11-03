<a href="https://github.com/rrushikeshp89">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/header-dark.svg">
    <img src="assets/header-light.svg" width="100%" alt="Rushikesh Panchal: I build software that can explain itself. Full-stack engineering, explainable AI and business systems.">
  </picture>
</a>

<p align="center">
  <a href="#selected-work">Selected work</a> &nbsp;·&nbsp;
  <a href="#explainable-ai-and-data-science">AI and data science</a> &nbsp;·&nbsp;
  <a href="#how-i-work">How I work</a> &nbsp;·&nbsp;
  <a href="#toolbox">Toolbox</a> &nbsp;·&nbsp;
  <a href="#get-in-touch">Get in touch</a>
</p>

<br>

I came to software through data science, and I still think like an analyst: **if a system gives you a number, it should be able to tell you why.** That idea runs through everything here. A clinical model gives a reason with every risk score, a résumé matcher shows its arithmetic, and a CRM labels its estimates as estimates.

Lately I build complete business systems (HR, inventory, sales) end to end: the data model, permissions enforced on the server, an accessible interface, the tests and the deployment. Each one ships with a live demo and an honest list of what it doesn't do yet.

<br>

<table align="center">
  <tr>
    <td align="center" width="170"><h3>6</h3><sub>public projects</sub></td>
    <td align="center" width="170"><h3>4</h3><sub>live demos</sub></td>
    <td align="center" width="170"><h3>830+</h3><sub>automated tests</sub></td>
    <td align="center" width="170"><h3>100</h3><sub>Lighthouse accessibility<br>score on Grove</sub></td>
  </tr>
</table>

<br>

## Selected work

### <img src="assets/logo-grove.svg" width="26" height="26" align="top" alt=""> Grove &nbsp;<sup><sub>HRMS · flagship</sub></sup>

<a href="https://grove-hrms.vercel.app"><img src="https://raw.githubusercontent.com/rrushikeshp89/grove-hrms/main/docs/screenshots/home.png" width="100%" alt="Grove home screen: a greeting, leave balances as rings, a press-and-hold clock-in button, this month's attendance and unread announcements"></a>

**An HR system people actually enjoy using.** People, attendance, leave, payroll, hiring, performance and analytics for a company of about 100, with separate experiences for employees, managers, HR and admins.

- **45 tables, 23 feature modules, 4 roles** with scoped, record-level permissions
- **One door for every change:** sign-in check, Zod validation and permission check, then the change, its audit entries and its notifications commit in one transaction, or none of them do
- **A four-eyes rule on payroll:** whoever prepares a pay run can't finalize it
- **369 unit and 420 end-to-end tests**, 0 serious axe violations, keyboard shortcuts for everything, light and dark themes checked against WCAG AA by a test

<sub>`Next.js 16` `React 19` `TypeScript` `Prisma 7` `PostgreSQL` `Supabase` `Better Auth` `Tailwind 4` `Radix` `Playwright`</sub>

[**Open the live demo →**](https://grove-hrms.vercel.app) &nbsp;·&nbsp; [Source](https://github.com/rrushikeshp89/grove-hrms) &nbsp;·&nbsp; [Design system](https://grove-hrms.vercel.app/design)

<br>

<table>
  <tr>
    <td width="50%" valign="top">
      <a href="https://stockroom-erp.onrender.com"><img src="https://raw.githubusercontent.com/rrushikeshp89/stockroom-erp/main/docs/screenshots/dashboard.png" alt="Stockroom dashboard with inventory health, purchases and consumption chart, and a purchase-order table"></a>
      <h3><img src="assets/logo-stockroom.svg" width="22" height="22" align="top" alt=""> Stockroom <sup><sub>ERP</sub></sup></h3>
      <p><b>Inventory and purchase orders for small shops and cafés.</b> It knows what's in the back room and suggests what to reorder before it runs out.</p>
      <ul>
        <li>Stock changes <b>only when goods arrive</b>, in one all-or-nothing transaction. Database triggers block direct edits and negative stock</li>
        <li>Access control in four layers: route permissions, row scope, per-record rules with separation of duties, and field masking</li>
        <li>Layout shift ≤ 0.004, no sideways scrolling from 360 to 1920 px, full flow works keyboard-only, measured in 175 audit runs</li>
      </ul>
      <sub><code>React 18</code> <code>TypeScript</code> <code>Express 5</code> <code>SQLite</code> <code>Zod</code> <code>JWT</code></sub>
      <p><a href="https://stockroom-erp.onrender.com"><b>Live demo →</b></a> &nbsp;·&nbsp; <a href="https://github.com/rrushikeshp89/stockroom-erp">Source</a></p>
    </td>
    <td width="50%" valign="top">
      <a href="https://leadhub-9stj.onrender.com/inquiry"><img src="https://raw.githubusercontent.com/rrushikeshp89/leadhub-crm/main/docs/screenshots/pipeline.png" alt="LeadHub pipeline board with deal cards in stage columns and pipeline totals"></a>
      <h3><img src="assets/logo-leadhub.svg" width="22" height="22" align="top" alt=""> LeadHub <sup><sub>CRM</sub></sup></h3>
      <p><b>A sales CRM for teams selling software, AI and consulting.</b> Leads, a 10-stage pipeline, proposals and follow-ups in one place.</p>
      <ul>
        <li>Weighted forecasts, and only Closed Won counts as revenue. A lost deal always needs a reason</li>
        <li>A public inquiry form becomes a lead and a follow-up task, assigned to the least-busy rep</li>
        <li>Optional Claude assistant for summaries, next steps and email drafts. It suggests and never changes data on its own</li>
        <li>37 tests, including 12 simultaneous writes. The Docker image is tested in CI and <code>npm audit</code> reports 0 vulnerabilities</li>
      </ul>
      <sub><code>React 18</code> <code>TypeScript</code> <code>Express 5</code> <code>libSQL / Turso</code> <code>Docker</code> <code>Claude API</code></sub>
      <p><a href="https://leadhub-9stj.onrender.com/inquiry"><b>Try the inquiry form →</b></a> &nbsp;·&nbsp; <a href="https://github.com/rrushikeshp89/leadhub-crm">Source</a></p>
    </td>
  </tr>
</table>

<br>

## Explainable AI and data science

<table>
  <tr>
    <td width="33%" valign="top">
      <h3><img src="assets/logo-tessaract.svg" width="20" height="20" align="top" alt=""> Tessaract</h3>
      <p><b>Résumé-to-job matching that shows its work.</b></p>
      <p>Every fit score breaks down into four weighted parts, with matched and missing skills, a gap report and a blind mode that hides identity. Core scoring needs no LLM API.</p>
      <pre>fit = 0.40 × semantic
    + 0.35 × skills
    + 0.15 × experience
    + 0.10 × education</pre>
      <sub><code>FastAPI</code> <code>Sentence-Transformers</code> <code>PostgreSQL</code> <code>Redis</code> <code>React 19</code> <code>Docker</code></sub>
      <p><a href="https://github.com/rrushikeshp89/Tessaract">Source →</a></p>
    </td>
    <td width="33%" valign="top">
      <h3><img src="assets/logo-strategyroom.svg" width="20" height="20" align="top" alt=""> StrategyRoom.ai</h3>
      <p><b>Investment research by two cooperating agents.</b></p>
      <p>A researcher agent gathers live sources with Firecrawl, and an analyst agent built on Gemini 2.5 Flash returns Buy, Hold or Sell with a confidence breakdown, its reasoning and citations. It adds watchlists, alerts, sector scans and scheduled re-research.</p>
      <sub><code>React</code> <code>TypeScript</code> <code>Supabase Edge Functions</code> <code>Postgres RLS</code> <code>Gemini</code> <code>Firecrawl</code></sub>
      <p><a href="https://github.com/rrushikeshp89/StrategyRoom.ai">Source →</a></p>
    </td>
    <td width="33%" valign="top">
      <h3>🛡️ Readmission Shield</h3>
      <p><b>An early warning for 30-day hospital readmission.</b></p>
      <p>The model flags diabetic patients at risk before discharge. On a 9:91 class imbalance, XGBoost with class weighting reaches <b>0.55 recall</b> and <b>0.65 AUC</b>. SHAP gives clinicians a reason for every score, and a QA gatekeeper checks for data leakage before release.</p>
      <sub><code>Python</code> <code>XGBoost</code> <code>SHAP</code> <code>pandas</code> <code>Streamlit</code></sub>
      <p><a href="https://hospital-readmission-shield-diabetes-mxh3cfy4tg5movmukaphtm.streamlit.app/"><b>Live app →</b></a> &nbsp;·&nbsp; <a href="https://github.com/rrushikeshp89/Hospital-Readmission-Shield-Diabetes">Source</a></p>
    </td>
  </tr>
</table>

<br>

## How I work

<table>
  <tr>
    <td width="33%" valign="top">
      <b>Show the why</b><br><br>
      A score comes with its breakdown and a verdict comes with its sources. An estimate is labelled as one. People trust what they can check.
    </td>
    <td width="33%" valign="top">
      <b>Enforce it on the server</b><br><br>
      Permissions, state machines and money rules live on the server and in database constraints, never only in the UI. The browser hides buttons, and the server decides.
    </td>
    <td width="33%" valign="top">
      <b>Prove it, then say what's missing</b><br><br>
      Tests for business rules, browser tests for flows, accessibility scans in both themes. Every README says plainly what isn't built yet.
    </td>
  </tr>
</table>

<br>

## Toolbox

<p>
  <img src="https://skillicons.dev/icons?i=ts,react,nextjs,nodejs,express,py,fastapi,postgres,sqlite,redis,prisma,supabase,tailwind,vite,docker,githubactions,vercel,figma&perline=9" alt="TypeScript, React, Next.js, Node.js, Express, Python, FastAPI, PostgreSQL, SQLite, Redis, Prisma, Supabase, Tailwind CSS, Vite, Docker, GitHub Actions, Vercel, Figma">
</p>

| Area | Tools |
| --- | --- |
| **Languages** | TypeScript, Python, SQL |
| **Front end** | React 18 and 19, Next.js 16 (Server Components and Actions), Tailwind, Radix, Motion, Recharts, TanStack Table |
| **Back end and data** | Node.js, Express 5, FastAPI, PostgreSQL, SQLite and libSQL, Redis, Prisma, Supabase (Auth, Edge Functions, RLS) |
| **AI and ML** | Claude API, Gemini, Sentence-Transformers, XGBoost, SHAP, scikit-learn, pandas, multi-agent orchestration |
| **Quality** | Vitest, Playwright, axe-core, Lighthouse, WCAG 2.1 AA, node:test, pytest |
| **Delivery** | Docker, GitHub Actions, Vercel, Render, Streamlit Cloud, Dependabot |

<br>

## Along the way

| When | What I built | Focus |
| --- | --- | --- |
| Nov 2026 | [**Grove**](https://github.com/rrushikeshp89/grove-hrms) HRMS | My own design system, a full HR suite, and 789 tests behind it |
| Oct 2026 | [**Stockroom**](https://github.com/rrushikeshp89/stockroom-erp) ERP · [**LeadHub**](https://github.com/rrushikeshp89/leadhub-crm) CRM | Integrity enforced by the database itself, and a CRM in use by a real team |
| Mar 2026 | [**Tessaract**](https://github.com/rrushikeshp89/Tessaract) · [**StrategyRoom.ai**](https://github.com/rrushikeshp89/StrategyRoom.ai) | Explainable scoring and multi-agent AI that people can audit |
| Dec 2025 | [**Readmission Shield**](https://github.com/rrushikeshp89/Hospital-Readmission-Shield-Diabetes) | Clinical machine learning on imbalanced data, explained with SHAP |

<br>

## Get in touch

<p>
  <a href="mailto:rrushikeshp8@gmail.com"><img src="https://img.shields.io/badge/Email-rrushikeshp8%40gmail.com-1C1B18?style=for-the-badge&logo=gmail&logoColor=white" alt="Email: rrushikeshp8@gmail.com"></a>
  <a href="https://www.linkedin.com/in/rushikesh-panchal"><img src="https://img.shields.io/badge/LinkedIn-rushikesh--panchal-1F5A47?style=for-the-badge&logo=linkedin&logoColor=white" alt="LinkedIn: rushikesh-panchal"></a>
  <a href="https://orcid.org/0009-0001-8991-1702"><img src="https://img.shields.io/badge/ORCID-0009--0001--8991--1702-3D3A36?style=for-the-badge&logo=orcid&logoColor=white" alt="ORCID: 0009-0001-8991-1702"></a>
</p>

If something here is useful to you, or you'd like to talk about building something similar, I'd be glad to hear from you.

<br>

<p align="center"><sub>Every company, person and figure in the screenshots is fictional demo data.</sub></p>
