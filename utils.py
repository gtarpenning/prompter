from enum import Enum
from pydantic import BaseModel
import weave
from typing import Optional
from exp import (
    OptimizedPrompt,
    OutputScore,
    PromptComparison,
    analyze_prompt,
    optimize_prompt,
    compare_outputs,
    score_outputs,
    PromptAnalysis,
    PromptPair,
)


class AnalysisData(BaseModel):
    original_system_prompt: Optional[str]
    optimized_system_prompt: Optional[str]
    user_prompt: str
    program_key: str
    program_inputs: list[str]
    hallucination_risk: str
    hallucination_targets: list[str]
    program_improvement_ideas: list[str]
    comparison_notes: list[str]
    winner: str
    original_score: int
    optimized_score: int
    original_output: str
    optimized_output: str

    def to_dict(self) -> dict:
        """Convert the AnalysisData model to a dictionary."""
        return self.model_dump()


@weave.op
def generate_responses(prompt_pair: PromptPair) -> AnalysisData:
    """Generate original and optimized responses for a given prompt pair.

    Args:
        prompt_pair: The user's input prompt pair containing system and user prompts

    Returns:
        Dictionary containing (original_response, optimized_response, analysis_data)
    """
    # Only analyze and optimize the system prompt if it exists
    optimized_system_prompt = None
    if prompt_pair.system_prompt:
        prompt = prompt_pair.system_prompt
    else:
        prompt = prompt_pair.user_prompt

    # Analyze the system prompt
    analysis: PromptAnalysis = analyze_prompt(prompt, is_system_prompt=True)

    # Optimize the system prompt
    optimized: OptimizedPrompt = optimize_prompt(analysis, prompt)
    optimized_system_prompt = optimized.optimized_prompt

    # Get responses for both prompts
    comparison: PromptComparison = compare_outputs(prompt_pair, optimized_system_prompt)
    scores: OutputScore = score_outputs(
        prompt_pair, comparison.original_output, comparison.optimized_output
    )

    analysis_data = AnalysisData(
        program_key=analysis.program_key,
        program_inputs=analysis.program_inputs,
        hallucination_risk=analysis.hallucination_risk,
        hallucination_targets=analysis.hallucination_targets,
        program_improvement_ideas=analysis.program_improvement_ideas,
        comparison_notes=scores.comparison_notes,
        winner=scores.winner,
        original_score=scores.input_1,
        optimized_score=scores.input_2,
        original_system_prompt=prompt_pair.system_prompt,
        optimized_system_prompt=optimized_system_prompt,
        user_prompt=prompt_pair.user_prompt,
        original_output=comparison.original_output,
        optimized_output=comparison.optimized_output,
    )

    return analysis_data


class Choice(str, Enum):
    ORIGINAL = "Original"
    OPTIMIZED = "Optimized"
