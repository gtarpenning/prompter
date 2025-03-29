import streamlit as st
import weave
from exp import PromptPair, DEFAULT_SYSTEM_PROMPT, DEFAULT_USER_PROMPT
from utils import AnalysisData, generate_responses, Choice

client = weave.init("prompter-app")

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
        value=DEFAULT_SYSTEM_PROMPT,
        key="system_prompt_input",
    )
    user_prompt = st.text_area(
        "User prompt:", value=DEFAULT_USER_PROMPT, key="user_prompt_input"
    )
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
def get_user_eval():
    score_optimized = st.session_state.slider_optimized
    score_original = st.session_state.slider_original
    preferred: Choice = (
        Choice.OPTIMIZED if score_optimized > score_original else Choice.ORIGINAL
    )

    return {
        "score_optimized": score_optimized,
        "score_original": score_original,
        "preferred": preferred,
    }


def show_analysis(original_prompt_pair: PromptPair):
    """Show the analysis of the prompt optimization..."""

    # Get analysis data from session state
    analysis_data: AnalysisData = st.session_state.analysis_data

    user_eval = get_user_eval()

    # Display winner
    if user_eval["preferred"] == Choice.ORIGINAL:
        st.success("**You chose:** your version!")
    else:
        st.error("**You chose:** the optimized version :(")

    # Display scores in a compact format
    col1, col2 = st.columns(2)
    col1.metric("Original score", f"{analysis_data.original_score}/100")
    col2.metric("Optimized score", f"{analysis_data.optimized_score}/100")

    # Display prompts
    st.subheader("Prompts")
    if analysis_data.original_system_prompt:
        col1, col2 = st.columns(2)
        col1.text_area(
            "Original system prompt",
            value=analysis_data.original_system_prompt,
            height=100,
            disabled=True,
        )
        col2.text_area(
            "Optimized system prompt",
            value=analysis_data.optimized_system_prompt,
            height=100,
            disabled=True,
        )
    st.text_area(
        "User prompt", value=analysis_data.user_prompt, height=100, disabled=True
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
    base = "https://wandb.ai/sparc/prompter-st/r/call/"
    op_name = "weave:///sparc/prompter-st/op/generate_responses:*"
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
                st.session_state.original = res["original_output"]
                st.session_state.optimized = res["optimized_output"]
                st.session_state.analysis_data = res["analysis_data"]
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
