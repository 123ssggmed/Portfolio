install:
	pip install -r requirements.txt

test:
	pytest tests/ -v --tb=short

run:
	python src/audit_cli.py

clean:
	rm -rf __pycache__ .venv
