# DOCUMENT SCAFFOLD — ASIC puzzle writeup

Repo: `/Users/jacobcrainic/asic-puzzle-2026`. All numbers below are the verified ones. Nothing here is drafted prose; every entry is an instruction about what a sentence must do.

---

## 0. Logistics that constrain the document (decide before writing)

- Two deliverables, different shapes. Google Form before **Sept 4 2026** wants "a brief description of how you did it" — that is ~200 words, not this document. This document is the **post-close publication** that gets emailed to `asic-puzzle@janestreet.com` for the follow-up post.
- Publish nothing public before Sept 4 (their spoiler rule is verbatim and explicit).
- Two artifacts, one repo: the **narrative writeup** (this scaffold) and the **repo as reference** (`TOOLCHAIN.md` already exists and is the "others can reference and learn from" axis). Do not merge them — the narrative must not become an install guide.
- AI rule: writeup must be human-written. Scripts were fine to generate. Note under Risks (§6) how to handle this — the genre answer is *do not mention it at all*, but do include a ground-truth provenance sentence.

---

## 1. Recommended shape and length

**Shape: result-first, then pipeline order, with two narrative set-pieces placed for maximum load (the cycle-124 miter failure, and the output generator).**

**Target: 3,000–3,600 words of narrative + one summary table + one block ledger table + 3 figures + ~6 blocks of pasted raw tool output. Hard ceiling 4,000.**

Justification from the research:

- Jane Street's own featured favourite (Gajdusek) is **~2,600 words** and won on evidence density, not length. Their in-house deep technical posts run 13–21 min read (~3,000–5,000 words). 3,000–3,600 sits exactly in their house band.
- Jhaveri's 15,000-word README was also featured — but for *breadth over 12 days*. This is one chip, one solve; length here must come from evidence, not coverage. If it passes 4,000 words, evidence has been replaced by explanation.
- Skarman (~550 words) and Saab (~330 words) prove short can win — but only on a single unimpeachable shown thing. We have eight or nine strong things; a 500-word note would waste them.
- Both stated judging axes are reachable at this length: "detailed write-ups that others can reference and learn from" (the block ledger + TOOLCHAIN.md link) and "trickier solves that took the solution further in some dimension" (formal miter, Hardcaml rewrite, Tiny Tapeout, Morse decode — four dimensions, each ≤300 words).
- Genre gap noted in the research: this is RE, not design, so the document must carry a thing none of the seven needed — **a confirmed/inferred confidence ledger**. Budget ~150 words of table for it and it replaces ~600 words of hedging prose.

Register targets (from the cross-cutting findings): first-person singular; exact numbers, scarce adjectives; wit only in asides; zero throat-clearing about why the project matters; limitations at point of first claim, never in a closing apology; praise/credentials at the bottom if at all.

---

## 2. Section-by-section outline

Word budgets are advisory; the sum is ~3,400.

---

### §A — Title + hero + thesis (≈120 w)

- **Heading:** none (title block). Title should name the answer object, not the activity.
- **Claim to land:** the chip is an 11×11 two-star Star Battle checker, it accepts exactly one grid, and the recovered model was proved equivalent to the silicon — all before any process is narrated.
- **Facts/numbers:** 728 logic cells; 92 flops; 121 serial input bits; 22 stars; 11 regions; exactly one accepted grid; payload `(* TWO STARS *)`; die 200 × 352.7 µm.
- **Figure:** `figures/puzzle.svg` (region map + 22 stars). Earns its place because it *is* the answer — the reader sees the recovered semantics in one glance, the same function as Gajdusek's video of the working board.
- **JS quote to engage:** "The GDS is, in a very real sense, the chip. Everything the circuit does is in there. The tricky part: nothing is labeled!" — engage only if the reply is immediate (see §C); otherwise save it.
- **Must NOT:** open with the journey, the fabrication crash-course, or why reverse engineering is interesting. No "when Jane Street posted…".

---

### §B — Summary table + confidence ledger (≈220 w, mostly table)

- **Heading:** something flat, e.g. "What the chip is".
- **Claim to land:** every headline claim in this document is already visible here, each marked by how it was established.
- **Facts/numbers (as table rows):** 121 bits in on `I` under `enable`; `success` asserts **one cycle after** the last bit; 92 flops = 84 `dfrtp` / 4 `dfxtp` / 4 `dfstp`; 11 regions summing to 121 cells; 22 stars; two stars per row/column/region; 4-connected adjacency; message 15 bytes on `O[7:0]`; 741 nets; 5,094 pin sites.
- **The ledger column is the point** (this is the RE-specific addition the design writeups didn't need). Three values only: **confirmed by miter** / **confirmed by experiment** / **inferred from structure**. Assign at minimum: semantics = miter; region map = experiment (one-hot probe); block boundaries = inferred from cone membership, tested against their hint; 22-star counter's *necessity* = experiment (corrupt-it-mid-run).
- **Figure:** none. The table is the figure.
- **JS quote:** none here.
- **Must NOT:** put a caveat in prose that could have been a cell in this table. Jhaveri's move is asterisks *in row one*, not a "limitations" section.

---

### §C — Run it yourself (≈90 w)

- **Heading:** "Reproduce" or similar.
- **Claim to land:** everything below is re-derivable from `puzzle.gds` alone, and here is the exact entry point.
- **Facts:** link `TOOLCHAIN.md`; the venv + `klayout gdstk numpy python-sat` line; `icarus-verilog`, `yosys`; note the Hardcaml path needs opam. State the honest friction the reader will hit (Skarman's credibility device): which steps are slow, that `netlist_check.py` prints `RESULT: PROBLEMS FOUND` by design of what it checks (forward-reference to §L), that the PDK must be fetched via `tools/fetch_pdk.sh`.
- **Figure:** none.
- **Must NOT:** become an install tutorial. Three commands maximum in-line, everything else behind the link.

---

### §D — Getting a netlist out was easy, and that matters (≈260 w)

- **Heading:** should say "easy" out loud.
- **Claim to land:** the shipped GDS retained standard-cell master names, pin labels (`li1` 67/5) and top-level port labels (`met3` 70/5), so KLayout `LayoutToNetlist` over the interconnect stack alone recovers the gate netlist — **no geometric cell recognition was needed**, and pretending otherwise would be the easiest lie in this document.
- **Facts/numbers:** 728 logic cells + 890 inert (fill/tap/decap — one clause, not a paragraph); the control experiment: same command on `warmup/04_final.gds` reproduces the shipped ground-truth netlist's cell histogram exactly.
- **Figure:** optional — a cropped `layout.png` region *only if* it shows a labelled pin; otherwise none.
- **JS quote to engage:** "nothing is labeled!" — the honest reply is that in this GDS the *cells* were labelled; what is unlabelled is the **meaning**, and that is where the rest of the document goes. This is the single best quote-engagement in the piece; spend one sentence on it and move.
- **Must NOT:** manufacture difficulty, and equally must not sneer at the puzzle for it. Anti-heroic register (Gajdusek: "There is no heroic tale of debugging…").

---

### §E — Two extractions, one partition; and 66 cell models checked (≈300 w)

- **Claim to land:** the netlist is not a single tool's opinion — two code-disjoint extractors agree exactly, and every cell's behaviour was checked against the PDK rather than assumed.
- **Facts/numbers:** `extract.py` (KLayout connectivity engine) vs `extract2.py` (gdstk + exact polygon booleans + own union-find); **5,095 pin sites found, 5,094 resolved and probed in both, 0 unresolved; 741 nets each; `PARTITIONS ARE IDENTICAL`**. 66 cell models: 63 combinational verified over **every** input vector, 3 sequential.
- **Raw output to paste:** the `compare_extractions.py` tail (`mine=741 klayout=741`, `PARTITIONS ARE IDENTICAL`) and one line of `check_cells.py`. Paste, do not paraphrase — the machine's voice is the proof.
- **Figure:** none.
- **JS quote:** optionally Minsky's "agents benefit a ton from universal guarantees, the ∀" — but better saved for §I. Skip here.
- **Must NOT:** describe how union-find works. Point at the file.

---

### §F — What the machine actually does (≈480 w — the longest section)

- **Heading:** should name the mechanism, e.g. "A one-pass streaming verifier".
- **Claim to land:** the chip never stores the grid; it decides an 11×11 two-star Star Battle in one streaming pass with 92 flops, and the three tricks that make that possible are the whole design.
- **Facts/numbers, in this order (each is a separate beat):**
  1. **92 flops for 121 bits** — the arithmetic that forces the conclusion; state it as the observation that started the reading.
  2. **12-deep history window** supplies the three neighbours in the row above; **only 4 of 8 neighbours are ever checked**, because the other four check themselves when their own cell arrives. Name this as the elegant part.
  3. **2-bit saturating tallies** — to decide "exactly two" you never count past three. Per-row, per-column, per-region accumulators.
  4. Block cell counts as evidence of proportion: column accumulators 59 cells, region accumulators 206 cells, adjacency check **7 cells**, input delay line 12, row counter 9, cell counter 5, success latch 32.
- **Figure:** an **ASCII/waveterm waveform** of ~15 cycles around a violating star pair, generated from `solution.vcd` / `export_trace.py`. This figure does not exist yet and is worth making: ASCII waveforms embedded as text are Jane Street's own signature evidence form (Andrew Ray's expect-test post), and it is the only medium that shows the window sliding.
- **JS quote to engage:** "You had to actually think about what the net was doing." (NN puzzle) — this section is the document's answer to that sentence. Use it here or nowhere.
- **Must NOT:** explain the rules of Star Battle for more than two sentences, and must not present this as if it were obvious on first read. If the ordering of discovery matters, one clause is enough.

---

### §G — The region map, by one-hot probing (≈190 w)

- **Claim to land:** the hard-wired region map was not read off the layout by eye; it was measured, by feeding a single star at each of the 121 cells and recording which accumulator moved.
- **Facts/numbers:** 121 probes → 11 regions summing to 121; 4-connected contiguity **True**; independent Star Battle solver finds **exactly 1** solution (search capped at 5) and it **matches the grid the chip accepts**.
- **Figure:** `figures/puzzle.svg` if not already spent in §A — otherwise reference back. Prefer spending it here if §A uses a die photo instead.
- **Must NOT:** claim the map was "obvious from the layout". The probe is what makes this confirmed rather than inferred.

---

### §H — The accepted grid (≈180 w)

- **Claim to land:** the solve fell out of the recovered netlist mechanically — unroll to CNF and ask a SAT solver — not from puzzle intuition.
- **Facts/numbers:** 122-cycle unroll, **16,504 vars / 56,074 clauses**; `verify.py solution_bits.txt 40` shows `success=0` right after the last bit and `1` one cycle later; solution is 121 bits with 22 ones (recount stated explicitly).
- **Raw output to paste:** the `verify.py` tail showing the 0→1 transition and the ASCII `(* TWO STARS *)` then zeros.
- **Must NOT:** celebrate. This is the midpoint, not the climax — the document's claim is understanding, and the flag is a byproduct. One sentence of understatement.

---

### §I — From "it accepts my grid" to "success ⟺ Star Battle" (≈300 w)

- **Claim to land:** an accepted grid proves almost nothing; the miter proves the equivalence in both directions over all inputs of the unrolled window, and that is a categorically different claim.
- **Facts/numbers:** `proof.py` — both directions **UNSAT**, 0.0s each, 122-cycle unroll, spec has exactly 1 satisfying grid. `diff_test.py` — **37,382 grids, 0 disagreements, 1 accepted**, with the strata disclosed as data (solution 1; 1-bit 121; 2-bit 7,260; 2-per-row 20,000; uniform 5,000; 22-star 5,000). Disclose the sampling design because the strata are the argument: the near-misses (2-per-row, 22-star) are the ones that could have caught a wrong model.
- **JS quotes to engage (pick one, not both):** Minsky's "Tests aren't enough!" or Patti's "in any non-trivial system, your tests are an approximation at best". This section is the document's alignment with their current editorial position; one quote, one sentence, no flattery.
- **Must NOT:** say "proved for all 2^121 inputs" without the bounded-unroll qualifier attached in the same sentence. See Risks.

---

### §J — The miter that failed at cycle 124 (≈340 w — set-piece #1)

- **Heading:** should not be cute. Name the cycle.
- **Claim to land:** every simulation against the known-good stimulus passed, and the reconstruction was still wrong; the miter found it at exactly cycle 124 and handed back the puzzle's own solution grid as the counterexample.
- **Facts/numbers:** silicon registers the verdict **one cycle after** the last bit; the RTL asserted it combinationally. The counterexample was the solution grid — i.e. the one stimulus that had been tested most. Tie to their own puzzle instruction: "Don't forget to toggle `rst_n` before each input attempt" — the same one-cycle protocol subtlety, from the other side.
- **Raw output to paste:** the yosys counterexample header / the failing timestep line, verbatim.
- **Figure:** none — the cycle number and the counterexample identity are the whole image.
- **Must NOT:** frame this as a confession or an apology, and must not moralize about verification for more than one clause. It is evidence for a claim already made in §I. The research is unambiguous: failures narrated as mechanism.

---

### §K — The output generator: the message is not in the layout (≈340 w — set-piece #2)

- **Claim to land:** `O = permute(LFSR) XOR mask(index)`; the mask bytes sitting in the gates are `4d ad fb 83 13 79 1c b5 79 63 c7 68 93 f5` — not text — and the plaintext exists only once the LFSR runs from its reset seed.
- **Facts/numbers:** 4-bit saturating index counter built from the 4 un-reset `dfxtp` flops (say why un-reset matters); 8-bit LFSR; verification that the decode is right, not just consistent: **single-bit flips are XOR-linear at every index**, and **randomising either the LFSR or the index destroys the message**. 208 cells in this block, 12 flops.
- **JS quotes to engage (this section has two earned ones):** "There is one section of the design that is used to generate the output but does not affect the success output. You can safely ignore it…" — we didn't; and "You'll need to come up with a way to simulate the underlying circuit to test your solution and get the final output!" — this section explains *why* that instruction had to be there. That mechanism-level explanation of the puzzle-setter's own constraint is the highest-value paragraph in the document for a judge reading it.
- **Must NOT:** present the mask bytes as a hex dump without saying what the reader is looking at, and must not claim the LFSR structure was inferred when it was decoded and tested.

---

### §L — The die, and using their hint as a test (≈260 w)

- **Claim to land:** every gate was assigned to a block by cone membership and placed by probing the net at its output pin; the blocks turn out to be tight physical clusters; and their hint image was held out and used as a **falsifiable test** of an independently derived floorplan, not as an input to it.
- **Facts/numbers:** their hint image boxes an "output generator" region; **203 of 208** cells attributed to that block fall inside the box, **all 12 of its flops** do, and **no flop from any other block does**. Die 200 × 352.7 µm.
- **Figure:** `figures/floorplan.svg` (10 panels). Earns its place because it is the only figure that shows the *inferred* structure sitting on real geometry — and the panel labels double as the block ledger's index.
- **Table:** the **per-block ledger** belongs here, one row per floorplan panel with fixed columns — *block / cells / flops / what it does / how established / confidence*. Rows: cell counter 5, row counter 9, input delay line 12, adjacency check 7, row accumulator 9, column accumulators 59, region accumulators 206, success latch 32, output generator 208, verdict/output shared 22. This is the "reference others can learn from" artifact; a fixed per-unit rubric is what makes a long document random-accessible (Jhaveri/Michon).
- **JS quote to engage:** "The circuit is physically arranged to hint at its functionality, so look closely at the layout!" — engage by reporting the *degree* of correspondence as a number, not as agreement.
- **Must NOT:** overstate the held-out framing. If the hint image had been seen before the floorplan was finalised, say so precisely; the 203/208 number survives either way, the epistemics don't.

---

### §M — Back to hardware (≈300 w)

- **Claim to land:** the model was written out twice, independently, and both were machine-proved against the silicon; then re-synthesized onto a Liberty built from the die itself, where the two reconstructions converge within one cell.
- **Facts/numbers:** Verilog 169 lines, Hardcaml 109 lines; both proved by bounded miter — **145 cycles under the operating protocol, 122 with every input free**; Verilog run: 3,100,406 vars / 8,531,120 clauses, 145 time steps, 27.5 s; Hardcaml run: 1,831,366 vars / 4,842,030 clauses. Liberty: cell *functions* from the PDK, cell **areas measured off `puzzle.gds`**. Area comparison: die **728 cells / 10,758 µm²** vs Verilog **451 / 6,816** vs Hardcaml **450 / 6,379**. Tiny Tapeout: packaged and tested, `uio_oe = 00000001`, `success = 1`, message 15 bytes, `$finish at 1446000`; **43% of a 1×1 tile**.
- **Raw output to paste:** `SAT proof finished - no model found: SUCCESS!` then `HARDCAML_PROVED` — verbatim, both lines.
- **The Hardcaml choice needs exactly one sentence of motive:** the payload `(* TWO STARS *)` is an OCaml comment; writing the reconstruction in their own HDL closes the joke. Do not explain the joke twice.
- **Figure:** none, or a two-row area table.
- **Must NOT:** say the design "fits" Tiny Tapeout as if OpenLane had confirmed it. Area estimate — the word "estimate" must be in the same sentence as "43%".

---

### §N — Easter eggs (≈220 w)

- **Claim to land:** two hidden messages, both recovered, and one of them was found by re-examining cells previously dismissed as electrically irrelevant.
- **Facts/numbers:** **36 placeholder cells** (`INTERNAL_3` / `INTERNAL_7`, two widths) in one row **below** the cell array spelling **`PER ARENAM AD ASTRA`** in Morse — through the sand to the stars. Their own `example_inputs.vcd` encodes **`The night sky awaits`** as 7-bit ASCII, one character per grid row, LSB in column 0 (report the two trailing spaces as observed — it's the kind of exactness the genre rewards). `$version` = "Leave no stone unturned!"; `$date` is a real leap second.
- **The honest beat:** those 36 cells had been dismissed earlier as electrically irrelevant. Say so — it converts a flex into a debugging-honesty datum, which is the axis they explicitly praised.
- **Figure:** `figures/morse.svg` (36 cells to scale + decode). Earns its place because the claim is *geometric*: the reader must see that cell widths encode dots and dashes.
- **JS quote:** "We hid a few fun Easter eggs in the circuit and in the repository… see if you can spot them once you're done" — one clause, reporting completion.
- **Must NOT:** put this before the technical content. Easter eggs are the dessert; a document that leads with them reads as a puzzle-hunt, not an RE writeup.

---

### §O — What didn't close (≈250 w)

- **Claim to land:** the unbounded result is not in hand, and three other claims have stated ceilings — each with a mechanism, not an apology.
- **Facts/numbers, each with its root cause:**
  - **k-induction did not converge** across differently encoded state spaces (one-hot region tally vs binary row tally). The equivalence is therefore **bounded** at the unroll depths in §I/§M, not unbounded.
  - **Fixed-point / quiescence argument failed over unreachable states** (`quiescence.py`).
  - **`$1447`**: one net with no driver, fanning out to `$279` `a31oi_2` pin A1 and `$1781` `a311o_2` pin A1. `netlist_check.py` prints `RESULT: PROBLEMS FOUND` solely on this. State the resolution as experiments: differential test re-run with the net **forced to each value** → 0 disagreements, 1 accepted grid both ways; `proof.py` re-run with `$1447` as a **free SAT variable** → still UNSAT both directions. Also disclose that `sim.py` defaults unknown nets to zero, i.e. the default runs implicitly assumed `$1447 = 0` — that admission is what makes the forced-both-ways experiment meaningful.
  - **Tiny Tapeout 43%** is an area estimate.
  - **Extraction was easy** — restated once, in the limitations ledger, so it can't be read as buried.
- **Also worth one line:** the 22-star total counter is logically redundant given the two-per-row constraints, yet load-bearing in the silicon — corrupt it mid-run and `success` dies. Give the precise sense of "redundant" (implied by other constraints on reachable inputs) so it doesn't read as a contradiction.
- **Must NOT:** hedge. One matter-of-fact sentence per item, with a number or a mechanism attached. No "future work" framing.

---

### §P — Provenance, reproduction pointer, credits (≈150 w)

- **Claim to land:** what ground truth was, where it came from, and that the analysis is the author's own.
- **Content:** ground truth = `puzzle.gds` plus the SkyWater PDK models (`google/skywater-pdk-libs-sky130_fd_sc_hd`) and nothing else; the warm-up's shipped netlist used only as an extraction control; tools named (KLayout, gdstk, yosys, Icarus, python-sat, Hardcaml). This is the slot the seven design writeups fill with independence declarations ("I haven't looked at anyone's attempts", "my own out-of-order RISC-V CPU that I made").
- **Credentialing goes here, at the bottom, if at all** — Michon's Achievements pattern. Never at the top.
- **Must NOT:** end on a pitch, a thank-you to Jane Street, or a meta-comment about how the document was written.

---

## 3. Ordering rationale — why this, not chronological

- **The epistemic inversion.** These are RE claims, not design claims: the reader's question is "is your model true?", not "did it work?". A reader cannot evaluate evidence for a model they haven't been shown. Chronology withholds the model until the end, which converts every evidence section into suspense instead of scrutiny.
- **The featured favourite opens artifact-first.** Gajdusek: win banner, video, three-sentence thesis, *then* process. Jhaveri: results table first, caveats asterisked in row one. Citerin: demo video, then `# Reproduce`. Only the two tutorial pieces are journey-first, and even they promise the destination in paragraph one.
- **Pipeline order is a free outline and it happens to match discovery closely.** GDS → netlist (§D–E) → semantics (§F–G) → solve (§H) → proof (§I–J) → payload (§K) → geometry (§L) → back to hardware (§M). The reader can hold one mental stack.
- **Chronology is preserved exactly where the sequence is the evidence** — §J (all sims passed, then the miter failed at 124) and §K (the decode had to be *tested*, not just made consistent) are told in time order because the order is what makes them arguments. That is Citerin's three-pseudocode-versions device and Tristan's failure-driven chapter structure, applied locally rather than globally.
- **Easy-extraction admission goes early (§D), not into a limitations section.** Deferred, it reads as concealment; up front, it sets the honest baseline that makes everything after it credible, and it tells the reader where the real work is.
- **Easter eggs go late** because they are thoroughness signals, and a signal placed before the substance changes the genre of the document.
- **Limitations sit at §O rather than dispersed** *only because* the per-claim caveats already live in the §B ledger and inline at each claim. §O is the residue that couldn't be tabled (k-induction, quiescence), not the document's first admission of anything.

---

## 4. Cut or compress

| Cut / compress | Reason |
|---|---|
| Any chip-fabrication primer (Verilog → netlist → GDS) | They wrote it, in the puzzle post. Tristan's 40% Clash prelude is explicitly flagged in the research as the thing to drop for an RE audience. |
| Star Battle rules beyond two sentences | Audience is hardware people; the rules are inlined at point of need in §F. |
| Warm-up narration | Keep exactly one clause in §D as an extraction *control*. It has no other role. |
| Tool installation, venv setup, PDK fetching | → `TOOLCHAIN.md`. §C links; it does not teach. |
| How union-find / polygon booleans / CNF unrolling work | The claim is that two methods agreed and a solver returned UNSAT. Mechanism of the solver is not the finding. |
| Per-cell enumeration of the 66 verified models | One sentence with 63/3 split. A list of cell names is dead weight. |
| The 890 inert cells | One clause in §D. Fill/tap/decap is not a finding. |
| Blow-by-blow early exploration (first look at the layout, initial hypotheses that were merely slow rather than wrong) | Dead ends earn trust only when *evidence killed them*. Wandering does not qualify. Keep the two that were falsified: the immediate-assert RTL (§J), and the dismissal of the 36 placeholder cells (§N). |
| Interactive figure pack description | One link. Do not narrate a UI. |
| Resynthesis methodology detail | Keep the three-row area comparison and the "areas measured off the die" clause; cut how the Liberty was assembled. |
| Any motivation/why-this-matters paragraph | Zero throat-clearing is uniform across all seven featured writeups. The artifact justifies itself; motivation gets at most one sentence. |
| Any praise of the puzzle, the company, or the design | Reads as pitching. Their own posts don't do it, and the credentialing slot is the bottom of the page. |
| Any mention of AI tooling, disclaimers, or writing process | Zero AI mentions across all seven featured writeups (verified by grep). The genre's slot for this is the provenance statement in §P. |
| Speculation about the designers' intent | Except in §K, where the mechanism *explains* their stated instruction — that is inference from evidence, not mind-reading. |

---

## 5. Highest-leverage ideas in the document

Four ideas, stated as ideas. Everything else is support.

1. **A verifier that never stores what it verifies.** 92 flops decide a 121-bit constraint problem in one streaming pass, because the design refuses to count past three to decide "exactly two" and refuses to check eight neighbours when four of them will check themselves later. This is the "you had to actually think about what the net was doing" content, and it is the only part of the document that no amount of tooling could have produced.

2. **The counterexample was the one input we had tested most.** Every simulation against the known-good stimulus passed; the miter failed at cycle 124 and returned the puzzle's own solution grid. One cycle of latency, invisible to the test that mattered. This is simultaneously the debugging-honesty datum they explicitly reward and a live instance of their current editorial thesis about verification burden — and it earns that reading without the document ever having to argue for it.

3. **The message does not exist in the layout.** `O = permute(LFSR) XOR mask(index)`, masks are `4d ad fb …`, plaintext only materialises once the LFSR runs from its reset seed. This is the mechanism-level explanation of why their own post had to tell solvers to build a simulator — the document answers a question the puzzle-setters raised, from inside their design.

4. **Their hint was held out and used as a test.** An independently derived floorplan predicted their boxed region: 203/208 cells inside, all 12 of its flops in, no foreign flop. Turning a provided hint into a falsifiable check of your own inference is the one move in this document that is purely epistemic, and it is what separates a recovered netlist from a recovered *understanding*.

Anchoring these: **the extraction was easy and the document says so in §D.** That sentence is what buys the reader's trust for the four claims above, and it costs nothing that was actually earned.

---

## 6. Risks — where the author could overclaim

| Risk | What the honest phrasing must preserve |
|---|---|
| "Proved for all 2^121 inputs" | The proof is a **bounded** miter: 122-cycle unroll with every input free, 145 cycles under the operating protocol. The qualifier belongs in the same sentence as the claim, every time. Nowhere may "all inputs" appear unqualified. |
| "The reconstruction is equivalent to the silicon" | Same bound. Plus: equivalence is against the **extracted** netlist, which is itself a recovered artifact (§E is what backs it). Two links in the chain, both stated. |
| "k-induction didn't converge" glossed over | Must say *why*: differently encoded state spaces (one-hot vs binary tallies), and that the quiescence/fixed-point route failed over unreachable states. A ceiling with a mechanism is a finding; a ceiling without one is a hedge. |
| "The floating net doesn't matter" | Must be stated as the two experiments, not as a judgement: forced to each value → 0 disagreements both ways; free SAT variable → UNSAT both directions. And must disclose that `sim.py` silently defaults unknown nets to zero, so the default runs assumed `$1447 = 0`. |
| Suppressing `netlist_check.py`'s `PROBLEMS FOUND` | Disclose it, in §C and §O, with the exact trigger (`undriven = ['$1447']`, sole cause) and the fact that it is pre-existing at clean commit `76d0fd9`, not a regression. Hiding a script that prints a failure is the one thing that would sink the document if a reader ran the repo. |
| "728 driven nets / 719 / 741" confusion | 741 is nets touching pins (both extractors); 719 is `netlist_check.py`'s narrower count of nets with a driving output pin, excluding the four input ports and power rails. Different metrics, both correct. Pick 741 for the headline and footnote the other if it appears at all. |
| "Fits in a Tiny Tapeout tile" | Area **estimate** from a Liberty with measured areas — not an OpenLane place-and-route result. The word "estimate" in the same sentence as "43%". |
| "We used their hint as a test, not an input" | Only true if the hint image was genuinely not consulted while deriving the floorplan. If it was seen first, the honest version is that the correspondence was *quantified* (203/208, 12/12, 0 foreign flops) rather than that it was held out. The number survives; the epistemic framing must match what actually happened. |
| "The 22-star counter is redundant" | Redundant **given the per-row constraints on reachable inputs**, yet load-bearing in the silicon — corrupting it kills `success`. Both halves in one sentence or it reads as self-contradiction. |
| "Exactly one accepted grid" | Two independent supports: `proof.py` (spec has exactly 1 satisfying grid) and `starbattle_check.py` (1 solution, search capped at 5). Say which; the cap is part of the claim. |
| "No geometric cell recognition needed" | This is a property of the shipped GDS, not a verdict on the puzzle's difficulty. Register must stay flat — Gajdusek's anti-heroic tone, not a shrug at the setters. |
| "The message is an OCaml comment / the Morse means X" | `(* TWO STARS *)` and *per arenam ad astra* are readings. Report the recovered bytes and the decode as facts; keep the interpretation to one clause and let the reader agree. |
| Quote-stuffing Jane Street at themselves | Maximum two or three verbatim quotes in the entire document (recommended: "nothing is labeled!" in §D, the ignore-that-section pointer in §K, and one of Minsky/Patti in §I or §J). Any credentialing or praise-quoting goes at the bottom, per Michon. |
| Mentioning AI anywhere | Their rule bans AI-generated writeups; the genre's own answer is silence plus an independence/provenance statement. §P carries it. Do not disclaim, do not credit, do not defend. |

---

**Assets that exist:** `/Users/jacobcrainic/asic-puzzle-2026/figures/puzzle.svg`, `figures/floorplan.svg`, `figures/morse.svg`, `figures.html` (interactive pack), `layout.png`, `TOOLCHAIN.md`, `solution.vcd`, `example_inputs.vcd`.

**One asset worth creating before writing:** an ASCII waveform excerpt (from `export_trace.py` / `solution.vcd`) covering ~15 cycles around an adjacency violation, for §F — it is the only medium that shows the 12-deep window sliding, and text-embedded waveforms are Jane Street's own house evidence form.