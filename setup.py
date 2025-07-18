from setuptools import setup, find_packages

# Read requirements from requirements.txt
def read_requirements():
    with open('requirements.txt', 'r') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

# Read README for long description
with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="frappe-pre-commit",
    version="1.0.0",
    description="Pre-commit hooks for Frappe Framework coding standards",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Bhushan Barbuddhe",
    author_email="bhushan.barbuddh@dhwaniris.com",
    url="https://github.com/dhwani-ris/frappe-pre-commit",
    packages=find_packages(),
    include_package_data=True,
    install_requires=read_requirements(),
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Quality Assurance",
    ],
    keywords="frappe erpnext pre-commit hooks code-quality",
)