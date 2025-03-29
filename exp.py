from typing import Optional
from pydantic import BaseModel
from openai import OpenAI

import weave

DEFAULT_USER_PROMPT = """
I'm going to the store to buy some eggs.
too bad inflation is so high.
2 eggs isn't enough
I need 100 eggs
small omelettes for breakfast I guess
"""
DEFAULT_SYSTEM_PROMPT = "Rewrite this poem in Shakespeare's style."

MODEL = "gpt-4o"


class PromptPair(BaseModel):
    system_prompt: Optional[str] = None
    user_prompt: str


class PromptAnalysis(BaseModel):
    program_key: str
    program_inputs: list[str]
    hallucination_risk: str
    hallucination_targets: list[str]
    program_improvement_ideas: list[str]
    reasoning: Optional[str] = None


@weave.op
def analyze_prompt(prompt: str, is_system_prompt: bool = False) -> PromptAnalysis:
    client = OpenAI()

    system_instruction = (
        "LLMs can be viewed as continuous, interpolative databases that store both data and vector-based programs. "
        "Unlike traditional databases, data is stored as points in a vector space, enabling interpolation between concepts. "
        "Prompts act as search queries in this space. Use this information to analyze the prompt, to provide information "
        "so that we can generate a better prompt. Include: \n"
        "- **Program Key**: Identifies the instruction that points to a specific behavior in program space.\n"
        "- **Program Inputs**: The data or context the program will act on.\n"
        "- **Risk of Hallucination**: Assessment of where interpolation may cause errors or unexpected outputs.\n"
        "- **Hallucination Targets**: Specific text targets that are at risk of hallucination.\n"
        "- **Program improvement ideas**: Ideas for improving the prompt.\n"
        "\nOutput must be a JSON object with the following fields:\n"
        "- program_key: A concise identifier for the type of operation.\n"
        "- program_inputs: List of identified inputs in the prompt.\n"
        "- hallucination_risk: Assessment of hallucination risk with specific text targets.\n"
        "- hallucination_targets: List of hallucination targets in the text.\n"
        "- program_improvement_ideas: Ideas for improving the prompt.\n"
        "- reasoning: optional: any supporting analysis.\n"
        f"\nPrompt to analyze: {prompt}"
    )

    response = client.chat.completions.create(
        model=MODEL,
        response_format={"type": "json_object"},
        messages=[{"role": "system", "content": system_instruction}],
    )

    # Parse the JSON response into our Pydantic model
    analysis = PromptAnalysis.model_validate_json(response.choices[0].message.content)
    return analysis


class OptimizedPrompt(BaseModel):
    original_prompt: str
    optimized_prompt: str
    improvements: list[str]


@weave.op
def optimize_prompt(analysis: PromptAnalysis, original_prompt: str) -> OptimizedPrompt:
    client = OpenAI()

    system_instruction = (
        "You are a prompt optimization expert. Using the provided prompt analysis, "
        "create an improved version of the original prompt. \n"
        "\nOutput must be a JSON object with:\n"
        "- original_prompt: The input prompt being optimized\n"
        "- optimized_prompt: The improved prompt text\n"
        "- improvements: List of specific improvements made\n"
    )

    # Convert analysis to a readable format for the AI
    analysis_summary = (
        f"Original Prompt: {original_prompt}\n\n"
        f"Analysis:\n"
        f"- Program Key: {analysis.program_key}\n"
        f"- Program Inputs: {', '.join(analysis.program_inputs)}\n"
        f"- Hallucination Risk: {analysis.hallucination_risk}\n"
        f"- Hallucination Targets: {', '.join(analysis.hallucination_targets)}\n"
        f"- Program Improvement Ideas: {', '.join(analysis.program_improvement_ideas)}\n"
        f"- Reasoning: {analysis.reasoning or 'Not provided'}"
    )

    response = client.chat.completions.create(
        model=MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": analysis_summary},
        ],
    )

    # Parse the response and ensure original_prompt is included
    response_data = response.choices[0].message.content
    return OptimizedPrompt.model_validate_json(response_data)


class PromptComparison(BaseModel):
    original_output: str
    optimized_output: str


@weave.op
def compare_outputs(
    prompt_pair: PromptPair, optimized_system_prompt: Optional[str] = None
) -> PromptComparison:
    client = OpenAI()

    # Prepare messages for original prompt
    original_messages = []
    if prompt_pair.system_prompt:
        original_messages.append(
            {"role": "system", "content": prompt_pair.system_prompt}
        )
    original_messages.append({"role": "user", "content": prompt_pair.user_prompt})

    # Get response for original prompt
    original_response = client.chat.completions.create(
        model=MODEL, messages=original_messages
    )

    # Prepare messages for optimized prompt
    optimized_messages = []
    if optimized_system_prompt:
        optimized_messages.append(
            {"role": "system", "content": optimized_system_prompt}
        )
    optimized_messages.append({"role": "user", "content": prompt_pair.user_prompt})

    # Get response for optimized prompt
    optimized_response = client.chat.completions.create(
        model=MODEL, messages=optimized_messages
    )

    return PromptComparison(
        original_output=original_response.choices[0].message.content,
        optimized_output=optimized_response.choices[0].message.content,
    )


class OutputScore(BaseModel):
    input_1: int
    input_2: int
    comparison_notes: list[str]
    winner: str


@weave.op
def score_outputs(
    prompt_pair: PromptPair, original_output: str, optimized_output: str
) -> OutputScore:
    client = OpenAI()

    system_instruction = """You are an expert prompt output evaluator. Score two different outputs based on:
    1. Adherence to the original prompt's intent
    2. Quality and creativity of the response
    3. Coherence and clarity
    4. Appropriate style and tone
    
    Score each output from 1-100 and provide specific reasons for the scoring.
    
    Output must be a JSON object with:
    - input_1: integer score 1-100 for the first output
    - input_2: integer score 1-100 for the second output
    - comparison_notes: list of strings, where each string is a specific observation about the differences between the outputs
    - winner: string indicating which version was better ("input_1", "input_2", or "tie")
    """

    evaluation_request = (
        f"System Prompt: {prompt_pair.system_prompt or 'None'}\n"
        f"User Prompt: {prompt_pair.user_prompt}\n\n"
        f"Input 1:\n{original_output}\n\n"
        f"Input 2:\n{optimized_output}"
    )

    response = client.chat.completions.create(
        model=MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": evaluation_request},
        ],
    )

    return OutputScore.model_validate_json(response.choices[0].message.content)


@weave.op
def run_prompt_optimization(prompt_pair: PromptPair):
    # Only analyze and optimize the system prompt if it exists
    if prompt_pair.system_prompt:
        print("\nAnalyzing system prompt...")
        analysis = analyze_prompt(prompt_pair.system_prompt, is_system_prompt=True)
        print("\nSystem Prompt Analysis:")
        print(f"Program Key: {analysis.program_key}")
        print(f"Program Inputs: {', '.join(analysis.program_inputs)}")
        print(f"Hallucination Risk: {analysis.hallucination_risk}")
        print(f"Hallucination Targets: {', '.join(analysis.hallucination_targets)}")
        print(
            f"Program Improvement Ideas: {', '.join(analysis.program_improvement_ideas)}"
        )

        print("\nOptimizing system prompt...")
        optimized = optimize_prompt(analysis, prompt_pair.system_prompt)
        print("\nOptimized System Prompt:")
        print(f"Original: {optimized.original_prompt}")
        print(f"Optimized: {optimized.optimized_prompt}")
        print("\nImprovements made:")
        for improvement in optimized.improvements:
            print(f"- {improvement}")

        optimized_system_prompt = optimized.optimized_prompt
    else:
        optimized_system_prompt = None

    # Compare outputs
    print("\nComparing outputs...")
    comparison = compare_outputs(prompt_pair, optimized_system_prompt)

    print("\nOriginal Prompt Output:")
    print("=" * 50)
    print(comparison.original_output)

    print("\nOptimized Prompt Output:")
    print("=" * 50)
    print(comparison.optimized_output)

    # Score the outputs
    print("\nScoring outputs...")
    scores = score_outputs(
        prompt_pair, comparison.original_output, comparison.optimized_output
    )

    print("\nScores:")
    print(f"Original Version: {scores.input_1}/100")
    print(f"Optimized Version: {scores.input_2}/100")
    print(f"\nWinner: {scores.winner.title()}")

    print("\nComparison Notes:")
    for note in scores.comparison_notes:
        print(f"- {note}")


def main():
    try:
        weave.init("prompter-dev")
        print("Enter a system prompt (optional):")
        system_prompt = input("> ") or None
        print("Enter a user prompt:")
        user_prompt = input("> ") or DEFAULT_USER_PROMPT
        prompt_pair = PromptPair(system_prompt=system_prompt, user_prompt=user_prompt)
        run_prompt_optimization(prompt_pair)
    except KeyboardInterrupt:
        print("\nProgram interrupted by user. Exiting gracefully...")
        return
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        return


if __name__ == "__main__":
    main()
