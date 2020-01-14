#! /usr/bin/env python3
import setuptools

def main():
    with open('README.md', 'r') as f:
        long_description = f.read()

    with open('requirements.txt', 'r') as f:
        install_requires = f.read().split()

    setuptools.setup(
        name='lapidary',
        version='0.7.0',
        author='Ian Glen Neal',
        author_email='iangneal@umich.com',
        description='A tool for scalable Gem5 Simulation',
        long_description=long_description,
        long_description_content_type='text/markdown',
        url='https://github.com/efeslab/lapidary',
        packages=setuptools.find_packages(),
        package_data={'lapidary': ['config/schema.yaml']},
        setup_requires=['wheel'],
        install_requires=install_requires,
        classifiers=[
            'Programming Language :: Python :: 3',
            'License :: OSI Approved :: MIT License',
            'Operating System :: OS Independent',
        ],
    )

if __name__ == '__main__':
    main()
