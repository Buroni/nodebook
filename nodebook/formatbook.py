#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ‘ ’
import re
import sys


class formatbook():
    def _I_to_FP(self, line):
        for unquoted_part in line.split('"')[0::2]:
            line = line.replace(unquoted_part, re.sub("(^I | I | I$)", " [FP] ", unquoted_part))
        return line

    def format(self, lines, quoted=True):
        formatted_lines = []
        for line in lines:
            line = line.replace('“','"').replace('”','"')
            if not(quoted):
                line = self._I_to_FP(line)
            formatted_lines.append(line.strip())
        return formatted_lines
