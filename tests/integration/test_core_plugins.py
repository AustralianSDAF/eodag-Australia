# -*- coding: utf-8 -*-
# Copyright 2018 CS Systemes d'Information (CS SI)
# All rights reserved
from __future__ import unicode_literals

import functools
import os
import unittest

import requests

from tests import EODagTestCase, TEST_RESOURCES_PATH
from tests.context import EOProduct, SatImagesAPI, SearchResult


try:
    from unittest import mock  # PY3
except ImportError:
    import mock  # PY2


class TestIntegrationCoreSearchPlugins(EODagTestCase):

    def test_core_resto_search_ok(self):
        """A search with a product type supported by a provider implementing RestoSearch must succeed"""
        self.override_properties(
            provider='mock-provider-1',
            product_type='MOCK_PRODUCT_TYPE',
            platform='',
            instrument='')
        provider_search_url_base = 'http://subdomain.domain.eu/resto/api/'  # See ../resources/mock_providers.yml
        resto_results = {
            'features': [
                {
                    'id': 1,
                    'geometry': self.geometry,
                    'properties': {
                        'productType': 'MOCK',  # See ../resources/mock_providers.yml
                        'platform': self.platform,
                        'instrument': self.instrument,
                        'completionDate': '',
                        'collection': 'MockCollection',  # See ../resources/mock_providers.yml
                        'productIdentifier': '/eodata/1/{}'.format(self.local_filename),
                        'organisationName': 'ESA',
                        'title': '1_{}'.format(self.local_filename),
                        'snowCover': '',
                        'cloudCover': '',
                        'description': '',
                        'keywords': '',
                        'resolution': '',
                        'startDate': '',
                        'orbitNumber': 0,
                    },
                },
                {
                    'id': 2,
                    'geometry': self.geometry,
                    'properties': {
                        'productType': 'MOCK',
                        'platform': '',
                        'instrument': '',
                        'completionDate': '',
                        'collection': 'MockCollection',
                        'productIdentifier': '/eodata/2/{}'.format(self.local_filename),
                        'organisationName': 'NOT_ESA',  # To see if the url given in 'services' below is used
                        'title': '2_{}'.format(self.local_filename),
                        'services': {
                            'download': {
                                'url': 'http://download.provider1.com/path/',
                            },
                        },
                        'snowCover': '',
                        'cloudCover': '',
                        'description': '',
                        'keywords': '',
                        'resolution': '',
                        'startDate': '',
                        'orbitNumber': 0,
                    },
                },
                {
                    'id': 3,
                    'geometry': self.geometry,
                    'properties': {
                        'productType': 'MOCK',
                        'platform': '',
                        'instrument': '',
                        'completionDate': '',
                        'collection': 'MockCollection',
                        'productIdentifier': '/eodata/3/{}'.format(self.local_filename),
                        'organisationName': 'NOT_ESA',  # To see if the url given in 'services' below is used
                        'title': '2_{}'.format(self.local_filename),
                        'snowCover': '',
                        'cloudCover': '',
                        'description': '',
                        'keywords': '',
                        'resolution': '',
                        'startDate': '',
                        'orbitNumber': 0,
                    },
                },
            ],
        }
        nominal_params = {
            'startDate': None,
            'cloudCover': '[0,20]',  # See RestoSearch.DEFAULT_MAX_CLOUD_COVER
            'sortOrder': 'descending',
            'sortParam': 'startDate',
            'productType': 'MOCK'
        }

        requests_http_get_response = self.requests_http_get.return_value
        requests_http_get_response.raise_for_status = mock.MagicMock()
        requests_http_get_response.json = mock.MagicMock(return_value=resto_results)

        dag = SatImagesAPI(providers_file_path=os.path.join(TEST_RESOURCES_PATH, 'mock_providers.yml'))
        results = dag.search(self.product_type)

        self.assertHttpGetCalledOnceWith(
            '{}collections/MockCollection/search.json'.format(provider_search_url_base),
            expected_params=nominal_params)
        self.assertEqual(requests_http_get_response.raise_for_status.call_count, 1)
        self.assertEqual(requests_http_get_response.json.call_count, 1)

        # Check the search result
        self.assertIsInstance(results, SearchResult)
        self.assertEqual(len(results), len(resto_results['features']))
        for idx, result in enumerate(results):
            self.assertIsInstance(result, EOProduct)
            self.assertEqual(result.provider, self.provider)
            self.assertEqual(result.product_type, 'MOCK')  # See ../resources/mock_providers.yml for 'MOCK'
            self.assertDictContainsSubset(
                {k: v for k, v in result.properties.items() if k not in ('endDate', 'provider_id')},
                resto_results['features'][idx]['properties'])
            self.assertEqual(result.properties['provider_id'], resto_results['features'][idx]['id'])
            self.assertEqual(result.properties['endDate'],
                             resto_results['features'][idx]['properties']['completionDate'])

            if idx == 0:
                self.assertEqual(result.location_url_tpl,
                                 '{base}/1/S2A_MSIL1C_20180101T105441_N0206_R051_T31TDH_20180101T124911.SAFE.zip')
            if idx == 1:
                self.assertEqual(result.location_url_tpl, 'http://download.provider1.com/path/')
            if idx == 2:
                self.assertEqual(result.location_url_tpl, '{base}/collections/MockCollection/3/download')

        # Test the use case of defining the product location scheme to 'file'
        self.override_properties(product_type='MOCK_PRODUCT_TYPE_5')
        results = dag.search(self.product_type)
        for idx, result in enumerate(results):
            self.assertEqual(result.location_url_tpl,
                             'file://{}'.format(resto_results['features'][idx]['properties']['productIdentifier']))

        # Test that when nothing is found, the returned result is empty
        requests_http_get_response.json = mock.MagicMock(return_value={'features': []})
        results = dag.search(self.product_type)
        self.assertEqual(len(results), 0)

    def test_core_resto_search_http_error(self):
        """If there is an requests.HTTPError, resto search must return an empty list of result"""
        self.override_properties(product_type='MOCK_PRODUCT_TYPE')
        provider_search_url_base = 'http://subdomain.domain.eu/resto/api/'  # See ../resources/mock_providers.yml
        nominal_params = {
            'startDate': None,
            'cloudCover': '[0,20]',  # See RestoSearch.DEFAULT_MAX_CLOUD_COVER
            'sortOrder': 'descending',
            'sortParam': 'startDate',
            'productType': 'MOCK'
        }

        requests_http_get_response = self.requests_http_get.return_value
        requests_http_get_response.raise_for_status = mock.MagicMock(side_effect=requests.HTTPError)

        dag = SatImagesAPI(providers_file_path=os.path.join(TEST_RESOURCES_PATH, 'mock_providers.yml'))
        # requests.get will return a response that will raise an requests.HTTPError when raise_for_status is called
        results = dag.search(self.product_type)

        self.assertEqual(requests_http_get_response.raise_for_status.call_count, 1)
        self.assertHttpGetCalledOnceWith(
            '{}collections/MockCollection/search.json'.format(provider_search_url_base),
            expected_params=nominal_params)

        # Assertions showing that the HTTPError was ignored and an empty list was returned as the result
        self.assertIsInstance(results, SearchResult)
        self.assertEqual(len(results), 0)

    def test_core_resto_search_configured_max_cloud_cover_ok(self):
        """A maxCloudCover config parameter must be the default max cloud cover for a search"""
        self.override_properties(product_type='MOCK_PRODUCT_TYPE_2')
        provider_search_url_base = 'http://subdomain2.domain.eu/resto/api/'  # See ../resources/mock_providers.yml
        configured_max_cloud_cover = 50  # See ../resources/mock_providers.yml
        call_params = {
            'startDate': None,
            'cloudCover': '[0,{}]'.format(configured_max_cloud_cover),
            'sortOrder': 'descending',
            'sortParam': 'startDate',
            'productType': 'MOCK2'
        }

        dag = SatImagesAPI(providers_file_path=os.path.join(TEST_RESOURCES_PATH, 'mock_providers.yml'))
        dag.search(self.product_type)

        self.assertHttpGetCalledOnceWith(
            '{}collections/MockCollection2/search.json'.format(provider_search_url_base),
            expected_params=call_params)

    def test_core_resto_search_configured_max_cloud_cover_over100_ko(self):
        """A maxCloudCover config parameter greater than 100 must raise a runtime_error"""
        self.override_properties(product_type='MOCK_PRODUCT_TYPE_3')
        dag = SatImagesAPI(providers_file_path=os.path.join(TEST_RESOURCES_PATH, 'mock_providers.yml'))
        self.assertRaises(RuntimeError, dag.search, self.product_type)

    def test_core_resto_search_configured_max_cloud_cover_below0_ko(self):
        """A maxCloudCover config parameter lower than 0 must raise a runtime_error"""
        self.override_properties(product_type='MOCK_PRODUCT_TYPE_4')
        dag = SatImagesAPI(providers_file_path=os.path.join(TEST_RESOURCES_PATH, 'mock_providers.yml'))
        self.assertRaises(RuntimeError, dag.search, self.product_type)

    def test_core_resto_search_kwargs_cloud_cover_default_ok(self):
        """A search with a cloud cover between 0 and the default max cloud cover must succeed"""
        self.override_properties(product_type='MOCK_PRODUCT_TYPE')
        kwargs = {'maxCloudCover': 5}  # RestoSearch.DEFAULT_MAX_CLOUD_COVER is 20
        provider_search_url_base = 'http://subdomain.domain.eu/resto/api/'  # See ../resources/mock_providers.yml
        call_params = {
            'startDate': None,
            'cloudCover': '[0,{maxCloudCover}]'.format(**kwargs),
            'sortOrder': 'descending',
            'sortParam': 'startDate',
            'productType': 'MOCK'
        }

        dag = SatImagesAPI(providers_file_path=os.path.join(TEST_RESOURCES_PATH, 'mock_providers.yml'))
        dag.search(self.product_type, **kwargs)

        self.assertHttpGetCalledOnceWith(
            '{}collections/MockCollection/search.json'.format(provider_search_url_base),
            expected_params=call_params)

    def test_core_resto_search_kwargs_cloud_cover_outbounds_ko(self):
        """A search with a cloud cover greater than 100 or lower than 0 must raise a RuntimeError"""
        self.override_properties(product_type='MOCK_PRODUCT_TYPE')
        dag = SatImagesAPI(providers_file_path=os.path.join(TEST_RESOURCES_PATH, 'mock_providers.yml'))
        self.assertRaises(RuntimeError, dag.search, self.product_type, maxCloudCover=101)
        self.assertRaises(RuntimeError, dag.search, self.product_type, maxCloudCover=-1)

    def test_core_resto_search_kwargs_cloud_cover_capped_ok(self):
        """A search with a cloud cover greater than the default max cloud cover must be capped to default"""
        self.override_properties(product_type='MOCK_PRODUCT_TYPE')
        kwargs = {'maxCloudCover': 30}  # RestoSearch.DEFAULT_MAX_CLOUD_COVER is 20
        provider_search_url_base = 'http://subdomain.domain.eu/resto/api/'  # See ../resources/mock_providers.yml
        call_params = {
            'startDate': None,
            'cloudCover': '[0,20]',
            'sortOrder': 'descending',
            'sortParam': 'startDate',
            'productType': 'MOCK'
        }

        dag = SatImagesAPI(providers_file_path=os.path.join(TEST_RESOURCES_PATH, 'mock_providers.yml'))
        dag.search(self.product_type, **kwargs)

        self.assertHttpGetCalledOnceWith(
            '{}collections/MockCollection/search.json'.format(provider_search_url_base),
            expected_params=call_params)

    def test_core_resto_search_kwargs_end_date_ok(self):
        """A search with an endDate must succeed"""
        self.override_properties(product_type='MOCK_PRODUCT_TYPE')
        kwargs = {'endDate': '2018-05-09'}
        provider_search_url_base = 'http://subdomain.domain.eu/resto/api/'  # See ../resources/mock_providers.yml
        call_params = {
            'startDate': None,
            'cloudCover': '[0,20]',
            'sortOrder': 'descending',
            'sortParam': 'startDate',
            'productType': 'MOCK',
            'completionDate': kwargs['endDate']
        }

        dag = SatImagesAPI(providers_file_path=os.path.join(TEST_RESOURCES_PATH, 'mock_providers.yml'))
        dag.search(self.product_type, **kwargs)

        self.assertHttpGetCalledOnceWith(
            '{}collections/MockCollection/search.json'.format(provider_search_url_base),
            expected_params=call_params)

    def test_core_resto_search_kwargs_footprint_ok(self):
        """A search with a footprint must succeed"""
        self.override_properties(product_type='MOCK_PRODUCT_TYPE')
        # first use case: footprint is a point
        kwargs = {'footprint': {'lat': self.footprint['latmin'], 'lon': self.footprint['lonmin']}}
        provider_search_url_base = 'http://subdomain.domain.eu/resto/api/'  # See ../resources/mock_providers.yml
        call_params = {
            'startDate': None,
            'cloudCover': '[0,20]',
            'sortOrder': 'descending',
            'sortParam': 'startDate',
            'productType': 'MOCK',
            'lat': kwargs['footprint']['lat'],
            'lon': kwargs['footprint']['lon'],
        }

        dag = SatImagesAPI(providers_file_path=os.path.join(TEST_RESOURCES_PATH, 'mock_providers.yml'))
        dag.search(self.product_type, **kwargs)

        self.assertHttpGetCalledOnceWith(
            '{}collections/MockCollection/search.json'.format(provider_search_url_base),
            expected_params=call_params)

        # second use case: footprint is a bbox
        self.requests_http_get.reset_mock()
        call_params = {
            'startDate': None,
            'cloudCover': '[0,20]',
            'sortOrder': 'descending',
            'sortParam': 'startDate',
            'productType': 'MOCK',
            'box': '{lonmin},{latmin},{lonmax},{latmax}'.format(**self.footprint)
        }
        dag.search(self.product_type, **{'footprint': self.footprint})
        self.assertHttpGetCalledOnceWith(
            '{}collections/MockCollection/search.json'.format(provider_search_url_base),
            expected_params=call_params)

    @mock.patch('eodag.plugins.search.csw.PropertyIsEqualTo', autospec=True)
    @mock.patch('eodag.plugins.search.csw.PropertyIsLike', autospec=True)
    @mock.patch('eodag.plugins.search.csw.CatalogueServiceWeb', autospec=True)
    def test_core_csw_search_auth_default_version_ok(self, mock_catalogue_web_service, prop_like, prop_eq):
        """A search on a provider implementing CSWSearch with auth requirement and default csw version must succeed"""
        self.override_properties(provider='mock-provider-7', product_type='MOCK_PRODUCT_TYPE_7')
        default_version = '2.0.2'
        dag = SatImagesAPI(
            providers_file_path=os.path.join(TEST_RESOURCES_PATH, 'mock_providers.yml'),
            user_conf_file_path=os.path.join(TEST_RESOURCES_PATH, 'mock_user_conf.yml'))
        mock_catalog = mock_catalogue_web_service.return_value

        mock_catalog.getrecords2.side_effect = functools.partial(self.compute_csw_records, mock_catalog)

        results = dag.search(self.product_type)

        # Catalog service is created only once
        self.assertEqual(mock_catalogue_web_service.call_count, 1)

        # One result for each search tag (dc:title and dc:subject)
        self.assertEqual(len(results), 5)
        mock_catalogue_web_service.assert_called_with(
            'http://www.catalog.com/rest/catalog/csw/',
            version=default_version,
            username='user',
            password='pwd')
        self.assertEqual(prop_like.call_count, 4)
        self.assertEqual(prop_eq.call_count, 1)
        prop_like.assert_any_call('dc:title', '%{}%'.format(self.product_type))
        prop_like.assert_any_call('dc:yet_another_thing', '%{}%'.format(self.product_type))
        prop_like.assert_any_call('dc:something', '{}%'.format(self.product_type))
        prop_like.assert_any_call('dc:something_else', '%{}'.format(self.product_type))
        prop_eq.assert_any_call('dc:subject', self.product_type)
        self.assertEqual(mock_catalog.getrecords2.call_count, 5)
        mock_catalog.getrecords2.assert_called_with(
            constraints=mock.ANY,
            esn='full',
            maxrecords=10)

    @mock.patch('eodag.plugins.search.csw.PropertyIsLike', autospec=True)
    @mock.patch('eodag.plugins.search.csw.CatalogueServiceWeb', autospec=True)
    def test_core_csw_search_no_auth_default_version_ok(self, mock_catalogue_web_service, prop_like):
        """A search on a provider implementing CSWSearch without auth and default csw version must succeed"""
        self.override_properties(provider='mock-provider-8', product_type='MOCK_PRODUCT_TYPE_8')
        default_version = '2.0.2'
        dag = SatImagesAPI(providers_file_path=os.path.join(TEST_RESOURCES_PATH, 'mock_providers.yml'))
        mock_catalog = mock_catalogue_web_service.return_value

        mock_catalog.getrecords2.side_effect = functools.partial(self.compute_csw_records, mock_catalog)

        results = dag.search(self.product_type)

        # Catalog service is created only once
        self.assertEqual(mock_catalogue_web_service.call_count, 1)
        self.assertEqual(len(results), 1)
        mock_catalogue_web_service.assert_called_with(
            'http://www.catalog.com/rest/catalog/csw/',
            version=default_version,
            username=None,
            password=None)
        self.assertEqual(prop_like.call_count, 1)
        prop_like.assert_any_call('dc:title', '%{}%'.format(self.product_type))
        self.assertEqual(mock_catalog.getrecords2.call_count, 1)
        mock_catalog.getrecords2.assert_called_with(
            constraints=mock.ANY,
            esn='full',
            maxrecords=10
        )

    @mock.patch('eodag.plugins.search.csw.CatalogueServiceWeb', autospec=True)
    def test_core_csw_search_catalog_init_error_ok(self, mock_catalogue_web_service):
        """A search on a provider implementing CSWSearch must return no result if error during catalog initialisation"""
        self.override_properties(provider='mock-provider-8', product_type='MOCK_PRODUCT_TYPE_8')
        default_version = '2.0.2'
        dag = SatImagesAPI(providers_file_path=os.path.join(TEST_RESOURCES_PATH, 'mock_providers.yml'))
        mock_catalogue_web_service.side_effect = Exception
        mock_catalog = mock_catalogue_web_service.return_value
        results = dag.search(self.product_type)
        self.assertEqual(len(results), 0)
        mock_catalogue_web_service.assert_called_with(
            'http://www.catalog.com/rest/catalog/csw/',
            version=default_version,
            username=None,
            password=None)
        mock_catalog.getrecords2.assert_not_called()

    @mock.patch('eodag.plugins.search.csw.CatalogueServiceWeb', autospec=True)
    def test_core_csw_search_get_records_error_ok(self, mock_catalogue_web_service):
        """A search on a provider implementing CSWSearch must return result even though getrecords fails on some tags"""
        self.override_properties(provider='mock-provider-7', product_type='MOCK_PRODUCT_TYPE_7')
        dag = SatImagesAPI(
            providers_file_path=os.path.join(TEST_RESOURCES_PATH, 'mock_providers.yml'),
            user_conf_file_path=os.path.join(TEST_RESOURCES_PATH, 'mock_user_conf.yml'))
        mock_catalog = mock_catalogue_web_service.return_value
        mock_catalog.getrecords2.side_effect = functools.partial(
            self.compute_csw_records, mock_catalog, raise_error_for='dc:title')
        results = dag.search(self.product_type)
        self.assertEqual(len(results), 4)  # Only the number of results is different from a nominal search
        self.assertEqual(mock_catalog.getrecords2.call_count, 5)
        mock_catalog.getrecords2.assert_called_with(
            constraints=mock.ANY,
            esn='full',
            maxrecords=10)

    @mock.patch('eodag.plugins.search.csw.BBox', autospec=True)
    @mock.patch('eodag.plugins.search.csw.PropertyIsLike', autospec=True)
    @mock.patch('eodag.plugins.search.csw.PropertyIsGreaterThanOrEqualTo', autospec=True)
    @mock.patch('eodag.plugins.search.csw.PropertyIsLessThanOrEqualTo', autospec=True)
    @mock.patch('eodag.plugins.search.csw.CatalogueServiceWeb', autospec=True)
    def test_core_csw_search_start_end_dates_footprint(self, mock_catalogue_web_service, prop_le, prop_ge, prop_like,
                                                       bbox):
        """A search on a provider implementing CSWSearch must correctly interpret date tags and footprint"""
        self.override_properties(provider='mock-provider-8', product_type='MOCK_PRODUCT_TYPE_8')
        params = {'endDate': '2018-05-09', 'startDate': '2018-05-01', 'footprint': self.footprint}
        dag = SatImagesAPI(providers_file_path=os.path.join(TEST_RESOURCES_PATH, 'mock_providers.yml'))
        mock_catalog = mock_catalogue_web_service.return_value
        mock_catalog.getrecords2.side_effect = functools.partial(self.compute_csw_records, mock_catalog)

        results = dag.search(self.product_type, **params)

        self.assertEqual(len(results), 1)
        self.assertEqual(mock_catalog.getrecords2.call_count, 1)
        self.assertEqual(prop_like.call_count, 1)
        prop_like.assert_any_call('dc:title', '%{}%'.format(self.product_type))
        prop_ge.assert_called_with('apiso:TempExtent_begin', params['startDate'])
        prop_le.assert_called_with('apiso:TempExtent_end', params['endDate'])
        bbox.assert_called_with([
            self.footprint['lonmin'], self.footprint['latmin'], self.footprint['lonmax'], self.footprint['latmax']])
        mock_catalog.getrecords2.assert_called_with(
            constraints=mock.ANY,
            esn='full',
            maxrecords=10)

    def test_core_aws_search_ok(self):
        """A search with a product type supported by a provider implementing AwsSearch must succeed"""
        self.override_properties(provider='mock-provider-6', product_type='MOCK_PRODUCT_TYPE_6')
        provider_search_url_base = 'http://subdomain6.domain.eu/resto/api/'  # See ../resources/mock_providers.yml
        comp_date = '2018-05-09'
        resto_results = {
            'features': [{
                'id': 1,
                'geometry': self.geometry,
                'properties': {
                    'productType': 'MOCK6',  # See ../resources/mock_providers.yml
                    'platform': self.platform,
                    'instrument': self.instrument,
                    'completionDate': comp_date,
                    'collection': 'MockCollection6',
                    'productIdentifier': '/eodata/1/{}'.format(self.local_filename),
                    'organisationName': 'ESA',
                    'title': self.local_filename,
                    'snowCover': '',
                    'cloudCover': '',
                    'description': '',
                    'keywords': '',
                    'resolution': '',
                    'startDate': '',
                    'orbitNumber': 0,
                }
            }]
        }
        nominal_params = {
            'startDate': None,
            'cloudCover': '[0,20]',  # See RestoSearch.DEFAULT_MAX_CLOUD_COVER
            'sortOrder': 'descending',
            'sortParam': 'startDate',
            'productType': 'MOCK6'
        }

        requests_http_get_response = self.requests_http_get.return_value
        requests_http_get_response.raise_for_status = mock.MagicMock()
        requests_http_get_response.json = mock.MagicMock(return_value=resto_results)

        dag = SatImagesAPI(providers_file_path=os.path.join(TEST_RESOURCES_PATH, 'mock_providers.yml'))
        results = dag.search(self.product_type)

        self.assertHttpGetCalledOnceWith(
            '{}collections/MockCollection6/search.json'.format(provider_search_url_base),
            expected_params=nominal_params)
        self.assertEqual(requests_http_get_response.raise_for_status.call_count, 1)
        self.assertEqual(requests_http_get_response.json.call_count, 1)

        # Check the search result
        self.assertIsInstance(results, SearchResult)
        self.assertEqual(len(results), len(resto_results['features']))
        for result in results:
            self.assertIsInstance(result, EOProduct)
            self.assertEqual(result.provider, self.provider)
            self.assertEqual(result.location_url_tpl, 'tiles/31/T/DH/2018/5/9/0/')

        # Test that when nothing is found, the returned result is empty
        requests_http_get_response.json = mock.MagicMock(return_value={'features': []})
        results = dag.search(self.product_type)
        self.assertEqual(len(results), 0)


class TestIntegrationCoreDownloadPlugins(unittest.TestCase):

    def test_core_http_download(self):
        """"""

    def test_core_aws_download(self):
        """"""


class TestIntegrationCoreApiPlugins(unittest.TestCase):

    def test_core_usgs_search(self):
        """"""

    def test_core_usgs_download(self):
        """"""

    def test_core_sentinelsat_search(self):
        """"""

    def test_core_sentinelsat_download(self):
        """"""
