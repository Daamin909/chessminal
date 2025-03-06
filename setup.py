from setuptools import setup

setup(
    name="chessminal",
    version="1.8",
    packages=["chessminal", "chessminal.assets"],
    package_data={'chessminal': ['assets/*.json']},
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
