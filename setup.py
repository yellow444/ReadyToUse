from setuptools import setup, Extension
from Cython.Build import cythonize
import numpy

extensions = [
    Extension(
        "app._assign_abc",
        ["app/_assign_abc.pyx"],
        extra_compile_args=["-O3", "-fopenmp"],
        extra_link_args=["-fopenmp"],
        include_dirs=[numpy.get_include()],
    )
]

setup(
    name="ReadyToUse",
    version="0.1.0",
    packages=["app"],
    package_dir={"app": "app"},
    ext_modules=cythonize(extensions, language_level=3),
)
