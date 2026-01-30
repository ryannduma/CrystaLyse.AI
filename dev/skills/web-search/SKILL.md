---
name: web-search
description: >
  Search the web for materials science literature and information. Use when:
  (1) finding synthesis conditions or methods, (2) checking if a material has
  been made experimentally, (3) finding reported property values, (4) getting
  references for computed properties, (5) learning about recent developments.
  Do NOT use for numerical property values - use databases or compute instead.
---

# Web Search for Materials Science

Search for literature, synthesis information, and external resources.

## Quick Usage

Use the `web_search` tool:

```python
web_search(
    query="BiVO4 photocatalyst synthesis conditions",
    num_results=5,
    search_type="academic"
)
```

## Search Types

| Type | Description | When to Use |
|------|-------------|-------------|
| `general` | Broad web search | General information |
| `academic` | Focus on arxiv, journals | Finding papers, methods |
| `databases` | Focus on materials databases | When OPTIMADE isn't enough |

## When to Use Web Search

### Synthesis Information

```python
# Find how to make a material
web_search(
    query="Sr2TiO4 solid-state synthesis temperature",
    search_type="academic"
)
# → Learn: "Typically synthesized at 1300-1400°C"
```

### Experimental Validation

```python
# Check if predicted material has been made
web_search(
    query="Bi2SbSe4 experimental synthesis crystal structure",
    search_type="academic"
)
# → Confirms experimental existence (or lack thereof)
```

### Literature Grounding

```python
# Find references for a computed property
web_search(
    query="BiVO4 band gap experimental measurement",
    search_type="academic"
)
# → "Reported band gap: 2.4-2.5 eV (Kudo et al., 2006)"
```

### Understanding Failures

```python
# Why might a synthesis fail?
web_search(
    query="LiNiO2 synthesis challenges side reactions",
    search_type="academic"
)
# → Learns about Li/Ni disorder, oxygen loss, etc.
```

## When NOT to Use Web Search

| Situation | Problem | Better Alternative |
|-----------|---------|-------------------|
| "What's the band gap of TiO2?" | Web data has no provenance | Query MP or compute |
| "Get the structure of NaCl" | Need actual CIF file | Use OPTIMADE or MP |
| "Is LiFePO4 stable?" | Need thermodynamic calculation | Use hull distance |
| Numerical property values | Can be outdated/wrong | Always compute or use database |

## Critical Rules

### NEVER Trust Web-Sourced Numbers

**Bad**: "Web search says band gap is 1.5 eV, reporting that."

**Good**: "Literature reports band gap of 1.5 eV (Zhang et al., 2020). For provenance, I will compute with MACE or query Materials Project."

### Always Cite Sources

**Bad**: "This material has been synthesized."

**Good**: "This material was synthesized by Liu et al. (J. Mater. Chem., 2019) using solid-state reaction at 1200°C."

### Flag Uncertainty

When using web information, always add caveats:
- "According to literature..."
- "This should be validated experimentally..."
- "Reported values range from X to Y..."

## Workflow Examples

### Workflow 1: Literature-Backed Recommendation

```
1. SMACT validates composition ✓
2. Chemeleon predicts structure ✓
3. MACE calculates energy ✓
4. Web search: "Has [formula] been made?"
   → If yes: Cite paper, compare to prediction
   → If no: Note as "computationally predicted, not yet synthesized"
5. Report with full provenance chain
```

### Workflow 2: Synthesis Planning

```
1. User asks: "How do I synthesize Sr2TiO4?"
2. Web search: "Sr2TiO4 synthesis method temperature"
3. Extract: Precursors, temperatures, atmospheres
4. Cross-check with multiple sources
5. Provide synthesis protocol with citations
```

### Workflow 3: Property Comparison

```
1. Compute band gap with MACE: 1.8 eV
2. Web search: "[formula] band gap experimental"
3. Find: "Reported as 2.1 eV (Smith, 2018)"
4. Report both:
   - Computed: 1.8 eV (MACE)
   - Experimental: 2.1 eV (Smith, 2018)
   - Note: "0.3 eV discrepancy typical for DFT underestimation"
```

## Provenance for Web Results

When reporting web-sourced information, include:

1. **Source**: Author, publication, year
2. **URL**: Where it was found (if available)
3. **Quote**: Exact text if numerical
4. **Caveat**: Why this should be verified

Example:
```
Synthesis conditions from literature:
- Temperature: 1300°C (Liu et al., J. Am. Chem. Soc., 2019)
- Atmosphere: Air
- Precursors: SrCO3 + TiO2
- URL: https://pubs.acs.org/doi/...

Note: These conditions should be optimized for specific equipment.
```

## Error Handling

| Result | Interpretation | Action |
|--------|---------------|--------|
| No results | Rare/novel topic | Try broader terms |
| Conflicting info | Normal in science | Report range, cite multiple |
| Old papers only | May be outdated | Note date, seek recent work |
| Non-peer-reviewed | Lower reliability | Flag as preprint/blog |

## Tips for Effective Searching

1. **Be specific**: "BiVO4 water splitting overpotential" not "BiVO4 properties"
2. **Include synthesis**: Add "synthesis" or "preparation" for making materials
3. **Add "experimental"**: Distinguishes from computational studies
4. **Use chemical formulas**: More precise than common names
5. **Specify property**: "band gap" not "electronic properties"

## For Workers

If you're a worker subagent executing this skill:

1. Follow the task instructions from the lead agent (search queries, focus areas)
2. Write full search results to artifact path if specified
3. Return a summary with: paper count, key findings with citations (author, year, DOI)
4. Report confidence level (peer-reviewed vs preprint vs blog)
5. Flag if no results found or results are conflicting
