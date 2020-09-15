# -*- coding: utf-8 -*-
# pheme/transformation/scanreport/gvmd.py
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
from functools import reduce
from typing import Callable, Dict, List
import logging

import pandas as pd
from pandas import DataFrame
from pandas.core.groupby.generic import DataFrameGroupBy


from pheme.transformation.scanreport.model import (
    CommonVulnerabilities,
    CVSSDistributionCount,
    HostCount,
    HostResults,
    NVTCount,
    PortCount,
    QOD,
    Ref,
    Report,
    Result,
    Results,
    Scan,
    SeverityOverview,
    Solution,
    Summary,
    SummaryReport,
    SummaryResults,
    TopTen,
    VulnerabilityOverview,
)


def group_by_host(first: Dict[str, HostResults], second: Dict[str, str]):
    host = second.pop('host')
    host = host if isinstance(host, str) else host.pop("text")
    hr: HostResults = first.get(host)
    nvt = second.pop('nvt')
    solution = (
        Solution(nvt['solution']['type'], nvt['solution']['text'])
        if nvt.get('solution')
        else None
    )
    refs = (
        [Ref(r['id'], r['type']) for r in nvt['refs']['ref']]
        if nvt.get('refs')
        else []
    )
    oid = nvt['oid']
    qod = (
        QOD(
            second['qod']['value'],
            second['qod']['type'],
        )
        if second.get('qod')
        else None
    )
    shr = Result(
        oid,
        nvt.get('type'),
        nvt.get('name'),
        nvt.get('family'),
        nvt.get('cvss_base'),
        nvt.get('tags'),
        solution,
        refs,
        second.get('port'),
        second.get('threat'),
        second.get('severity'),
        qod,
        second.get('description'),
    )
    if hr:
        hr.results.append(shr)
        first[host] = hr
    else:
        first[host] = HostResults(host, [shr])
    del nvt
    return first


logger = logging.getLogger(__name__)


def __create_nvt_top_ten(
    threat: str, group_by_threat: DataFrameGroupBy
) -> TopTen:
    threat = group_by_threat.get_group(threat)
    threat_nvts = threat[['nvt.oid', 'nvt.name']]
    counted = threat_nvts.value_counts()
    return TopTen(
        chart=None,
        top_ten=[
            NVTCount(oid=k[0], amount=v, name=k[1])
            for k, v in counted.head(10).to_dict().items()
        ],
    )


def __create_host_top_ten(result_series_df: DataFrame) -> TopTen:
    threat = result_series_df.get(['host.text', 'host.hostname'])
    if threat is None:
        threat = result_series_df.get(['host.text'])
    if threat is None:
        return None

    counted = threat.value_counts()
    return TopTen(
        chart=None,
        top_ten=[
            HostCount(ip=k[0], amount=v, name=k[1] if len(k) > 1 else None)
            for k, v in counted.head(10).to_dict().items()
        ],
    )


def __create_port_top_ten(result_series_df: DataFrame) -> TopTen:
    threat = result_series_df.get(['port'])
    if threat is None:
        return None
    counted = threat.value_counts()
    return TopTen(
        chart=None,
        top_ten=[
            PortCount(port=k, amount=v)
            for k, v in counted.head(10).to_dict().items()
        ],
    )


def __create_cvss_distribution_port_top_ten(
    result_series_df: DataFrame,
) -> TopTen:
    threat = result_series_df.get(['port', 'nvt.cvss_base'])
    if threat is None:
        return None
    counted = threat.value_counts()
    return TopTen(
        chart=None,
        top_ten=[
            CVSSDistributionCount(identifier=k[0], amount=v, cvss=k[1])
            for k, v in counted.head(10).to_dict().items()
        ],
    )


def __create_cvss_distribution_host_top_ten(
    result_series_df: DataFrame,
) -> TopTen:
    threat = result_series_df.get(
        ['host.text', 'host.hostname', 'nvt.cvss_base']
    )
    if threat is None:
        return None
    counted = threat.value_counts()
    return TopTen(
        chart=None,
        top_ten=[
            CVSSDistributionCount(identifier=k[0], amount=v, cvss=k[1])
            for k, v in counted.head(10).to_dict().items()
        ],
    )


def __create_cvss_distribution_nvt_top_ten(
    result_series_df: DataFrame,
) -> TopTen:
    threat = result_series_df.get(['nvt.oid', 'nvt.cvss_base'])
    if threat is None:
        return None
    counted = threat.value_counts()
    return TopTen(
        chart=None,
        top_ten=[
            CVSSDistributionCount(identifier=k[0], amount=v, cvss=k[1])
            for k, v in counted.head(10).to_dict().items()
        ],
    )


def __create_severity_class_summary(
    df: DataFrame,
) -> SeverityOverview:
    data = df.value_counts()
    return SeverityOverview([x[0] for x in data.index.values], data.values)


def __simple_data_frame_to_values(df: DataFrame) -> List:
    if df is None:
        return []
    return [v[0] for v in df.to_dict().values()]


def __create_scan(
    report: DataFrame,
) -> Scan:
    scan = report.get(
        [
            'task.name',
            'scan_start',
            'scan_end',
            'hosts.count',
            'task.comment',
        ]
    )
    if scan is None:
        return None
    return Scan(*__simple_data_frame_to_values(scan))


def __create_summary_report(report: DataFrame) -> SummaryReport:
    filters = report.get(['filters.term', 'filters.filter', 'timezone'])
    if filters is None:
        return None
    return SummaryReport(*__simple_data_frame_to_values(filters))


def __create_summary_results(report: DataFrame) -> SummaryResults:
    counts = report.get(['result_count.full', 'result_count.filtered'])
    if counts is None:
        return None
    data = __simple_data_frame_to_values(counts)
    if len(data) != 2:
        return None
    data += [None]  # append graph
    return SummaryResults(*data)


def transform(
    data: Dict[str, str], group_by: Callable = group_by_host
) -> Report:
    report = data.pop("report")
    # sometimes gvmd reports have .report.report sometimes just .report
    report = report.pop("report", None) or report

    n_df = pd.json_normalize(report)
    results_series = n_df.get('results.result')
    # pylint: disable=W0108
    result_series_df = results_series.map(lambda x: pd.json_normalize(x)).all()
    common_vulnerabilities = None
    try:
        group_by_threat = result_series_df.groupby('original_threat')

        # severity_overview = __create_severity_class_summary(
        #     result_series_df[['original_threat']]
        # )
        common_vulnerabilities = CommonVulnerabilities(
            __create_nvt_top_ten('High', group_by_threat),
            __create_nvt_top_ten('Medium', group_by_threat),
            __create_nvt_top_ten('Low', group_by_threat),
        )
    except KeyError as e:
        logger.debug('ignoring grouping exception, %s', e)

    vulnerabilities_overview = VulnerabilityOverview(
        __create_host_top_ten(result_series_df),
        None,
        __create_port_top_ten(result_series_df),
        __create_cvss_distribution_port_top_ten(result_series_df),
        __create_cvss_distribution_host_top_ten(result_series_df),
        __create_cvss_distribution_nvt_top_ten(result_series_df),
    )
    summary = Summary(
        __create_scan(n_df),
        __create_summary_report(n_df),
        __create_summary_results(n_df),
    )
    # rewrite with pandas as well
    original_results = report.pop('results')
    grouped = reduce(group_by, original_results.pop("result", []), {})

    logger.info("data transformation; grouped by %s.", group_by)

    return Report(
        report.get('id'),
        summary,
        common_vulnerabilities,
        vulnerabilities_overview,
        Results(0, 0, list(grouped.values())),
    )
