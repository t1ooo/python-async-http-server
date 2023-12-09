.PHONY: example
example:
	poetry run python -m examples.example_server


.PHONY: test_example
test_example:
	poetry run pytest -s examples/test_example_server.py
