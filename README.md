# AMM Revision Engineer — Claude Code Skill

> **Agentic Aviation** | by Emin Öztürk
> Automate the work of an AMM Revision Engineer using AI

[![Live Demo](https://img.shields.io/badge/Live%20Demo-View%20Report-f59e0b?style=for-the-badge&logo=googlechrome&logoColor=white)](https://eminozturk1986.github.io/AMM-revision-engineer/)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-0f172a?style=for-the-badge&logo=github&logoColor=white)](https://github.com/eminozturk1986/AMM-revision-engineer)

---

## 🎯 What This Skill Does

When an OEM publishes a new AMM revision, someone has to read every changed page and figure out:

- Did any scheduled interval change? → **CAMO needs to amend the AMP**
- Did any new special test appear? → **MRO needs borescope / NDT crew**
- Did any new tool get required? → **Stores needs to procure it**
- Did any material specification change? → **QA needs to update approved materials list**
- Were any tasks added or deleted? → **Work packages need updating**

This Claude Code skill automates that entire process.

---

## 👥 Two User Modes

| Mode | Who Uses It | Primary Focus |
|------|-------------|---------------|
| **MRO Mode** | Maintenance Planning Engineers | New tools, materials, special tests, man-hours |
| **CAMO Mode** | Airworthiness / Planning Engineers | Interval changes vs. AMP, authority notifications |

---

## 📁 Repository Structure

```
AMM-revision-engineer/
├── SKILL.md                          ← Main skill instructions for Claude Code
├── references/
│   ├── parsing_guide.md              ← How to extract data from AMM PDFs/text
│   ├── excel_template_guide.md       ← Excel report format & openpyxl code
│   ├── ata_chapters.md               ← ATA 100 chapter reference
│   └── aviation_glossary.md          ← Key aviation MRO/CAMO terms
├── sample_data/
│   ├── README.md                     ← How to use sample data
│   ├── amm_revisions/
│   │   ├── cessna172_amm_rev15_excerpt.txt   ← Baseline AMM (synthetic)
│   │   └── cessna172_amm_rev21_excerpt.txt   ← New revision (synthetic, with deliberate changes)
│   └── amp_excel/
│       └── sample_AMP_cessna172.xlsx         ← Simulated airline AMP
└── README.md                         ← This file
```

---

## 🚀 Quick Start

### Installation in Claude Code

```bash
# Clone this repository
git clone https://github.com/eminozturk1986/AMM-revision-engineer.git

# Copy skill to your Claude Code skills directory
cp -r AMM-revision-engineer ~/.claude/skills/
```

Or install via Claude Code skill management if `.skill` packaging is supported.

### Basic Usage

Once installed, Claude Code will automatically trigger this skill when you use phrases like:

- *"Analyze the AMM revision delta between Rev 15 and Rev 21"*
- *"Check if any intervals changed in the new AMM revision"*
- *"What new tools are required after the AMM update?"*
- *"Update the AMP impact matrix based on the new revision"*

### Example Prompt (CAMO Context)

```
I've uploaded two AMM excerpts for our Cessna 172 fleet:
- cessna172_amm_rev15_excerpt.txt (old baseline)
- cessna172_amm_rev21_excerpt.txt (new revision)
- sample_AMP_cessna172.xlsx (our current AMP)

Please analyze the AMM revision delta from a CAMO perspective.
Identify all interval changes, flag which AMP tasks are affected,
and tell me which changes require authority notification.
Generate an impact report in Excel.
```

### Example Prompt (MRO Context)

```
We have a C-check coming up on D-EABC (Cessna 172).
The OEM just released AMM Revision 21.
Compare it to our Rev 15 baseline and tell me:
- What new special tests are required?
- What new tools do I need to procure?
- What new materials are needed?
- How have man-hours changed?
Generate an Excel report for the maintenance planner.
```

---

## 🧪 Test Data

The `sample_data/` folder contains **synthetic** (not copyrighted) AMM excerpts and an AMP designed to test all skill capabilities.

### Changes embedded in Rev 21 for testing:

| Change | Type | Priority |
|--------|------|----------|
| Fuel Filter: 100 FH → 50 FH | `INTERVAL_REDUCED` | 🔴 HIGH |
| Battery check: 90 days → 60 days | `INTERVAL_REDUCED` | 🔴 HIGH |
| Engine Mount: 500 FH → 300 FH | `INTERVAL_REDUCED` | 🔴 HIGH |
| Borescope inspection (new) | `NEW_TASK` + `NEW_SPECIAL_TEST` | 🟡 MEDIUM |
| Wheel Bearing Repack (new) | `NEW_TASK` | 🟡 MEDIUM |
| Torque Link Lubrication (new) | `NEW_TASK` | 🟡 MEDIUM |
| Brake fluid spec: MIL-H-5606 → MIL-PRF-5606 | `MATERIAL_CHANGED` | 🟡 MEDIUM |
| Borescope equipment required | `NEW_TOOL` | 🟡 MEDIUM |
| Wheel bearing grease MIL-PRF-81322 | `NEW_MATERIAL` | 🟡 MEDIUM |
| Annual MH: 16 → 19 hours | `MH_CHANGE` | 🟢 LOW |

---

## 📦 Output Formats

The skill generates:

1. **Excel Report** (`.xlsx`) with 6 sheets:
   - SUMMARY — dashboard with counts and priorities
   - ALL_CHANGES — complete delta table
   - MRO_ACTION_ITEMS — filtered for tools/materials/tests
   - CAMO_AMP_IMPACT — interval changes vs. AMP
   - NEW_TASKS — new tasks requiring engineering review
   - DELETED_TASKS — tasks removed from AMM

2. **Markdown Summary** — quick review text with priority actions

---

## 🔧 Technical Requirements

```
Python 3.10+
pdfplumber or PyMuPDF   (PDF parsing)
pandas                   (data processing)
openpyxl                 (Excel generation)
rich                     (terminal output)
```

```bash
pip install pdfplumber pandas openpyxl rich
```

---

## ✈️ About Agentic Aviation

This skill is part of the **Agentic Aviation** suite — AI agents that automate aviation MRO and CAMO engineering workflows.

Other agents in the suite:
- 🔍 **CAMO AD Monitor** — EASA/FAA Airworthiness Directive tracking
- 🧾 **Invoice Check Engineer** — Automated MRO invoice auditing  
- 🔧 **Warranty Engineer Agent** — Automated warranty claim processing

---

## 📜 License

MIT License — Free for aviation industry use.

**Disclaimer:** This tool is an engineering aid only. All output must be verified
by a qualified aviation maintenance engineer. Do not use as sole basis for
airworthiness decisions. Always refer to the original OEM documentation.

---

*Built with ❤️ for the aviation maintenance community*
