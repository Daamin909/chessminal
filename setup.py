from setuptools import setup

setup(
    name="chessminal",
    version="2.1",
    packages=["chessminal"],
    package_data={},
    include_package_data=True,
    install_requires=[
        "chess",
        "python-chess",
        "stockfish",
        "requests",
        "rich",
    ],
    entry_points={
        "console_scripts": [
            "chessminal=chessminal.main:main",
        ],
    },
)
