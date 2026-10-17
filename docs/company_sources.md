# Company-shaped sources for under-the-radar climate startups

Researched 2026-10-17. Why this file exists: GitHub and Hacker News show *public code*, not *companies*
(see the structural-flaw discussion). These sources start from companies, grants, filings and cohorts instead.

**Status legend.** *Verified* = I read the official documentation or repository page on the date above.
*To confirm* = the source exists but a detail (key, limits, terms, format) was not confirmed. Check it before building.
Only free sources with official APIs, open data, or openly published lists are included. Nothing here requires scraping
against a site's terms.

## A. Programmatic sources (free), ranked by value for this engine

"Description?" = does the record say what the company does (needed for the AI filter).
"Radar value" = how likely it is to surface a company that has not yet been widely covered.

| # | Source | What you get | Access | Description? | Radar value | Status |
|---|--------|--------------|--------|--------------|-------------|--------|
| 1 | **SBIR.gov awards** (DOE, NSF, EPA, USDA, NASA ...) <https://www.sbir.gov/api> | Tiny US companies that won federal R&D grants: firm name, abstract, keywords, amount, date | Award API, params `agency`, `year`, `firm`, `rows`, `start`; JSON default. No keyword parameter, so pull by agency and year, then filter locally | Yes (abstract) | High | Verified. **Page carries an "APIs undergoing maintenance" notice**: expect outages, check a bulk download as a fallback |
| 2 | **NSF Award Search API** <https://resources.research.gov/common/webapi/awardapisearch-v1.htm> | NSF-funded projects and companies (includes small-business programs, to confirm which filter isolates them); abstract | `http://api.nsf.gov/services/v1/awards.json?keyword=...` | Yes (abstract) | High | `keyword` and base URL verified. Key requirement, awardee/program filters and limits: to confirm. Docs mention weekend downtime |
| 3 | **YC company directory, unofficial JSON** <https://github.com/yc-oss/api> | YC companies with tags. Industry "Climate" (53) and "Energy" (51); tags ClimateTech, Renewable Energy, Energy Storage, Sustainability | Public JSON files, daily GitHub Actions refresh, built from YC's Algolia index. No key | Yes | Low (all funded) | Verified. Unofficial, **licence not stated**. Best used as the **known-positive calibration list** (section D), not as radar |
| 4 | **SEC EDGAR Form D** <https://www.sec.gov/data-research/sec-markets-data/form-d-data-sets> | Companies that quietly raised a private round: issuer name, industry group, offering amount, date of first sale, state, year of incorporation, related persons (founders/directors) | Quarterly ZIP datasets (2008 to Sep 2026) plus daily index at `/Archives/edgar/daily-index`. Declare a User-Agent with contact email; max 10 requests/second | **No** (name only) | High | Verified. Industry field top level includes "Energy"; finer sub-types: to confirm. Needs a website lookup before the AI can judge a company. Includes funds, so exclude "Pooled Investment Fund" |
| 5 | **Companies House (UK)** <https://developer.company-information.service.gov.uk/> | Newly incorporated UK companies | `GET https://api.company-information.service.gov.uk/advanced-search/companies` with `company_name_includes`, `sic_codes`, `incorporated_from/to`, `size` up to 5000. API key from a free account | **No** | Medium: earliest possible signal, but noisy | Endpoint and parameters verified. "Free" and the rate limit are not stated on the pages I read: confirm in the developer guidelines |
| 6 | **UKRI Gateway to Research** <https://gtr.ukri.org/resources/api.html> | Innovate UK and UKRI funded projects with participating organisations | REST API (projects, organisations, people, search endpoints) | Yes | Medium-High | Endpoints verified. Key, limits, licence: to confirm |
| 7 | **CORDIS (EU research and EIC)** <https://cordis.europa.eu/about/services> | Horizon Europe / EIC projects and participating SMEs | EU Open Data Portal dataset "CORDIS EU research projects under Horizon Europe (2021-2027)" | Yes | Medium-High | Dataset exists; **formats, licence and the SME flag: to confirm** on data.europa.eu |
| 8 | **CarbonPlan CDR database** <https://github.com/carbonplan/cdr-database> | Carbon-removal projects and technologies | Open repo, data folder. Code MIT, some data CC-BY-4.0 (keep attribution) | Partly | Medium (niche) | Verified. Content scope and freshness not clear from the page |
| 9 | **Product Hunt API** <https://api.producthunt.com/v2/docs> | Product launches (GraphQL) | Free developer token. **Default terms forbid commercial use** (ask hello@producthunt.com for business use) | Yes | Medium | Token and terms verified. Topic filter and rate limits: to confirm. Fine for a personal portfolio project |
| 10 | **Hacker News: "Who is hiring" threads, "Launch HN"** <https://hn.algolia.com/api> | Small teams hiring (a real traction proxy) and YC launches | Same Algolia API as `src/ingest_hn.py` | Yes | Medium | The API is verified; the specific tags and thread structure: to confirm |
| 11 | **USPTO patents, CPC class Y02 (climate mitigation)** <https://data.uspto.gov/> | Patent filers in climate technologies, including small entities | PatentsView is **moving into the USPTO Open Data Portal** (redirect observed) | Yes (abstract) | High, but phase 2 | **To confirm**: new endpoints, key, and whether Y02 can be filtered |

**Verified-but-gated (not free): CDR.fyi API** <https://www.cdr.fyi/blog/introducing-cdr-fyi-api>.
Orders, suppliers, marketplaces and purchasers, but only for Data Partners or Team+ plans, with an API key.
Not usable on a zero budget. Their public website can still be browsed by hand for radar checks.

## B. Curated lists (human reading, no API)

These are cohort announcements and directories. They are company-shaped and often early. Method: copy names and websites
into `data/manual_leads.csv` (columns: `name,url,description,source_list,date_added`). A small collector can merge them
into the pipeline with `source = manual`.

| Source | Why it matters | Link |
|--------|----------------|------|
| Breakthrough Energy Fellows cohorts | Very early companies chosen by a major climate funder; cohort pages list every company, including a Southeast Asia cohort (Oct 2025) | <https://breakthroughenergy.org/news/cohort-3-fellows> |
| Greentown Labs "newest startups" (quarterly) | Hardware and climate startups joining a major US climatetech incubator; one post per quarter | <https://greentownlabs.com/meet-our-members-introducing-greentowns-newest-startups-of-q1-2026/> |
| Techstars accelerator classes | Per-class company lists (Fall 2026 and earlier) | <https://www.techstars.com/newsroom/introducing-techstars-fall-2026-accelerator-class> |
| Challenger Sustainability Accelerator | 2026 cohort | <https://www.challengeraccelerator.com/challenger-ai-news/announcing-the-challenger-sustainability-accelerator-2026-cohort> |
| Venture for ClimateTech | Accelerator, cohort 6 | <https://www.globenewswire.com/news-release/2026/01/06/3213627/0/en/venture-for-climatetech-accelerator-launches-applications-for-cohort-6.html> |
| Tech Nation: 25 UK climate tech startups (2026) | Curated UK list | <https://technation.io/tech-nation-climate-tech-startups-2026/> |
| Cleantech Open regional programs | Long-running accelerator with regional finalists | <https://cleantechopen.org/en/page/2026-cto-accelerator-en> |
| Climatescape | Directory in 12 sectors plus capital and program types. **No API or export found**, so browse only | <https://climatescape.org> |
| India: EAI "India Climate Tech 100" | Indian climate startups grouped by decarbonization area | <https://www.eai.in/blog/2024/01/india-climate-tech-100.html> |
| India: MUFG "India Climate Tech Startup Landscape" | Landscape PDF | <https://www.bk.mufg.jp/global/globalnetwork/asiaoceania/pdf/India_Climate_Tech_Startup_Landscape.pdf> |
| India: C-CAMP climate cohort | Biology-driven climate startups (11 selected in one cohort) | <https://biospectrumindia.com/news/102/28587/c-camp-in-collaboration-with-ashraya-hastha-trust-selects-11-biology-driven-startups-to-accelerate-climate-action.html> |
| India: Villgro climate programs | Early-stage climate and impact startups | <https://villgro.org> |

Not yet checked, worth a look: ARPA-E project lists (<https://arpa-e.energy.gov>), DOE lab-embedded entrepreneurship cohorts,
XPRIZE Carbon Removal teams, Frontier offtake recipients.

## C. Skipped on purpose
- **Crunchbase, PitchBook, Dealroom, Wellfound, LinkedIn:** paid or terms forbid scraping. Use them **by hand** only for the
  radar check on your final top 5 (Day 10).
- **Sightline Climate (formerly CTVC) database:** paid.

## D. How these plug into the engine

1. **Entity = website domain.** Every row should carry a `homepage`. Merge rows from all sources on the domain, so a
   company seen in SBIR, on Show HN and in a cohort list is one row with several evidence lines.
2. **Name-only sources (Form D, Companies House)** cannot be judged by the AI from a name. Use them as a **cross-check**
   ("does this company legally exist and has it filed a raise?") and for the radar check, or add a website-lookup step.
3. **Calibration list.** Use the YC "Climate" and "Energy" companies (about 100) as **known real companies**. Run the
   filter on them and measure how many it keeps. This gives a recall test that does not depend on rare positives in a
   random sample.
4. **Replace stars-based traction** with signals these sources provide: grants won, filings, cohort membership, hiring posts.

## E. Limits to state in the README
- Mostly US, UK and EU sources. India coverage is manual lists only.
- Grant and filing sources skew toward deep-tech and hardware-adjacent companies; consumer and services climate
  companies will be under-represented.
- "Under the radar" here means "no widely covered funding at the date checked". A Form D or grant is itself evidence that
  someone has already funded the company, so these companies are early, not unfunded.
- Terms of use and rate limits change. Re-check before each new collector, and keep a User-Agent with a contact email.
