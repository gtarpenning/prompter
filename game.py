import streamlit as st
import weave
from exp import PromptPair, DEFAULT_SYSTEM_PROMPT, DEFAULT_USER_PROMPT
from utils import AnalysisData, generate_responses, Choice

PROJECT_ID = "sparc/prompter-app"
client = weave.init(PROJECT_ID)

# Set page to wide mode
st.set_page_config(layout="wide")


def initialize_session_state():
    """Initialize session state variables"""
    if "current_stage" not in st.session_state:
        st.session_state.current_stage = "input"
    if "scores" not in st.session_state:
        st.session_state.scores = []
    if "analysis_data" not in st.session_state:
        st.session_state.analysis_data = None
    if "previous_system_prompt" not in st.session_state:
        st.session_state.previous_system_prompt = DEFAULT_SYSTEM_PROMPT
    if "previous_user_prompt" not in st.session_state:
        st.session_state.previous_user_prompt = DEFAULT_USER_PROMPT


def display_header():
    """Display the game header and title"""
    if st.session_state.current_stage == "input":
        st.title("Is Prompt Engineering Dead?")
    else:
        st.title("Prompter")
    # Add space between title and content
    st.markdown("<br>", unsafe_allow_html=True)


def get_user_prompts():
    """Get the system and user prompts from the user"""
    system_prompt = st.text_area(
        "System prompt (optional):",
        value=st.session_state.previous_system_prompt,
        key="system_prompt_input",
        height=180,
    )
    user_prompt = st.text_area(
        "User prompt:",
        value=st.session_state.previous_user_prompt,
        key="user_prompt_input",
        height=180,
    )

    # Store the prompts for next time
    st.session_state.previous_system_prompt = system_prompt
    st.session_state.previous_user_prompt = user_prompt

    return PromptPair(
        system_prompt=system_prompt if system_prompt else None, user_prompt=user_prompt
    )


def display_responses(original, optimized):
    """Display the responses in side-by-side columns"""
    col1, col2 = st.columns(2)

    # Randomly assign responses to columns
    if hash(original) % 2 == 0:
        col1.text_area("Response A:", value=original, height=200, disabled=True)
        col2.text_area("Response B:", value=optimized, height=200, disabled=True)
        col1.slider("Rate response A:", 1, 10, key="slider_original")
        col2.slider("Rate response B:", 1, 10, key="slider_optimized")
    else:
        col1.text_area("Response A:", value=optimized, height=200, disabled=True)
        col2.text_area("Response B:", value=original, height=200, disabled=True)
        col1.slider("Rate response A:", 1, 10, key="slider_optimized")
        col2.slider("Rate response B:", 1, 10, key="slider_original")


@weave.op
def get_user_eval(score_optimized: int, score_original: int):
    preferred: Choice = (
        Choice.OPTIMIZED if score_optimized > score_original else Choice.ORIGINAL
    )

    return {
        "score_optimized": score_optimized,
        "score_original": score_original,
        "preferred": preferred,
        "user_chose_optimized": score_optimized > score_original,
    }


def show_analysis(original_prompt_pair: PromptPair):
    """Show the analysis of the prompt optimization..."""

    if st.session_state.current_stage != "analysis":
        return

    # Get analysis data from session state
    analysis_data: AnalysisData = st.session_state.analysis_data

    score_optimized = st.session_state.get("slider_optimized", -1)
    score_original = st.session_state.get("slider_original", -1)
    if score_optimized == -1 or score_original == -1:
        st.session_state.current_stage = "input"

    user_eval = get_user_eval(score_optimized, score_original)

    # Display winner
    if not user_eval["user_chose_optimized"]:
        st.success("**You chose:** your version!")
    else:
        st.error("**You chose:** the optimized version :(")

    # Display scores in a compact format
    col1, col2 = st.columns(2)
    col1.metric("Original score", f"{analysis_data.original_score}/100")
    col2.metric("Optimized score", f"{analysis_data.optimized_score}/100")

    # Display prompts
    st.subheader("Prompts")
    col1, col2 = st.columns(2)
    col1.text_area(
        "Original system prompt",
        value=analysis_data.original_system_prompt,
        height=150,
        disabled=True,
    )
    col2.text_area(
        "Optimized system prompt",
        value=analysis_data.optimized_system_prompt,
        height=150,
        disabled=True,
    )
    st.text_area(
        "User prompt", value=analysis_data.user_prompt, height=200, disabled=True
    )
    col1, col2 = st.columns(2)
    col1.text_area(
        "Original output",
        value=analysis_data.original_output,
        height=200,
        disabled=True,
    )
    col2.text_area(
        "Optimized output",
        value=analysis_data.optimized_output,
        height=200,
        disabled=True,
    )

    # Display program analysis in a table
    st.subheader("Optimization analysis")
    analysis_table = {
        "Key": [
            "Program key",
            "Program inputs",
            "Hallucination risk",
            "Hallucination targets",
            "Potential improvements",
        ],
        "Value": [
            analysis_data.program_key,
            "\n".join(analysis_data.program_inputs),
            analysis_data.hallucination_risk,
            "\n".join(analysis_data.hallucination_targets),
            "\n".join(analysis_data.program_improvement_ideas),
        ],
    }
    st.table(analysis_table)

    # Display comparison notes
    st.write("### Comparison notes")
    for note in analysis_data.comparison_notes:
        st.write(f"- {note}")

    # View weave traces
    st.markdown("---")
    st.markdown("### View weave traces")
    base = f"https://wandb.ai/{PROJECT_ID}/r/call/"
    op_name = f"weave:///{PROJECT_ID}/op/generate_responses:*"
    call = client.get_calls(
        filter={"op_names": [op_name]},
        sort_by=[{"field": "started_at", "direction": "desc"}],
    )[0]
    st.markdown(f"[{base}{call.id}]({base}{call.id})")

    # Add challenge message and restart button
    st.markdown("---")
    st.markdown("### Think you can write a better prompt?")
    st.markdown(
        "Try your hand at crafting a prompt that generates even better results!"
    )

    if st.button("Try again", key="restart_button"):
        st.session_state.current_stage = "input"
        st.rerun()


def main():
    initialize_session_state()
    display_header()

    if st.session_state.current_stage == "input":
        prompt_pair = get_user_prompts()
        if st.button("Generate responses"):
            with st.spinner("Working our magic..."):
                res = generate_responses(prompt_pair)
                st.session_state.original = res.original_output
                st.session_state.optimized = res.optimized_output
                st.session_state.analysis_data = res
                st.session_state.current_stage = "evaluate"
            st.rerun()

    elif st.session_state.current_stage == "evaluate":
        display_responses(st.session_state.original, st.session_state.optimized)

        if st.button("Show analysis"):
            st.session_state.current_stage = "analysis"
            st.rerun()

    elif st.session_state.current_stage == "analysis":
        show_analysis(st.session_state.analysis_data)


if __name__ == "__main__":
    main()
