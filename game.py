import streamlit as st
import weave
from exp import PromptPair, DEFAULT_SYSTEM_PROMPT, DEFAULT_USER_PROMPT
from utils import AnalysisData, generate_responses

# Set page to wide mode
st.set_page_config(layout="wide")

client = weave.init("prompter-st")


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
        col1.slider("Rate response A:", 1, 10, key="slider_a")
        col2.slider("Rate response B:", 1, 10, key="slider_b")
    else:
        col1.text_area("Response A:", value=optimized, height=200, disabled=True)
        col2.text_area("Response B:", value=original, height=200, disabled=True)
        col1.slider("Rate response A:", 1, 10, key="slider_a")
        col2.slider("Rate response B:", 1, 10, key="slider_b")


@weave.op
def get_user_evaluation():
    """Get user's evaluation of both responses"""
    # Get values from the sliders that were created in display_responses
    response_a_score = st.session_state.slider_a
    response_b_score = st.session_state.slider_b
    preferred = "Response A" if response_a_score > response_b_score else "Response B"
    return {
        "response_a_score": response_a_score,
        "response_b_score": response_b_score,
        "preferred": preferred,
    }


def show_analysis(original_prompt_pair: PromptPair):
    """Show the analysis of the prompt optimization..."""

    # Get analysis data from session state
    analysis_data: AnalysisData = st.session_state.analysis_data

    # Display winner
    if analysis_data.winner == "input_1":
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
        get_user_evaluation()

        if st.button("Show analysis"):
            st.session_state.current_stage = "analysis"
            st.rerun()

    elif st.session_state.current_stage == "analysis":
        show_analysis(st.session_state.analysis_data)


if __name__ == "__main__":
    main()
