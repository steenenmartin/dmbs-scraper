from setuptools import find_packages, setup


setup(
    name="dmbslocal",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages(where="src", include=["dmbslocal*"]),
    install_requires=[],
    entry_points={
        "console_scripts": [
            "dmbs-backend = dmbslocal.scripts:run_backend",
            "dmbs-frontend = dmbslocal.scripts:run_frontend",
        ]
    },
)
