## -*- mode: python; coding: utf-8 -*-

# Mixin include file to add wifi stats to a test


WIFI_STATS_HOSTS=TEST_PARAMETERS.get('wifi_stats_hosts')
WIFI_STATS_IFACES=TEST_PARAMETERS.get('wifi_stats_interfaces')
WIFI_STATS_STATIONS=TEST_PARAMETERS.get('wifi_stats_stations')
if WIFI_STATS_HOSTS:
    for host,iface in zip(WIFI_STATS_HOSTS.split(","), WIFI_STATS_IFACES.split(",")):
        DATA_SETS['wifi_stats_%s' % host] = {'command': find_wifistats_iterate(iface, STEP_SIZE, TOTAL_LENGTH, host),
                                             'stations': WIFI_STATS_STATIONS.split(","),
                                             'units': 'misc',
                                             'runner': 'wifi_stats',}
        for station in WIFI_STATS_STATIONS.split(","):
            DATA_SETS['wifi_stats_%s::airtime_rx::%s' % (host,station)] = {'units': 'us', 'data_transform': 'cumulative_to_events',
                                                                           'runner': 'null', 'id': "%s::%s" % (host, station), 'parent_id' : host}
            DATA_SETS['wifi_stats_%s::airtime_tx::%s' % (host,station)] = {'units': 'us', 'data_transform': 'cumulative_to_events',
                                                                           'runner': 'null', 'id': "%s::%s" % (host, station), 'parent_id' : host}
            DATA_SETS['wifi_stats_%s::airtime_total::%s' % (host,station)] = {'units': 'us', 'apply_to': ['wifi_stats_%s::airtime_rx::%s' % (host,station),
                                                                                                          'wifi_stats_%s::airtime_tx::%s' % (host,station),],
                                                                              'runner': 'sum', 'id': "%s::%s" % (host, station), 'parent_id' : host}
            DATA_SETS['wifi_stats_%s::avg_aggr_size::%s' % (host,station)] = {'units': 'packets',
                                                                              'runner': 'null', 'id': "%s::%s" % (host, station), 'parent_id' : host}

        DATA_SETS['wifi_stats_%s::airtime_sum' % host] = {'units': 'us', 'apply_to': [glob('wifi_stats_%s::airtime_rx::**' % host),
                                                                                      glob('wifi_stats_%s::airtime_tx::**' % host),],
                                                          'runner': 'sum', 'id': host}
        DATA_SETS['wifi_stats_%s::airtime_fairness' % host] = {'units': 'us', 'apply_to': [glob('wifi_stats_%s::airtime_total::*' % host)],
                                                               'runner': 'fairness', 'id': host}

    PLOTS['airtime_rx'] = {'description': 'WiFi RX airtime',
                           'type': 'timeseries',
                           'axis_labels': ['Microseconds'],
                           'legend_title': 'RX airtime',
                           'series': [
                               {'data': glob('wifi_stats_*::airtime_rx::**'),
                                'label': 'RX airtime'},
                           ]}
    PLOTS['airtime_rx_combine'] = {'description': 'Combined airtime RX plot (short timescale)',
                                   'parent': 'airtime_rx',
                                   'type': 'box_combine',
                                   'cutoff': (DELAY,DELAY),
                                   'group_by': 'groups_concat'}
    PLOTS['airtime_rx_combine_long'] = {'description': 'Combined airtime RX plot (long timescale)',
                                        'parent': 'airtime_rx',
                                        'type': 'box_combine',
                                        'cutoff': (DELAY,DELAY),
                                        'group_by': 'groups'}
    PLOTS['airtime_tx'] = {'description': 'WiFi TX airtime',
                           'type': 'timeseries',
                           'axis_labels': ['Microseconds'],
                           'legend_title': 'TX airtime',
                           'series': [
                               {'data': glob('wifi_stats_*::airtime_tx::**'),
                                'label': 'TX airtime'},
                           ]}
    PLOTS['airtime_tx_combine'] = {'description': 'Combined airtime TX plot (short timescale)',
                                   'parent': 'airtime_tx',
                                   'type': 'box_combine',
                                   'cutoff': (DELAY,DELAY),
                                   'group_by': 'groups_concat'}
    PLOTS['airtime_tx_combine_long'] = {'description': 'Combined airtime TX plot (long timescale)',
                                        'parent': 'airtime_tx',
                                        'type': 'box_combine',
                                        'cutoff': (DELAY,DELAY),
                                        'group_by': 'groups'}
    PLOTS['airtime'] = {'description': 'WiFi airtime',
                        'type': 'meta',
                        'subplots': ('airtime_rx', 'airtime_tx')}

    PLOTS['airtime_rx_stacked'] = {'description': 'WiFi RX airtime (stacked)',
                           'parent': 'airtime_rx',
                           'stacked': True}
    PLOTS['airtime_tx_stacked'] = {'description': 'WiFi TX airtime (stacked)',
                           'parent': 'airtime_tx',
                           'stacked': True}
    PLOTS['airtime_stacked'] = {'description': 'WiFi airtime (stacked)',
                        'type': 'meta',
                        'subplots': ('airtime_rx_stacked', 'airtime_tx_stacked')}
    PLOTS['airtime_total'] = {'description': 'WiFi total airtime (TX+RX sum)',
                           'type': 'timeseries',
                           'axis_labels': ['Microseconds'],
                           'legend_title': 'Total airtime',
                           'series': [
                               {'data': glob('wifi_stats_*::airtime_total::**'),
                                'label': 'Total airtime'},
                           ]}
    PLOTS['airtime_total_stacked'] = {'description': 'WiFi total airtime (stacked)',
                           'parent': 'airtime_total',
                           'stacked': True}
    PLOTS['airtime_total_combine'] = {'description': 'Combined airtime total plot',
                                      'type': 'box_combine',
                                      'axis_labels': ['Airtime share'],
                                      'cutoff': (DELAY,DELAY),
                                      'group_by': 'groups_concat',
                                      'series': [
                                          {'data': glob('wifi_stats_*::airtime_total::**'),
                                           'label': 'Total airtime',
                                           'norm_by': 'wifi_stats_{parent_id}::airtime_sum'},
                                      ]}
    PLOTS['airtime_total_combine_long'] = {'description': 'Combined airtime total plot (long timescale)',
                                   'parent': 'airtime_total_combine',
                                   'group_by': 'groups'}
    PLOTS['airtime_fairness_combine'] = {'description': 'Combined airtime fairness plot',
                                         'type': 'box_combine',
                                         'axis_labels': ['Fairness index'],
                                         'cutoff': (DELAY,DELAY),
                                         'series': [
                                             {'data': glob('wifi_stats_*::airtime_fairness'),
                                              'source': glob('wifi_stats_{id}::airtime_total::**'),
                                              'label': 'Airtime fairness',
                                              'combine_mode': 'fairness_mean'},
                                         ],
                                         'group_by': 'groups_concat'}
    PLOTS['airtime_fairness_combine_bar'] = {'description': 'Combined airtime fairness bar plot',
                                         'type': 'bar_combine',
                                         'axis_labels': ['Fairness index'],
                                         'cutoff': (DELAY,DELAY),
                                         'series': [
                                             {'data': glob('wifi_stats_*::airtime_fairness'),
                                              'source': glob('wifi_stats_{id}::airtime_total::**'),
                                              'label': 'Airtime fairness',
                                              'combine_mode': 'fairness_mean'},
                                         ],
                                         'group_by': 'groups_concat'}
    PLOTS['airtime_fairness_combine_tx'] = {'description': 'Combined TX airtime fairness plot',
                                            'parent': 'airtime_fairness_combine',
                                            'series': [
                                             {'data': glob('wifi_stats_*::airtime_fairness'),
                                              'source': glob('wifi_stats_{id}::airtime_tx::**'),
                                              'label': 'Airtime TX fairness',
                                              'combine_mode': 'fairness_mean'}]}
    PLOTS['airtime_sum'] = {'description': 'WiFi airtime (all stations)',
                            'type': 'timeseries',
                            'axis_labels': ['Microseconds'],
                            'legend_title': 'Airtime sum',
                            'series': [
                                {'data': glob('wifi_stats_*::airtime_sum'),
                                 'label': 'Airtime sum'},
                            ]}
    PLOTS['airtime_sum_combine'] = {'description': 'Combined airtime sum plot',
                                    'parent': 'airtime_sum',
                                    'type': 'box_combine',
                                    'cutoff': (DELAY,DELAY),
                                    'group_by': 'groups_concat'}
    PLOTS['aggregation'] = {'description': 'WiFi aggregation size',
                           'type': 'timeseries',
                           'axis_labels': ['Packets'],
                           'legend_title': 'Avg aggregation size',
                           'series': [
                               {'data': glob('wifi_stats_*::avg_aggr_size::**'),
                                'label': 'Aggr size'},
                           ]}
    PLOTS['aggregation_combine'] = {'description': 'Combined aggregation size plot',
                                   'parent': 'aggregation',
                                   'type': 'box_combine',
                                   'cutoff': (DELAY,DELAY),
                                   'group_by': 'groups_concat'}
