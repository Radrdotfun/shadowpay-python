"""Setup script for shadowpay package."""

from setuptools import setup, find_packages

setup(
    name="shadowpay",
    packages=find_packages(),
    package_data={
        "shadowpay": ["py.typed"],
    },
    include_package_data=True,
)

