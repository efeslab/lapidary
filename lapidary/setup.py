#! /usr/bin/env python3
import setuptools

def main():
    with open("README.md", "r") as fh:
        long_description = fh.read()

    setuptools.setup(
        name="lapidary",
        version="0.0.1",
        author="Ian Glen Neal",
        author_email="ian.gl.neal@gmail.com",
        description="A tool for scalable Gem5 Simulation",
        long_description=long_description,
        long_description_content_type="text/markdown",
        url="",
        packages=setuptools.find_packages(),
        classifiers=[
            "Programming Language :: Python :: 3",
            "License :: OSI Approved :: MIT License",
            "Operating System :: OS Independent",
        ],
    )

if __name__ == '__main__':
    main()
