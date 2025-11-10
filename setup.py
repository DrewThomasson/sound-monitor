#!/usr/bin/env python3
"""
Setup script for Sound Monitor application
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="sound-monitor",
    version="1.0.0",
    author="Sound Monitor Developer",
    description="A comprehensive noise pollution documentation tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/DrewThomasson/sound-monitor",
    py_modules=["sound_monitor", "run", "test_sound_monitor"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Sound/Audio :: Capture/Recording",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.7",
    install_requires=[
        "PyQt5>=5.15.0",
        "pyaudio>=0.2.11",
        "pydub>=0.25.1",
        "numpy>=1.21.0",
        "matplotlib>=3.5.0",
        "scipy>=1.7.0",
    ],
    extras_require={
        "system-monitoring": ["psutil>=5.8.0"],
    },
    entry_points={
        "console_scripts": [
            "sound-monitor=run:main",
        ],
    },
)
