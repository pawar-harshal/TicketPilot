"""
setup.py declares the external PyPI packages ticketpilot_das depends on.
It does NOT wrap any custom config/logging package -- we use Python's own
configparser and logging modules directly (see utils/ConfigReader.py and
utils/Logger.py).
"""
from setuptools import find_packages, setup

setup(
    name="ticketpilot_das",
    version="1.0.0",
    description="TicketPilot data-access-and-service layer: AI-agent-driven customer support for QuickCrave.",
    author="Harshal Pawar",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "fastapi>=0.115,<1.0",
        "uvicorn[standard]>=0.30,<1.0",
        "sqlalchemy>=2.0,<3.0",
        "pymysql>=1.1,<2.0",
        "pydantic[email]>=2.7,<3.0",
        "qdrant-client>=1.9,<2.0",
        "openai>=1.30,<2.0",  # used as an OpenAI-compatible client against OpenRouter, for both chat and embeddings
        "pyjwt>=2.8,<3.0",
        "passlib[bcrypt]>=1.7,<2.0",
        "bcrypt>=3.1.7,<4.1",
        "python-multipart>=0.0.9",
        "retrying>=1.3.3,<2.0",
    ],
    python_requires=">=3.10",
)