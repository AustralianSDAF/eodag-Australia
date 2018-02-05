# -*- coding: utf-8 -*-
# Copyright 2015-2018 CS Systemes d'Information (CS SI)
# All rights reserved
from eodag.plugins.base import GeoProductDownloaderPluginMount
from eodag.utils.exceptions import ValidationError
from eodag.utils.validators import URLValidator


class Search(metaclass=GeoProductDownloaderPluginMount):

    def __init__(self, config):
        if not isinstance(config.get('products'), dict):
            raise MisconfiguredError("'products' must be a dictionary of values")
            # TODO: an instance without products should have minimum possible priority => it should be lower bounded
        if not config.get('api_endpoint'):
            raise MisconfiguredError("'api_endpoint' must be a valid url")
        validate_url = URLValidator(schemes=['http', 'https'], message="'api_endpoint' must be a valid url")
        try:
            validate_url(config['api_endpoint'])
        except ValidationError as e:
            raise MisconfiguredError(e.message)
        self.config = config

    def query(self, *args, **kwargs):
        """Implementation of how the products must be searched goes here.

        This method must return a list of EOProduct instances (see eodag.api.product module) which will
        be processed by a Download plugin.
        """
        raise NotImplementedError('A Search plugin must implement a method named query')


class MisconfiguredError(Exception):
    """An error indicating a Search Plugin that is not well configured"""
