# -*- coding: utf-8 -*-
from pkg_resources import parse_version
import pkgutil

__version__ = pkgutil.get_data(__package__, 'VERSION').decode('ascii').strip()
version_info = parse_version(__version__)

__all__ = ['__version__', 'version_info']
