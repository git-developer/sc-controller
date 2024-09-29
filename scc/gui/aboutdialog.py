"""SC-Controller - About dialog."""
from scc.gui.editor import Editor


class AboutDialog(Editor):
	"""Standard looking about dialog."""

	GLADE = "about.glade"

	def __init__(self, app) -> None:
		self.app = app
		self.setup_widgets()


	def setup_widgets(self) -> None:
		"""Setup widgets and get and set app version in the About.

		TODO - We can get a mismatch like this and version won't be set then, why?:
			location:     /usr/lib/python3.12/site-packages
			scc.__file__: /home/user/sc-controller/scc/__init__.py
		"""
		Editor.setup_widgets(self)

		app_ver = "(unknown version)"
		import pkg_resources

		import scc
		sccontroller_module = pkg_resources.require("sccontroller")[0]
		if sccontroller_module.location is not None:
			if scc.__file__.startswith(sccontroller_module.location):
				app_ver = "v" + sccontroller_module.version
			else:
				print(
					"Could not get version, locations possibly could not match.",
					f"scc.__file__:{scc.__file__}",
					f"sccontroller_module.location: {sccontroller_module.location}",
					f"sccontroller_module.version: {sccontroller_module.version}",
					f"sccontroller_module: {sccontroller_module}")
		# Display version in UI
		self.builder.get_object("lblVersion").set_label(app_ver)


	def show(self, modal_for) -> None:
		if modal_for:
			self.window.set_transient_for(modal_for)
			self.window.set_modal(True)
		self.window.show()


	def on_dialog_response(self, *a) -> None:
		self.close()
