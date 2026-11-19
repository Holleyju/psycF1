import setuptools

setuptools.setup(
    name="f1_pipeline",
    version="0.1.0",
    description="F1 pit stop analysis for PSYC 40650",
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    install_requires=["pandas", "matplotlib", "numpy", "scikit-learn","ipykernel", "scipy", "seaborn"],
)
