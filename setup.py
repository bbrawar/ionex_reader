from setuptools import setup, find_packages

setup(
    name='ionex_reader',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'numpy',
        'matplotlib',
        'xarray',
        'cartopy',
        'mpl_toolkits'
    ],
    author='Bhuvi Brawar',
    author_email='bbrawar@gmail.com',
    description='A module to read and plot IONEX TEC maps as xarray Datasets',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/yourusername/ionex_reader',  # Replace with your GitHub repo URL
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
