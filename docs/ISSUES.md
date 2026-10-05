# Issues

## 2026-10-05: My smoke test was using an old report

- **What I saw:** The Project 04 checker said the first purchase had not landed, even though I had already finished the sign, verify, submit, and receipt steps. The report showed the first case stopped at `sign is not written yet`.
- **What was actually wrong:** `smoke-report.json` came from an earlier run, before I finished the purchase loop. The code was updated, but the saved report was not.
- **How I found it:** I opened `smoke-report.json` and saw that `1-espresso` ended at the `sign` step instead of ending with a receipt.
- **What I changed:** I ran `make smoke-recorded` first to confirm the offline fallback still worked. Then I ran `make smoke` on devnet again. The new report shows one Espresso purchase landed and the other five cases were stopped safely.
- **What it cost:** One intentional devnet Espresso purchase: 1,000,000 raw class tokens and a small devnet SOL fee. The other five cases did not sign anything.
- **Would the checks have caught it?** Yes. The Project 04 checker caught it because the first case had no reconciled receipt and the live report did not match the recorded report.
