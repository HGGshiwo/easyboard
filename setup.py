from setuptools import setup, find_packages

setup(
    name='easyboard',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'streamlit',
        'pandas',
        'plotly'
    ],
    entry_points={
        'console_scripts': [
            # 这行代码的魔法：安装后，终端会多出一个 easyboard 命令！
            'easyboard = easyboard.cli:main' 
        ]
    }
)