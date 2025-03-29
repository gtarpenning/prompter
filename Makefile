.PHONY: install lint run clean

install:
	pip install -r requirements.txt

lint:
	ruff check . --fix
	ruff format . 

run-py:
	python exp.py

run:
	streamlit run game.py

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".pytest_cache" -delete
	find . -type f -name ".ruff_cache" -delete 