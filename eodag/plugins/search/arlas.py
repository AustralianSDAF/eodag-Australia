# -*- coding: utf-8 -*-
# Copyright 2018 CS Systemes d'Information (CS SI)
# All rights reserved
from __future__ import unicode_literals

import logging

import requests
import shapely.geometry

from eodag.api.product import EOProduct
from eodag.plugins.search.base import Search
from eodag.utils import get_timestamp


logger = logging.getLogger('eodag.plugins.search.arlas')


class ArlasSearch(Search):
    SEARCH_ENDPOINT_TPL = '/explore/{arlas_collection}/_geosearch'
    COUNT_ENDPOINT_TPL = '/explore/{arlas_collection}/_count'

    def query(self, product_type, auth=None, **kwargs):
        logger.info('New search for product type : *%s* on %s interface', product_type, self.name)
        query_string = self.build_query_string(product_type, kwargs)
        if auth:
            auth = auth.authenticate()

        total_hits = self.count_products(query_string, auth)

        # Do not perform the search if the criteria lead to 0 result
        if total_hits == 0:
            return []

        # If there was a silenced error during result counting (total_hits == -1), perform the search anyway without
        # specifying the size query string parameter
        if total_hits != -1:
            query_string += '&size={}'.format(total_hits)

        search_url = '{base}{path}?{qs}'.format(
            base=self.config['api_endpoint'].rstrip('/'),
            path=self.SEARCH_ENDPOINT_TPL.format(**self.config),
            qs=query_string
        )

        logger.info('Making search request at: %s', search_url)
        response = requests.get(search_url, auth=auth)
        try:
            logger.info('Checking response')
            response.raise_for_status()
            logger.info('Search requests successful. HTTP status code: %s', response.status_code)
        except requests.HTTPError:
            import traceback as tb
            logger.warning('Failed to query arlas server at %s. Got error:\n%s',
                           self.config['api_endpoint'], tb.format_exc())
            return []

        results = response.json()
        products = []
        try:
            if results['features']:
                logger.info('Normalizing results')
                for feature in results['features']:
                    products.append(EOProduct(
                        self.instance_name,
                        '{base}' + '/{}'.format(feature['properties']['uid']),
                        '{}.zip'.format(feature['properties']['identification']['externalId']),
                        shapely.geometry.shape(feature['geometry']),
                        kwargs['footprint'],
                        feature['properties']['identification']['type'],
                        feature['properties']['acquisition']['missionCode'],
                        feature['properties']['acquisition']['sensorId'],
                        provider_id=feature['properties']['uid']
                    ))
        except KeyError as ke:
            if 'features' in ke:
                logger.warning('Invalid geojson returned: %s, assuming no results', results)
                return []
            raise ke
        logger.info('Search on Arlas server %s succeeded. Results: %s', self.config['api_endpoint'], products)
        return products

    def build_query_string(self, product_type, options):
        """Build the query string that is used to perform search requests

        :param product_type: the code of the product type to look for as defined by eodag
        :type product_type: str or unicode
        :param options: the additional search criteria that are not mandatory for a search on eodag
        :type options: dict
        :return:
        """
        logger.debug('Building the query string that will be used for search')
        mandatory_qs = 'f=identification.type:eq:{}'.format(self.config['products'][product_type]['product_type'])
        optional_qs = ''

        max_cloud_cover = options.get('maxCloudCover')
        if max_cloud_cover:
            logger.debug('Adding filter for max cloud cover: %s', max_cloud_cover)
            optional_qs += '&contentDescription.cloudCoverPercentage:range:0,{max}'.format(
                max=max_cloud_cover)

        footprint = options.get('footprint')
        if footprint:
            logger.debug('Adding filter for footprint: %s', footprint)
            optional_qs += '&gintersect={lonmin},{latmin},{lonmax},{latmax}'.format(**footprint)

        start_date = options.get('startDate')
        end_date = options.get('endDate')
        if start_date:
            start_timestamp = int(1e3 * get_timestamp(start_date))
            if end_date:
                logger.debug('Adding filter for sensing date range: %s - %s', start_date, end_date)
                end_timestamp = int(1e3 * get_timestamp(end_date))
                optional_qs += '&f=acquisition.beginViewingDate:range:[{min}<{max}]'.format(
                    min=start_timestamp, max=end_timestamp)
            else:
                logger.debug('Adding filter for minimum sensing date: %s', start_date)
                optional_qs += '&f=acquisition.beginViewingDate:gte:{min}'.format(min=start_timestamp)
        elif end_date:
            logger.debug('Adding filter for maximum sensing date: %s', end_date)
            end_timestamp = int(1e3 * get_timestamp(end_date))
            optional_qs += '&f=acquisition.beginViewingDate:lte:{max}'.format(max=end_timestamp)

        return '{}{}'.format(mandatory_qs, optional_qs)

    def count_products(self, query_string, auth):
        """Return the total number of results that can be found given the search_url

        :param query_string: the query string that will serve as filter
        :type query_string: str or unicode
        :param auth: the authentication information if needed
        :return: the number of products that will be reached if we perform a search with this query string
        :rtype: int
        """
        logger.info('Looking for the number of products satisfying the search criteria')
        response = requests.get(
            '{base}{path}?{qs}'.format(
                base=self.config['api_endpoint'],
                path=self.COUNT_ENDPOINT_TPL.format(**self.config),
                qs=query_string
            ),
            auth=auth
        )
        try:
            response.raise_for_status()
        except requests.HTTPError:
            import traceback as tb
            logger.warning('Unable to determine the number of products satisfying the criteria. Got error:\n%s',
                           tb.format_exc())
            return -1
        return response.json()['totalnb']
