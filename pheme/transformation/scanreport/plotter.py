# pylint: disable=W0614,W0511,W0401,C0103
# -*- coding: utf-8 -*-
# tests/generate_test_data.py
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

import base64
import io
import matplotlib.pyplot as plt

from pheme.transformation.scanreport.model import SeverityOverview, TopTen


class GVMPlotter:
    def __init__(
        self, fig_format: str = 'png', legend_location: str = 'lower right'
    ):
        self.legend_location = legend_location
        self.fig_format = fig_format

    def pie_plot(self, severities: SeverityOverview) -> bytes:
        fig, _ = plt.subplots()
        fig.pie(severities.amounts, labels=severities.names)
        fig.legend(loc=self.legend_location)

        fig_base64 = self.__convert_to_base_64(fig)
        return fig_base64

    def __convert_to_base_64(self, fig) -> bytes:
        fig_bytes = io.BytesIO()
        fig.savefig(fig_bytes, format=self.fig_format)

        fig_bytes.seek(0)
        return base64.b64encode(fig_bytes.read())

    def horizontal_bar_plot(self, top_ten: TopTen):
        pass

    def bar_plot(self, top_ten: TopTen):
        pass
