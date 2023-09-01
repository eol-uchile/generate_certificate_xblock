
import os

from setuptools import setup

def package_data(pkg, roots):
    """Generic function to find package_data.

    All of the files under each of the `roots` will be declared as package
    data for package `pkg`.

    """
    data = []
    for root in roots:
        for dirname, _, files in os.walk(os.path.join(pkg, root)):
            for fname in files:
                data.append(os.path.relpath(os.path.join(dirname, fname), pkg))

    return {pkg: data}

setup(
    name="generate_certificate",
    version="0.0.1",
    author="Matías Melo",
    author_email="matias.melo@uchile.cl",
    description=".",
    url="https://eol.uchile.cl",
    packages=["generate_certificate"],
    install_requires=[
        'XBlock',
        ],
    classifiers=[
        "Programming Language :: Python :: 2",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'xblock.v1': ['generate_certificate = generate_certificate:CertificateLinkXBlock']
    },
    package_data=package_data("generate_certificate", ["static", "public"]),
)
