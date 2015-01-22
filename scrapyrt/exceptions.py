# -*- coding: utf-8 -*-


class ScrapyrtDeprecationWarning(Warning):
    """Warning category for deprecated features, since the default
    DeprecationWarning is silenced on Python 2.7+
    """
    pass
