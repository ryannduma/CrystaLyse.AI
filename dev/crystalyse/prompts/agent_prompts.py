"""
Prompts for autonomous agents with true decision-making capabilities.

These prompts guide the agents to exhibit genuine autonomy while maintaining
scientific rigor and transparency.
"""

import json
from typing import Any


class AgentPrompts:
    """Collection of prompts for autonomous agent behavior"""

    def get_understanding_prompt(self, query: str, domain_context: dict[str, Any]) -> str:
        """Generate prompt for understanding user query"""
        return f"""
Analyze this materials science query deeply to understand the user's true intent:

Query: "{query}"

Domain Context:
{json.dumps(domain_context, indent=2)}

Provide a comprehensive analysis including:
1. What the user is literally asking for
2. What they might actually need (reading between the lines)
3. Any ambiguities or missing information
4. Implicit constraints or requirements
5. Whether clarification would significantly improve results

Return as JSON with structure:
{{
    "literal_request": "what they asked for",
    "interpreted_need": "what they likely need",
    "ambiguities": ["list of unclear points"],
    "implicit_constraints": ["inferred requirements"],
    "needs_clarification": true/false,
    "clarification_topics": ["topics needing clarification"]
}}

Remember: Users often don't know exactly what to ask. Use your materials science expertise to identify what would truly help them.
"""

    def get_clarification_prompt(
        self, query: str, understanding: dict[str, Any], domain_context: dict[str, Any]
    ) -> str:
        """Generate prompt for creating clarification questions"""
        return f"""
Based on this query analysis, generate 2-4 clarifying questions that would significantly improve the results.

Original Query: "{query}"

Understanding:
{json.dumps(understanding, indent=2)}

Domain Context:
{json.dumps(domain_context, indent=2)}

Create questions that:
1. Are specific to materials science (not generic)
2. Would meaningfully narrow the search space
3. Help avoid wasted computation
4. Are easy for the user to answer

Return as JSON:
{{
    "questions": [
        {{
            "id": "unique_id",
            "question": "Clear question text",
            "options": ["Option 1", "Option 2", ...] or null for free text,
            "why": "Brief explanation of why this matters",
            "impact": "How this affects the search"
        }}
    ]
}}

Focus on questions that distinguish between fundamentally different approaches or requirements.
"""

    def get_planning_prompt(
        self,
        query: str,
        clarifications: dict[str, str],
        constraints: dict[str, Any],
        available_tools: list[dict[str, Any]],
    ) -> str:
        """Generate prompt for strategic planning"""
        return f"""
Create an adaptive strategy for this materials discovery task.

Query: "{query}"

Clarifications provided:
{json.dumps(clarifications, indent=2)}

Constraints:
{json.dumps(constraints, indent=2)}

Available tools:
{json.dumps(available_tools, indent=2)}

Design a strategy that:
1. Can adapt based on intermediate results
2. Prioritizes most promising approaches
3. Has fallback options if primary approach fails
4. Balances exploration vs exploitation

Return as JSON:
{{
    "description": "High-level strategy description",
    "primary_approach": {{
        "method": "Main approach",
        "steps": ["Step 1", "Step 2", ...],
        "success_criteria": "What indicates success"
    }},
    "adaptation_triggers": [
        {{
            "condition": "When to adapt",
            "action": "How to adapt"
        }}
    ],
    "fallback_approaches": [
        {{
            "trigger": "When to use",
            "method": "Alternative approach"
        }}
    ],
    "estimated_iterations": 3,
    "confidence": 0.8
}}

Think like an expert materials scientist planning an experimental campaign.
"""

    def get_decision_prompt(
        self,
        context: Any,  # AgentContext
        strategy: dict[str, Any],
        current_results: dict[str, Any],
        available_actions: list[str],
    ) -> str:
        """Generate prompt for next action decision"""

        # Extract relevant context
        query = context.query
        iteration = context.iteration_count
        failed = context.failed_approaches

        return f"""
Decide the next action in this materials discovery workflow.

Current situation:
- Query: "{query}"
- Iteration: {iteration}
- Strategy: {strategy["description"]}
- Failed approaches: {failed}

Results so far:
{json.dumps(current_results, indent=2)}

Available actions:
{json.dumps(available_actions, indent=2)}

Consider:
1. What have we learned from results so far?
2. Are we making progress toward the goal?
3. Should we continue current approach or pivot?
4. What's the most informative next action?

Return as JSON:
{{
    "action": "chosen_action",
    "confidence": "high/medium/low/uncertain",
    "reasoning": "Detailed explanation of why this action",
    "parameters": {{
        "param1": "value1"
    }},
    "requires_approval": false,
    "alternatives": ["backup_action_1", "backup_action_2"],
    "expected_outcome": "What we hope to learn"
}}

Be genuinely autonomous - make decisions based on scientific reasoning, not predetermined paths.
"""

    def get_adaptation_prompt(
        self,
        context: Any,  # AgentContext
        current_strategy: dict[str, Any],
        results: dict[str, Any],
        failed_approaches: list[str],
    ) -> str:
        """Generate prompt for strategy adaptation"""
        return f"""
The current strategy may need adaptation based on results.

Original strategy: {current_strategy["description"]}

Results obtained:
{json.dumps(results, indent=2)}

Failed approaches:
{failed_approaches}

Analyze whether and how to adapt:
1. Is the current strategy still viable?
2. What have we learned that changes our approach?
3. Are there new opportunities revealed by the results?
4. Should we pivot completely or adjust slightly?

Return as JSON:
{{
    "needs_adaptation": true/false,
    "reason": "Why adaptation is needed",
    "new_strategy": {{
        "description": "Updated strategy",
        "changes": ["What's different"],
        "rationale": "Why these changes"
    }},
    "abandoned_paths": ["Approaches we're giving up on"],
    "new_opportunities": ["Newly discovered possibilities"]
}}

Think like a scientist adjusting their experimental plan based on preliminary results.
"""

    def get_validation_prompt(self, results: dict[str, Any]) -> str:
        """Generate prompt for result validation"""
        return f"""
Validate these computational results for scientific integrity.

Results:
{json.dumps(results, indent=2)}

Check for:
1. Physical reasonableness (do values make sense?)
2. Internal consistency (do related values agree?)
3. Computational backing (are all numbers from actual calculations?)
4. Uncertainty quantification (do we know error bars?)

For each result, assess:
- Is this from actual tool output or estimation?
- Are the values in reasonable ranges?
- Are there any red flags or anomalies?
- What's our confidence in this result?

Return validation assessment with specific concerns highlighted.
"""

    def get_synthesis_prompt(
        self, query: str, context: dict[str, Any], validated_results: dict[str, Any]
    ) -> str:
        """Generate prompt for final synthesis"""
        return f"""
Synthesize a comprehensive report for this materials discovery task.

Original query: "{query}"

Context:
{json.dumps(context, indent=2)}

Validated results:
{json.dumps(validated_results, indent=2)}

Create a report that:
1. Directly addresses the user's query
2. Highlights key findings with confidence levels
3. Acknowledges limitations and uncertainties
4. Provides actionable recommendations
5. Suggests logical next steps

Structure the report for clarity and usefulness, remembering that the user may not be a materials expert.

Include:
- Executive summary (2-3 sentences)
- Main findings with context
- Technical details where relevant
- Practical recommendations
- Future research directions

Be honest about what we found, what we didn't find, and what we're uncertain about.
"""

    def get_failure_recovery_prompt(self, context: Any, error: str) -> str:
        """Generate prompt for handling failures gracefully"""
        return f"""
A failure occurred during materials discovery. Help the user understand and recover.

Query: "{context.query}"
Error: "{error}"
Partial results: {json.dumps(context.results, indent=2)}

Provide:
1. User-friendly explanation of what went wrong
2. What results (if any) are still valid
3. Suggested modifications to the query
4. Alternative approaches that might work

Remember: Failures are learning opportunities. Help the user understand the constraints and guide them toward a successful search.
"""

    def get_domain_expertise_prompt(self, topic: str) -> str:
        """Generate prompt for domain-specific reasoning"""
        return f"""
Apply deep materials science expertise to this topic: {topic}

Consider:
1. Fundamental physical/chemical principles
2. Known structure-property relationships
3. Synthesis-structure correlations
4. Practical/engineering constraints
5. Recent advances in the field

Provide insights that go beyond basic database queries - think like an expert materials scientist with years of experience.
"""

    def get_creativity_prompt(self, context: dict[str, Any]) -> str:
        """Generate prompt for creative/exploratory mode"""
        return f"""
Engage creative materials discovery mode for: {context}

Think beyond conventional approaches:
1. What non-obvious combinations might work?
2. Can we apply principles from other fields?
3. What if we relax typical constraints?
4. Are there unexplored corners of chemical space?

Balance creativity with scientific plausibility. Propose novel ideas that are ambitious but not impossible.
"""

    def get_rigorous_prompt(self, context: dict[str, Any]) -> str:
        """Generate prompt for rigorous validation mode"""
        return f"""
Apply rigorous scientific validation to: {context}

Ensure:
1. Every claim is computationally backed
2. All assumptions are stated explicitly
3. Uncertainties are quantified
4. Multiple validation methods used where possible
5. Results are reproducible

Be skeptical of all results. It's better to reject a potentially good material than to propose a bad one with high confidence.
"""
