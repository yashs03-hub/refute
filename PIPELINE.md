# The validation pipeline

Two loops and a gate. The resolve loop is re-entrant — advice generates new
grounding questions, so it is not a preamble. The gate and the terminal refusal
are the honest parts: a pipeline with no box for *"do not run this"* cannot emit
the finding that matters most.

<svg viewBox="0 0 920 740" xmlns="http://www.w3.org/2000/svg" style="max-width:100%;height:auto;color:inherit" role="img" aria-label="Validation pipeline: sources feed a re-entrant resolve loop, which emits an abridged review and calibrates the twin; a design is parsed or extracted into a DesignSpec, routed by an assay gate to tier 1, tier 0, out-of-scope or refusal, then simulated and advised, terminating either in a revision that re-enters the resolve loop or in a verdict that the question is not answerable at this scale">
  <defs>
    <marker id="pl1" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="currentColor" opacity="0.6"/></marker>
    <marker id="pl2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#4a9eb5"/></marker>
  </defs>

  <text x="24" y="24" font-size="12" fill="currentColor" opacity="0.65">Accent = the loops and the outputs. Dashed = a stop, not a failure.</text>

  <!-- sources -->
  <rect x="300" y="44" width="360" height="58" rx="4" fill="none" stroke="currentColor" opacity="0.35"/>
  <text x="316" y="68" font-size="13" font-weight="500" fill="currentColor">Sources — one protocol, four methods</text>
  <text x="316" y="88" font-size="10" fill="currentColor" opacity="0.65">literature · public datasets · own ELN / prior runs · robot logs</text>

  <!-- inputs -->
  <rect x="24" y="136" width="152" height="44" rx="4" fill="none" stroke="currentColor" opacity="0.35"/>
  <text x="36" y="163" font-size="13" font-weight="500" fill="currentColor">hypothesis</text>
  <rect x="24" y="192" width="152" height="58" rx="4" fill="none" stroke="currentColor" opacity="0.35"/>
  <text x="36" y="216" font-size="13" font-weight="500" fill="currentColor">design</text>
  <text x="36" y="236" font-size="10" fill="currentColor" opacity="0.65">prose · script · log</text>

  <!-- resolve loop -->
  <rect x="300" y="130" width="360" height="136" rx="4" fill="none" stroke="#4a9eb5" stroke-width="2"/>
  <text x="316" y="155" font-size="13" font-weight="500" fill="#4a9eb5">RESOLVE LOOP</text>
  <text x="316" y="180" font-size="11" fill="#4a9eb5">what quantities does this verdict depend on?</text>
  <text x="316" y="202" font-size="11" fill="#4a9eb5">resolved  →  Evidence</text>
  <text x="316" y="222" font-size="11" fill="#4a9eb5">not       →  Blocked (typed reason)</text>
  <text x="316" y="248" font-size="10" fill="#4a9eb5" opacity="0.8">loop until every one is one or the other</text>

  <!-- right-hand outputs -->
  <rect x="700" y="130" width="180" height="56" rx="4" fill="none" stroke="#4a9eb5" stroke-dasharray="4 4"/>
  <text x="714" y="155" font-size="12" font-weight="500" fill="#4a9eb5">Abridged review</text>
  <text x="714" y="174" font-size="10" fill="#4a9eb5">decision-scoped, not a summary</text>
  <rect x="700" y="200" width="180" height="56" rx="4" fill="none" stroke="#4a9eb5" stroke-dasharray="4 4"/>
  <text x="714" y="225" font-size="12" font-weight="500" fill="#4a9eb5">Calibrates the twin</text>
  <text x="714" y="244" font-size="10" fill="#4a9eb5">constants, with provenance</text>

  <!-- parse/extract -->
  <rect x="24" y="300" width="152" height="58" rx="4" fill="none" stroke="currentColor" opacity="0.35"/>
  <text x="36" y="324" font-size="12" font-weight="500" fill="currentColor">PARSE | EXTRACT</text>
  <text x="36" y="344" font-size="10" fill="currentColor" opacity="0.65">lossless · model call</text>

  <!-- designspec -->
  <rect x="300" y="306" width="170" height="46" rx="4" fill="none" stroke="currentColor" opacity="0.35"/>
  <text x="314" y="334" font-size="13" font-weight="500" fill="currentColor">DesignSpec</text>

  <!-- gate -->
  <rect x="370" y="390" width="180" height="44" rx="4" fill="none" stroke="currentColor" opacity="0.35"/>
  <text x="386" y="418" font-size="13" font-weight="500" fill="currentColor">ASSAY GATE</text>

  <!-- four branches -->
  <rect x="30" y="468" width="200" height="60" rx="4" fill="none" stroke="currentColor" opacity="0.35"/>
  <text x="44" y="494" font-size="12" font-weight="500" fill="currentColor">tier 1</text>
  <text x="44" y="513" font-size="10" fill="currentColor" opacity="0.65">mechanistic twin</text>
  <rect x="240" y="468" width="200" height="60" rx="4" fill="none" stroke="currentColor" opacity="0.35"/>
  <text x="254" y="494" font-size="12" font-weight="500" fill="currentColor">tier 0</text>
  <text x="254" y="513" font-size="10" fill="currentColor" opacity="0.65">power arithmetic</text>
  <rect x="450" y="468" width="200" height="60" rx="4" fill="none" stroke="currentColor" opacity="0.35" stroke-dasharray="4 4"/>
  <text x="464" y="494" font-size="12" font-weight="500" fill="currentColor" opacity="0.75">out of scope</text>
  <text x="464" y="513" font-size="10" fill="currentColor" opacity="0.65">twin cannot model it</text>
  <rect x="660" y="468" width="200" height="60" rx="4" fill="none" stroke="currentColor" opacity="0.35" stroke-dasharray="4 4"/>
  <text x="674" y="494" font-size="12" font-weight="500" fill="currentColor" opacity="0.75">refuse</text>
  <text x="674" y="513" font-size="10" fill="currentColor" opacity="0.65">nothing to stand on</text>

  <!-- simulate / advise -->
  <rect x="170" y="566" width="170" height="44" rx="4" fill="none" stroke="currentColor" opacity="0.35"/>
  <text x="186" y="594" font-size="13" font-weight="500" fill="currentColor">SIMULATE</text>
  <rect x="380" y="566" width="170" height="44" rx="4" fill="none" stroke="currentColor" opacity="0.35"/>
  <text x="396" y="594" font-size="13" font-weight="500" fill="currentColor">ADVISE</text>

  <!-- outcomes -->
  <rect x="60" y="644" width="320" height="58" rx="4" fill="none" stroke="#4a9eb5" stroke-width="2"/>
  <text x="76" y="670" font-size="13" font-weight="500" fill="#4a9eb5">⛔ Not answerable at this scale</text>
  <text x="76" y="690" font-size="10" fill="#4a9eb5">the most valuable output</text>
  <rect x="430" y="644" width="190" height="58" rx="4" fill="none" stroke="currentColor" opacity="0.35"/>
  <text x="444" y="670" font-size="13" font-weight="500" fill="currentColor">revise</text>
  <text x="444" y="690" font-size="10" fill="currentColor" opacity="0.65">new levers, new questions</text>

  <!-- plain edges -->
  <g stroke="currentColor" opacity="0.6" stroke-width="1.4" fill="none">
    <path d="M 480 102 L 480 122" marker-end="url(#pl1)"/>
    <path d="M 176 158 L 292 172" marker-end="url(#pl1)"/>
    <path d="M 176 221 L 292 206" marker-end="url(#pl1)"/>
    <path d="M 100 250 L 100 292" marker-end="url(#pl1)"/>
    <path d="M 176 329 L 292 329" marker-end="url(#pl1)"/>
    <path d="M 420 352 L 420 382" marker-end="url(#pl1)"/>
    <path d="M 460 434 L 460 452"/>
    <path d="M 130 452 L 760 452"/>
    <path d="M 130 452 L 130 460" marker-end="url(#pl1)"/>
    <path d="M 340 452 L 340 460" marker-end="url(#pl1)"/>
    <path d="M 550 452 L 550 460" marker-end="url(#pl1)"/>
    <path d="M 760 452 L 760 460" marker-end="url(#pl1)"/>
    <path d="M 130 528 L 130 548"/>
    <path d="M 340 528 L 340 548"/>
    <path d="M 130 548 L 340 548"/>
    <path d="M 255 548 L 255 558" marker-end="url(#pl1)"/>
    <path d="M 340 588 L 372 588" marker-end="url(#pl1)"/>
    <path d="M 465 610 L 465 626"/>
    <path d="M 220 626 L 525 626"/>
    <path d="M 525 626 L 525 636" marker-end="url(#pl1)"/>
  </g>

  <!-- accent edges -->
  <g stroke="#4a9eb5" stroke-width="1.7" fill="none">
    <path d="M 660 158 L 692 158" marker-end="url(#pl2)"/>
    <path d="M 660 228 L 692 228" marker-end="url(#pl2)"/>
    <path d="M 790 256 L 790 368 L 466 368 L 466 382" marker-end="url(#pl2)"/>
    <path d="M 220 626 L 220 636" marker-end="url(#pl2)"/>
    <path d="M 620 673 L 890 673 L 890 286 L 480 286 L 480 274" marker-end="url(#pl2)"/>
  </g>
  <text x="560" y="279" font-size="10" fill="#4a9eb5">revision re-enters the loop</text>
</svg>

## What the drawing is asserting

**The resolve loop is re-entrant.** `ADVISE` output — add an antifibrinolytic,
move the endpoint earlier — raises grounding questions that were not askable
before the simulation ran. So revision returns into the loop rather than around
it.

**Sources are one interface.** Literature, public datasets, an ELN, a robot's
execution log: four backends behind one protocol, differing only in provenance
tier. A robot log is the strongest of them, because it has no publication
filter — every unit that failed is in it.

**`PARSE` and `EXTRACT` are not the same confidence.** A protocol script is a
`DesignSpec` losslessly; prose needs a model call and must be held constant
across comparisons. The pipeline should report which path it took.

**The gate has four exits and two of them are stops.** Out-of-scope is a limit
of the twin, not a verdict on the design. Refusal is what happens with no
calibrated model *and* no variance estimate to fall back on.

**The terminal box is the point.** A loop with no exit polishes a design that
should be abandoned. "Not answerable at this scale" is the finding, not a
failure to produce one.
