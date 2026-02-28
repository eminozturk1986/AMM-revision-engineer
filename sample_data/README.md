# Sample Data — AMM Revision Engineer Skill

## What's Here

This folder contains **synthetic** test data that simulates real AMM revision analysis scenarios.
All content is original — not copied from any manufacturer documentation.

---

## AMM Revision Excerpts (Cessna 172 Simulated)

We chose the Cessna 172 as the reference aircraft because:
- It's the most widely trained-on light aircraft in the world
- Its general structure (ATA chapters, task types) mirrors commercial aircraft AMMs
- Multiple public domain references exist for structural comparison
- The skill logic translates directly to B737/A320 AMMs (just more chapters)

### Files

| File | Represents | Key Content |
|------|-----------|-------------|
| `amm_revisions/cessna172_amm_rev15_excerpt.txt` | Rev 15 (Dec 1996) baseline | ATA 05, 12, 32, 71 tasks |
| `amm_revisions/cessna172_amm_rev21_excerpt.txt` | Rev 21 (Jul 2007) — new revision | Same chapters with deliberate changes |

### Embedded Changes (Rev 15 → Rev 21)

The Rev 21 file has these deliberate changes for testing:

**INTERVAL REDUCTIONS (most important for CAMO):**
- `ATA 05`: Fuel Filter 100 FH → 50 FH
- `ATA 05`: Battery check 90 Days → 60 Days  
- `ATA 71`: Engine mount 500 FH → 300 FH

**NEW TASKS (require AMP evaluation):**
- `ATA 71`: Engine cylinder borescope inspection @ 600 FH/Annual
- `ATA 32`: Wheel bearing inspection and repack @ 500 FH/Annual
- `ATA 12`: Landing gear torque link lubrication @ 200 FH/Annual

**NEW TOOLS:**
- Borescope (Olympus IPLEX SA or equivalent)
- Wheel bearing packing tool
- Grease gun with needle adapter

**NEW MATERIALS:**
- MIL-PRF-81322 wheel bearing grease (new P/N class)
- MIL-PRF-5606 brake fluid (spec revision of MIL-H-5606)
- MIL-PRF-680 Type II system flush solvent

**MAN-HOUR CHANGES:**
- Annual: 16.0 → 19.0 MH (+3.0 MH due to borescope)
- 100-Hour: 8.0 → 9.5 MH

---

## Sample AMP (`amp_excel/sample_AMP_cessna172.xlsx`)

This Excel file simulates a CAMO's Approved Maintenance Programme with:

- **AMP_Tasks sheet**: 12 current scheduled maintenance tasks
- **Fleet_Register sheet**: 4 aircraft in the simulated fleet
- **AMM_Impact_Tracking sheet**: Empty template for the skill to populate
- **README sheet**: Instructions

### AMP Tasks Summary

| AMP Task | Description | Current Interval |
|----------|-------------|-----------------|
| AMP-001 | Annual Inspection | 12 Months |
| AMP-002 | 100-Hour Inspection | 100 FH |
| AMP-003 | Oil Change | 100 FH / 4 Mo |
| AMP-004 | Fuel Filter Replacement | 100 FH / 12 Mo → **needs update to 50 FH** |
| AMP-005 | Battery Inspection | 100 FH / 90 Days → **needs update to 60 Days** |
| AMP-006 | Brake Fluid Check | 100 FH → **fluid spec change** |
| AMP-007 | Wheel and Brake Inspection | 100 FH / Annual |
| AMP-008 | Engine Mount Inspection | 500 FH / Annual → **needs update to 300 FH** |
| AMP-009 | Spark Plug Inspection | 100 FH |
| AMP-010 | Alternator Belt | 100 FH |
| AMP-011 | Flight Control Rigging | Annual |
| AMP-012 | Compass Swing | Annual |

---

## Using Real AMMs for Testing

When you have access to real AMM documents, the skill works with:

1. **PDF files** — upload directly, skill uses pdfplumber to extract
2. **Text exports** — paste extracted text
3. **Multiple chapters** — provide full revision or specific ATA chapters

### Public AMM Sources for Reference

- **Cessna 172 (1996 Series)**: Available on ManualsLib  
  https://www.manualslib.com/manual/1637920/Cessna-172-Series-1996.html
  
- **FAA NTSB Document Library**: Contains inspection table excerpts  
  https://data.ntsb.gov/ (search for specific aircraft maintenance data)

- **WT9 Dynamic LSA**: Complete free AMM available  
  https://www.tmg-service.de/doc-download/manuals/AMM-20-01_%20E_2-16.pdf

> **Note**: For commercial aircraft (B737, A320), AMMs are proprietary.
> Access requires Boeing/Airbus customer credentials (MyBoeingFleet, Airbus World).
> The skill is designed to work with whatever format you have access to.
