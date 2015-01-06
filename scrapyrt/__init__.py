# -*- coding: utf-8 -*-
from distutils.version import LooseVersion
import pkgutil

__version__ = pkgutil.get_data(__package__, 'VERSION').decode('ascii').strip()
version_info = tuple(LooseVersion(__version__).version)

__all__ = ['__version__', 'version_info']
