# -*- coding: utf-8 -*-
# pheme/transformation/scanreport/renderer.py
# Copyright (C) 2020 Greenbone Networks GmbH
#
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import logging
from typing import Dict
from pathlib import Path
import urllib
import base64

from django.core.cache import cache
from django.template import loader
from django.conf import settings
from rest_framework import renderers
from weasyprint import CSS, HTML

logger = logging.getLogger(__name__)


class DetailScanReport(renderers.BaseRenderer):
    def _get_css(self, name: str) -> CSS:

        background_image = urllib.parse.quote(
            base64.b64encode(
                Path(settings.TEMPLATE_COVER_IMAGE_ADDRESS).read_bytes()
            )
        )

        indicator_image = urllib.parse.quote(
            base64.b64encode(
                Path('/{}/heading.svg'.format(settings.STATIC_DIR)).read_bytes()
            )
        )

        return loader.get_template(name).render(
            {
                'background_image': 'data:image/png;base64,' + background_image,
                'indicator': 'data:image/svg+xml;base64,' + indicator_image,
            }
        )

    def _enrich(self, name: str, data: Dict) -> Dict:
        data['logo'] = settings.TEMPLATE_LOGO_ADDRESS
        data['grouping'] = 'host'
        data['internal_name'] = name
        return data

    def render(self, data, accepted_media_type=None, renderer_context=None):
        renderer_context = renderer_context or {}  # to throw key error
        request = renderer_context['request']
        name = data.get('internal_name')
        cache_key = "{}/{}".format(self.media_type, name) if name else None
        logger.debug("generating report %s", cache_key)

        if cache_key:
            cached = cache.get(cache_key)
            if cached:
                return cached
        result = self.apply(name, data)
        if cache_key:
            cache.set(cache_key, result)
        return result

    def apply(self, name: str, data: Dict):
        raise NotImplementedError(
            'DetailScanReport class requires .apply() to be implemented'
        )


class DetailScanHTMLReport(DetailScanReport):
    __template = 'scan_report.html'
    media_type = 'text/html'
    format = 'html'

    def _enrich(self, name: str, data: Dict) -> Dict:
        data = super()._enrich(name, data)
        data['css'] = self._get_css('html_report.css')
        return data

    def apply(self, name: str, data: Dict):
        return loader.get_template(self.__template).render(
            self._enrich(name, data)
        )


class DetailScanPDFReport(DetailScanReport):
    __template = 'scan_report.html'
    media_type = 'application/pdf'
    format = 'binary'

    def apply(self, name: str, data: Dict):
        logger.debug("got template: %s", self.__template)
        html = loader.get_template(self.__template).render(
            self._enrich(name, data)
        )
        logger.debug("created html")
        css = self._get_css('pdf_report.css')
        pdf = HTML(string=html).write_pdf(stylesheets=[CSS(string=css)])
        logger.debug("created pdf")
        return pdf
