#!/usr/bin/env python3
"""
VDF file reader
Copyright (C) 2017 Kozec

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License version 2 as published by
the Free Software Foundation

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""
import os, sys, importlib


def parse_vdf(file):
	# employ arcane rituals to import a better vdf parser
	
	# find system installed vdf package
	locs = sys.path[1:]
	for d in locs:
		if os.path.isdir(d):
			if os.path.isdir(os.path.join(d, 'vdf')):
				vdfpath = os.path.join(d, 'vdf/__init__.py')
				
	if not vdfpath:
		raise ModuleNotFoundError("vdf package not found!")

	# import it
	spec = importlib.util.spec_from_file_location('vdf', vdfpath)
	vdf = importlib.util.module_from_spec(spec)
	sys.modules[spec.name] = vdf
	spec.loader.exec_module(vdf)
	return vdf.parse(file, mapper=vdf.VDFDict, merge_duplicate_keys=False)

def ensure_list(value):
	"""
	If value is list, returns same value.
	Otherwise, returns [ value ]
	"""
	return value if type(value) == list else [ value ]


if __name__ == "__main__":
	print(parse_vdf(open('test.vdf', "r")))

