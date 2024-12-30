from setuptools import setup, find_namespace_packages

setup(
    name="tmpl_generator",
    version="1.0.0",
    packages=find_namespace_packages(include=['*']),
    install_requires=[
        'numpy',
        'opencv-python',
        'psutil',
    ],
    python_requires='>=3.7',
)