# Prompter

A Streamlit-based web application for analyzing and optimizing prompts using LLMs. The app allows users to input system and user prompts, generates responses using both original and optimized prompts, and provides detailed analysis of the optimization process.

- [View the project storyboard](./storyboard.txt)
- [View the weave project](https://wandb.ai/sparc/prompter-st/weave/traces)

## Setup and Usage

The project uses Make for common development tasks:

```bash
export OPENAI_API_KEY=
export WANDB_API_KEY=

# Install dependencies
make install

# Run the streamlit app
make run

# Run the terminal app
make run-py

# Lint the codebase
make lint

# Clean up cache files
make clean
```

## Requirements

- Python 3.8+
- See `requirements.txt` for Python package dependencies 