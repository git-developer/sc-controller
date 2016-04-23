#!/usr/bin/env python2
"""
SC Controller - Actions and ActionParser

Action describes what should be done when event from physical controller button,
stick, pad or trigger is generated - typicaly what emulated button, stick or
trigger should be pressed.

ActionParser parses action(s) expressed as string (loaded from JSON file) into
one or more Action instances.
"""
from __future__ import unicode_literals

from tokenize import generate_tokens, TokenError
from collections import namedtuple
from scc.uinput import Keys, Axes, Rels
import token as TokenType
import sys
_ = lambda x : x

MOUSE_BUTTONS = ( Keys.BTN_LEFT, Keys.BTN_MIDDLE, Keys.BTN_RIGHT, Keys.BTN_SIDE, Keys.BTN_EXTRA )
GAMEPAD_BUTTONS = ( Keys.BTN_A, Keys.BTN_B, Keys.BTN_X, Keys.BTN_Y, Keys.BTN_TL, Keys.BTN_TR,
		Keys.BTN_SELECT, Keys.BTN_START, Keys.BTN_MODE, Keys.BTN_THUMBL, Keys.BTN_THUMBR )

class Action(object):
	"""
	Simple action that executes one of predefined methods.
	See ACTIONS for list of them.
	"""
	# Used everywhere to convert strings to Action classes and back
	COMMAND = None
	
	# "Action Context" constants used by describe method
	AC_BUTTON = 1
	AC_STICK = 2
	AC_TRIGGER = 3
	AC_PAD = 4
	
	def __init__(self, parameters):
		self.parameters = parameters
	
	
	def describe(self, context):
		"""
		Returns string that describes what action does in human-readable form.
		Used in GUI.
		"""
		return str(self)
	
	
	def to_string(self, multiline=False):
		""" Converts action back to string """
		return "%s(%s)" % (self.COMMAND, ", ".join([ str(x) for x in self.parameters ]))
	
	
	def execute(self, event):
		return getattr(event, self.COMMAND)(*self.parameters)
	
	
	def __str__(self):
		return "<Action '%s', %s>" % (self.COMMAND, self.parameters)
	
	__repr__ = __str__


class AxisAction(Action):
	COMMAND = "axis"
	
	AXIS_NAMES = {
		Axes.ABS_X : ("LStick", "Left", "Right"),
		Axes.ABS_Y : ("LStick", "Up", "Down"),
		Axes.ABS_RX : ("RStick", "Left", "Right"),
		Axes.ABS_RY : ("RStick", "Up", "Down"),
		Axes.ABS_HAT0X : ("DPAD", "Left", "Right"),
		Axes.ABS_HAT0Y : ("DPAD", "Up", "Down"),
		Axes.ABS_Z  : ("Left Trigger", "Press", "Press"),
		Axes.ABS_RZ : ("Right Trigger", "Press", "Press"),
	}
	X = [ Axes.ABS_X, Axes.ABS_RX, Axes.ABS_HAT0X ]
	Z = [ Axes.ABS_Z, Axes.ABS_RZ ]
	
	def _get_axis_description(self):
		axis, neg, pos = "%s %s" % (self.parameters[0].name, _("Axis")), _("Negative"), _("Positive")
		if self.parameters[0] in AxisAction.AXIS_NAMES:
			axis, neg, pos = [ _(x) for x in AxisAction.AXIS_NAMES[self.parameters[0]] ]
		return axis, neg, pos
	
	def describe(self, context):
		axis, neg, pos = self._get_axis_description()
		if context == Action.AC_BUTTON:
			for x in self.parameters:
				if type(x) in (int, float):
					if x > 0:
						return "%s %s" % (axis, pos)
					if x < 0:
						return "%s %s" % (axis, neg)
		if context in (Action.AC_TRIGGER, Action.AC_STICK, Action.AC_PAD):
			if self.parameters[0] in AxisAction.Z: # Trigger
				return axis
			else:
				xy = "X" if self.parameters[0] in AxisAction.X else "Y"
				return "%s %s" % (axis, xy)
		return axis


class RAxisAction(AxisAction):
	COMMAND = "raxis"
	def describe(self, context):
		axis, neg, pos = self._get_axis_description()
		if context in (Action.AC_STICK, Action.AC_PAD):
			xy = "X" if self.parameters[0] in AxisAction.X else "Y"
			return _("%s %s (reversed)") % (axis, xy)
		return _("Reverse %s Axis") % (axis,)

class HatAction(AxisAction):
	COMMAND = None
	def describe(self, context):
		axis, neg, pos = self._get_axis_description()
		if "up" in self.COMMAND or "left" in self.COMMAND:
			return "%s %s" % (axis, neg)
		else:
			return "%s %s" % (axis, pos)
	

class HatUpAction(HatAction): COMMAND = "hatup"
class HatDownAction(HatAction): COMMAND = "hatdown"
class HatLeftAction(HatAction): COMMAND = "hatleft"
class HatRightAction(HatAction): COMMAND = "hatright"

class MouseAction(Action):
	COMMAND = "mouse"
	def describe(self, context):
		if self.parameters[0] == Rels.REL_WHEEL:
			return _("Wheel")
		elif self.parameters[0] == Rels.REL_HWHEEL:
			return _("Horizontal Wheel")
		else:
			return _("Mouse %s") % (self.parameters[0].name.split("_", 1)[-1],)


class MacroAction(Action):
	COMMAND = "macro"


class ChangeProfileAction(Action):
	COMMAND = "profile"
	
	def describe(self, context):
		return _("Profile Change")
	
	
	def to_string(self, multiline=False):
		""" Converts action back to string """
		return "%s('%s')" % (self.COMMAND, self.parameters[0].encode('string_escape'))


class TrackpadAction(Action):
	COMMAND = "trackpad"
	def describe(self, context):
		return "Trackpad"


class TrackballAction(Action):
	COMMAND = "trackball"
	def describe(self, context):
		return "Trackball"


class ButtonAction(Action):
	COMMAND = "button"
	SPECIAL_NAMES = {
		Keys.BTN_LEFT	: "Mouse Left",
		Keys.BTN_MIDDLE	: "Mouse Middle",
		Keys.BTN_RIGHT	: "Mouse Right",
		Keys.BTN_SIDE	: "Mouse 8",
		Keys.BTN_EXTRA	: "Mouse 9",

		Keys.BTN_TR		: "Right Bumper",
		Keys.BTN_TL		: "Left Bumper",
		Keys.BTN_THUMBL	: "LStick Click",
		Keys.BTN_THUMBR	: "RStick Click",
		Keys.BTN_START	: "Start >",
		Keys.BTN_SELECT	: "< Select",
		Keys.BTN_A		: "A Button",
		Keys.BTN_B		: "B Button",
		Keys.BTN_X		: "X Button",
		Keys.BTN_Y		: "Y Button",
	}

	def describe(self, context):
		p = self.parameters[0]
		if p in ButtonAction.SPECIAL_NAMES:
			return _(ButtonAction.SPECIAL_NAMES[p])
		elif p == Rels.REL_WHEEL:
			if len(self.parameters) < 2 or self.parameters[1] > 0:
				return _("Wheel UP")
			else:
				return _("Wheel DOWN")
		elif p in MOUSE_BUTTONS:
			return _("Mouse %s") % (p,)
		else:
			return p.name.split("_", 1)[-1]


class ClickAction(Action):
	COMMAND = "click"
	def describe(self, context):
		return _("(if pressed)")


class MultiAction(object):
	"""
	Two or more actions executed in sequence.
	Generated when parsing ';'
	"""
	COMMAND = None

	def __init__(self, *actions):
		self.actions = []
		self._add_all(actions)


	def _add_all(self, actions):
		for x in actions:
			if type(x) == list:
				self._add_all(x)
			else:
				self._add(x)


	def _add(self, action):
		if action.__class__ == self.__class__:	# I don't wan't subclasses here
			self._add_all(action.actions)
		else:
			self.actions.append(action)


	def describe(self, context):
		"""
		Returns string that describes what action does in human-readable form.
		Used in GUI.
		"""
		return self.actions[0].describe(context)


	def execute(self, event):
		rv = False
		for a in self.actions:
			rv = a.execute(event)
		return rv
	
	
	def to_string(self, multiline=False):
		return "; ".join([ x.to_string() for x in self.actions ])
	
	
	def __str__(self):
		return "<[ %s ]>" % ("; ".join([ str(x) for x in self.actions ]), )

	__repr__ = __str__


class DPadAction(MultiAction):
	COMMAND = "dpad"
	
	def describe(self, context):
		return "DPad"
	
	def execute(self, event):
		return getattr(event, self.COMMAND)(*self.actions)
	
	def to_string(self, multiline=False):
		if multiline:
			rv = [ "dpad(" ]
			for a in self.actions:
				rv += [ "  " + a.to_string(False) + ","]
			if rv[-1].endswith(","):
				rv[-1] = rv[-1][0:-1]
			rv += [ ")" ]
			return "\n".join(rv)
		return "dpad(" + (", ".join([
			x.to_string() if x is not None else "None"
			for x in self.actions
		])) + ")"


class LinkedActions(MultiAction):
	"""
	Two actions linked together.
	Action 2 is executed only if action 1 returns True - currently used only
	with 'click' action that returns True only if pad or stick is pressed.
	"""
	COMMAND = None

	def execute(self, event):
		for x in self.actions:
			if not x.execute(event): return False
		return True


	def describe(self, context):
		"""
		Returns string that describes what action does in human-readable form.
		Used in GUI.
		"""
		return self.actions[0].describe(context)
	
	
	def to_string(self, multiline=False):
		return " and ".join([ x.to_string() for x in self.actions ])
	
	
	def __str__(self):
		return "< %s >" % (" and ".join([ str(x) for x in self.actions ]), )

	__repr__ = __str__


class XYAction(MultiAction):
	"""
	Used internaly to store actions for X and Y axis at once.
	Shouldn't be saved into profile or weird stuff may happen.
	"""
	COMMAND = "XY"

	def execute(self, event):
		raise Exception("XYAction cannot be executed")


	def describe(self, context):
		return self.actions[0].describe(context)
	
	
	def to_string(self, multiline=False):
		if multiline:
			rv = []
			i = 0
			for a in self.actions[0:2]:
				if i == 0:
					rv += [ "X:" ]
				elif i == 1:
					rv += [ "Y:" ]
				i += 1
				rv += [ "  " + x for x in a.to_string(True).split("\n") ]
			return "\n".join(rv)
			
		return "XY(" + (", ".join([ x.to_string() for x in self.actions ])) + ")"
	
	
	def __str__(self):
		return "<XY %s >" % (", ".join([ str(x) for x in self.actions ]), )

	__repr__ = __str__


class NoAction(Action):
	"""
	Parsed from None
	"""
	COMMAND = None

	def execute(self, event):
		pass
	
	
	def describe(self, context):
		return _("(not set)")
	
	
	def to_string(self, multiline=False):
		return "None"
	
	
	def __str__(self):
		return "NoAction"

	__repr__ = __str__


class ParseError(Exception): pass


class ActionParser(object):
	"""
	Parses action expressed as string into Action instances.

	Usage:
		ap = ActionParser(string)
		action = ap.parse()
		if action is None:
			error = ap.get_error()
			# do something with error
	"""
	Token = namedtuple('Token', 'type value')

	CONSTS = {
		'Keys' : Keys,
		'Axes' : Axes,
		'Rels' : Rels,
		'None' : NoAction([]),
	}

	def __init__(self, string=""):
		self.restart(string)


	def restart(self, string):
		"""
		Restarts parsing with new string
		Returns self for chaining.
		"""

		try:
			self.tokens = [
				ActionParser.Token(type, string)
				for (type, string, trash, trash, trash)
				in generate_tokens( iter([string]).next )
				if type != TokenType.ENDMARKER
			]
		except TokenError:
			self.tokens = None
		self.index = 0
		return self


	def _next_token(self):
		rv = self.tokens[self.index]
		self.index += 1
		return rv


	def _peek_token(self):
		""" As _next_token, but without increasing counter """
		return self.tokens[self.index]


	def _tokens_left(self):
		""" Returns True if there are any tokens left """
		return self.index < len(self.tokens)


	def _parse_parameter(self):
		""" Parses single parameter """
		t = self._next_token()
		while t.type == TokenType.NEWLINE or t.value == "\n":
			if not self._tokens_left():
				raise ParseError("Excepted parameter at end of string")
			t = self._next_token()
		
		if t.type == TokenType.NAME:
			# Constant or action used as parameter
			if self._tokens_left() and self._peek_token().type == TokenType.OP and self._peek_token().value == '(':
				# Action used as parameter
				self.index -= 1 # go step back and reparse as action
				parameter = self._parse_action()
			else:
				# Constant
				if not t.value in ActionParser.CONSTS:
					raise ParseError("Excepted parameter, got '%s' which is not defined" % (t.value,))
				parameter = ActionParser.CONSTS[t.value]

			# Check for dots
			while self._tokens_left() and self._peek_token().type == TokenType.OP and self._peek_token().value == '.':
				self._next_token()
				if not self._tokens_left():
					raise ParseError("Excepted NAME after '.'")

				t = self._next_token()
				if not hasattr(parameter, t.value):
					raise ParseError("%s has no attribute '%s'" % (parameter, t.value,))
				parameter = getattr(parameter, t.value)
			return parameter

		if t.type == TokenType.OP and t.value == "-":
			if not self._tokens_left() or self._peek_token().type != TokenType.NUMBER:
				raise ParseError("Excepted number after '-'")
			return - self._parse_number()


		if t.type == TokenType.NUMBER:
			self.index -= 1
			return self._parse_number()
		
		if t.type == TokenType.STRING:
			return t.value[1:-1].decode('string_escape')
		
		raise ParseError("Excepted parameter, got '%s'" % (t.value,))


	def _parse_number(self):
		t = self._next_token()
		if t.type != TokenType.NUMBER:
			raise ParseError("Excepted number, got '%s'" % (t.value,))
		if "." in t.value:
			return float(t.value)
		elif "e" in t.value.lower():
			return float(t.value)
		elif t.value.lower().startswith("0x"):
			return int(t.value, 16)
		elif t.value.lower().startswith("0b"):
			return int(t.value, 2)
		else:
			return int(t.value)


	def _parse_parameters(self):
		""" Parses parameter list """
		# Check and skip over '('
		t = self._next_token()
		if t.type != TokenType.OP or t.value != '(':
			raise ParseError("Excepted '(' of parameter list, got '%s'" % (t.value,))

		parameters = []
		while self._tokens_left():
			# Check for ')' that would end parameter list
			t = self._peek_token()
			if t.type == TokenType.OP and t.value == ')':
				self._next_token()
				return parameters

			# Parse one parameter
			parameters.append(self._parse_parameter())
			# Check if next token is either ')' or ','
			t = self._peek_token()
			while t.type == TokenType.NEWLINE or t.value == "\n":
				self._next_token()
				if not self._tokens_left():
					raise ParseError("Excepted ',' or end of parameter list after parameter '%s'" % (parameters[-1],))
				t = self._peek_token()
			if t.type == TokenType.OP and t.value == ')':
				pass
			elif t.type == TokenType.OP and t.value == ',':
				self._next_token()
			else:
				raise ParseError("Excepted ',' or end of parameter list after parameter '%s'" % (parameters[-1],))


		# Code shouldn't reach here, unless there is not closing ')' in parameter list
		raise ParseError("Unmatched parenthesis")


	def _parse_action(self):
		"""
		Parses one action, that is one of:
		 - something(params)
		 - something()
		 - something
		"""
		# Check if next token is TokenType.NAME and grab action name from it
		t = self._next_token()
		if t.type != TokenType.NAME:
			raise ParseError("Excepted action name, got '%s'" % (t.value,))
		if t.value not in ACTIONS:
			raise ParseError("Unknown action '%s'" % (t.value,))
		action_name = t.value
		action_class = ACTIONS[action_name]

		# Check if there are any tokens left - return action without parameters
		# if not
		if not self._tokens_left():
			return action_class([])

		# Check if token after action name is parenthesis and if yes, parse
		# parameters from it
		t = self._peek_token()
		parameters = []
		if t.type == TokenType.OP and t.value == '(':
			parameters  = self._parse_parameters()
			if not self._tokens_left():
				return action_class(parameters)
			t = self._peek_token()

		# ... or, if it is one of ';', 'and' or 'or' and if yes, parse next action
		if t.type == TokenType.NAME and t.value == 'and':
			# Two (or more) actions joined by 'and'
			self._next_token()
			if not self._tokens_left():
				raise ParseError("Excepted action after 'and'")
			action1 = action_class(parameters)
			action2 = self._parse_action()
			return LinkedActions(action1, action2)
		
		if t.type == TokenType.NEWLINE or (t.type == TokenType.OP and t.value == ';'):
			# Two (or more) actions joined by ';'
			self._next_token()
			while self._tokens_left() and self._peek_token().type == TokenType.NEWLINE:
				self._next_token()
			if not self._tokens_left():
				# Having ';' at end of string is not actually error
				return action_class(parameters)
			action1 = action_class(parameters)
			action2 = self._parse_action()
			return MultiAction(action1, action2)

		return action_class(parameters)


	def parse(self):
		"""
		Returns parsed action.
		Throws ParseError if action cannot be parsed.
		"""
		if self.tokens == None:
			raise ParseError("Syntax error")
		a = self._parse_action()
		if self._tokens_left():
			raise ParseError("Unexpected '%s'" % (self._next_token().value, ))
		return a


class TalkingActionParser(ActionParser):
	"""
	ActionParser that returns None when parsing fails instead of
	trowing exception and outputs message to stderr
	"""

	def restart(self, string):
		self.string = string
		return ActionParser.restart(self, string)


	def parse(self):
		"""
		Returns parsed action or None if action cannot be parsed.
		"""
		try:
			return ActionParser.parse(self)
		except ParseError, e:
			print >>sys.stderr, "Warning: Failed to parse '%s':" % (self.string,), e


# Generate dict of { 'actionname' : ActionClass } for later use
ACTIONS = {
	globals()[x].COMMAND : globals()[x]
	for x in dir()
	if hasattr(globals()[x], 'COMMAND')
	and globals()[x].COMMAND is not None
}