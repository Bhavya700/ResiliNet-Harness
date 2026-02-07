from setuptools import setup, find_packages

setup(
    name="resilinet_harness",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "scapy",
        "pyroute2",
        "pytest"
    ],
)
