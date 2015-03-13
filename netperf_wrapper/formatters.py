## -*- coding: utf-8 -*-
##
## formatters.py
##
## Author:   Toke Høiland-Jørgensen (toke@toke.dk)
## Date:     16 October 2012
## Copyright (c) 2012-2015, Toke Høiland-Jørgensen
##
## This program is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program.  If not, see <http://www.gnu.org/licenses/>.

import json, sys, csv, math, inspect, os, re

from .util import cum_prob, frange, classname, long_substr
from .resultset import ResultSet
from .build_info import DATA_DIR, VERSION
from functools import reduce
from itertools import product,cycle,islice
try:
    from itertools import izip_longest as zip_longest
except ImportError:
    from itertools import zip_longest
try:
    from collections import OrderedDict
except ImportError:
    from netperf_wrapper.ordereddict import OrderedDict

def new(settings):
    formatter_name = classname(settings.FORMAT, 'Formatter')
    if not formatter_name in globals():
        raise RuntimeError("Formatter not found: '%s'." % settings.FORMAT)
    try:
        return globals()[formatter_name](settings)
    except Exception as e:
        raise RuntimeError("Error loading %s: %r." % (formatter_name, e))


class Formatter(object):

    open_mode = "w"

    def __init__(self, settings):
        self.settings = settings
        self.check_output(self.settings.OUTPUT)

    def check_output(self, output):
        if hasattr(output, 'read') or output == "-":
            self.output = output
        else:
            # This logic is there to ensure that:
            # 1. If there is no write access, fail before running the tests.
            # 2. If the file exists, do not open (and hence overwrite it) until after the
            #    tests have run.
            if os.path.exists(output):
                # os.access doesn't work on non-existant files on FreeBSD; so only do the
                # access check on existing files (to avoid overwriting them before the tests
                # have completed).
                if not os.access(output, os.W_OK):
                    raise RuntimeError("No write permission for output file '%s'" % output)
                else:
                    self.output = output
            else:
                # If the file doesn't exist, just try to open it immediately; that'll error out
                # if access is denied.
                try:
                    self.output = open(output, self.open_mode)
                except IOError as e:
                    raise RuntimeError("Unable to open output file: '%s'" % e)

    def open_output(self):
        output = self.output
        if hasattr(output, 'read'):
            return
        if output == "-":
            self.output = sys.stdout
        else:
            try:
                self.output = open(output, self.open_mode)
            except IOError as e:
                raise RuntimeError("Unable to output data: %s" % e)

    def format(self, results):
        if results[0].dump_file is not None:
            sys.stderr.write("No output formatter selected.\nTest data is in %s (use with -i to format).\n" % results[0].dump_file)

class NullFormatter(Formatter):
    def check_output(self, output):
        pass
    def format(self, results):
        pass

DefaultFormatter = Formatter

class TableFormatter(Formatter):

    def get_header(self, results):
        name = results[0].meta("NAME")
        keys = list(set(reduce(lambda x,y:x+y, [r.series_names for r in results])))
        header_row = [name]

        if len(results) > 1:
            for r in results:
                header_row += [k + ' - ' + r.label() for k in keys]
        else:
            header_row += keys
        return header_row

    def combine_results(self, results):
        """Generator to combine several result sets into one list of rows, by
        concatenating them."""
        keys = list(set(reduce(lambda x,y:x+y, [r.series_names for r in results])))
        for row in list(zip(*[list(r.zipped(keys)) for r in results])):
            out_row = [row[0][0]]
            for r in row:
                if r[0] != out_row[0]:
                    raise RuntimeError("x-value mismatch: %s/%s. Incompatible data sets?" % (out_row[0], r[0]))
                out_row += r[1:]
            yield out_row


class OrgTableFormatter(TableFormatter):
    """Format the output for an Org mode table. The formatter is pretty crude
    and does not align the table properly, but it should be sufficient to create
    something that Org mode can correctly realign."""

    def format(self, results):
        self.open_output()
        name = results[0].meta("NAME")

        if not results[0]:
            self.output.write(str(name) + " -- empty\n")
            return
        header_row = self.get_header(results)
        self.output.write("| " + " | ".join(header_row) + " |\n")
        self.output.write("|-" + "-+-".join(["-"*len(i) for i in header_row]) + "-|\n")

        def format_item(item):
            if isinstance(item, float):
                return "%.2f" % item
            return str(item)

        for row in self.combine_results(results):
            self.output.write("| ")
            self.output.write(" | ".join(map(format_item, row)))
            self.output.write(" |\n")



class CsvFormatter(TableFormatter):
    """Format the output as csv."""

    def format(self, results):
        self.open_output()
        if not results[0]:
            return

        writer = csv.writer(self.output)
        header_row = self.get_header(results)
        writer.writerow(header_row)

        def format_item(item):
            if item is None:
                return ""
            return str(item)

        for row in self.combine_results(results):
            writer.writerow(list(map(format_item, row)))

class StatsFormatter(Formatter):

    def __init__(self, settings):
        Formatter.__init__(self, settings)
        try:
            import numpy
            self.np = numpy
        except ImportError:
            raise RuntimeError("Stats formatter requires numpy, which seems to be missing. Please install it and try again.")

    def format(self, results):
        self.open_output()
        self.output.write("Warning: Totals are computed as cumulative sum * step size,\n"
                          "so spurious values wreck havoc with the results.\n")
        for r in results:
            self.output.write("Results %s" % r.meta('TIME'))
            if r.meta('TITLE'):
                self.output.write(" - %s" % r.meta('TITLE'))
            self.output.write(":\n")

            for s in sorted(r.series_names):
                self.output.write(" %s:\n" % s)
                d = [i for i in r.series(s) if i]
                if not d:
                    self.output.write("  No data.\n")
                    continue
                cs = self.np.cumsum(d)
                units = self.settings.DATA_SETS[s]['units']
                self.output.write("  Data points: %d\n" % len(d))
                if units != "ms":
                    self.output.write("  Total:       %f %s\n" % (cs[-1]*r.meta('STEP_SIZE'),
                                                               units.replace("/s", "")))
                self.output.write("  Mean:        %f %s\n" % (self.np.mean(d), units))
                self.output.write("  Median:      %f %s\n" % (self.np.median(d), units))
                self.output.write("  Min:         %f %s\n" % (self.np.min(d), units))
                self.output.write("  Max:         %f %s\n" % (self.np.max(d), units))
                self.output.write("  Std dev:     %f\n" % (self.np.std(d)))
                self.output.write("  Variance:    %f\n" % (self.np.var(d)))


class PlotFormatter(Formatter):

    def __init__(self, settings):
        Formatter.__init__(self, settings)
        try:
            from . import plotters
            plotters.init_matplotlib(settings)
            self.plotters = plotters
        except ImportError:
            raise RuntimeError("Unable to plot -- matplotlib is missing! Please install it if you want plots.")

        self.figure = None
        self.init_plots()


    def init_plots(self):
        if self.figure is None:
            self.plotter = self.plotters.new(self.settings)
            self.plotter.init()
            self.figure = self.plotter.figure
        else:
            self.figure.clear()
            self.plotter.disable_cleanup = True
            self.plotter = self.plotters.new(self.settings, self.figure)
            self.plotter.init()

    def _init_timeseries_combine_plot(self, config=None, axis=None):
        self._init_timeseries_plot(config, axis)

    def _init_bar_combine_plot(self, config=None, axis=None):
        self._init_bar_plot(config, axis)

    def _init_box_combine_plot(self, config=None, axis=None):
        self._init_box_plot(config, axis)

    def _init_ellipsis_combine_plot(self, config=None, axis=None):
        self._init_ellipsis_plot(config, axis)

    def _init_cdf_combine_plot(self, config=None, axis=None):
        self._init_cdf_plot(config, axis)

    def do_timeseries_combine_plot(self, results, config=None, axis=None):
        return self.do_combine_many_plot(self.do_timeseries_plot, results, config, axis)

    def do_bar_combine_plot(self, results, config=None, axis=None):
        return self.do_combine_many_plot(self.do_bar_plot, results, config, axis)

    def do_box_combine_plot(self, results, config=None, axis=None):
        self.do_combine_many_plot(self.do_box_plot, results, config, axis)

    def do_ellipsis_combine_plot(self, results, config=None, axis=None):
        self.do_combine_many_plot(self.do_ellipsis_plot, results, config, axis)

    def do_cdf_combine_plot(self, results, config=None, axis=None):
        self.do_combine_many_plot(self.do_cdf_plot, results, config, axis)


    @property
    def disable_cleanup(self):
        return self.plotter.disable_cleanup

    @disable_cleanup.setter
    def disable_cleanup(self, val):
        self.plotter.disable_cleanup = val

    def format(self, results):
        if not results[0]:
            return

        if self.settings.SUBPLOT_COMBINE:
            self.plotter.disable_cleanup = True
            self.figure.clear()
            self.plotter = self.plotters.get_plotter("subplot_combine")(self.settings, self.figure)
            self.plotter.init()
        self.plotter.plot(results)
        self.plotter.save(results)


class MetadataFormatter(Formatter):

    def format(self, results):
        self.open_output()
        self.output.write(json.dumps([r.serialise_metadata() for r in results], indent=4) + "\n")
