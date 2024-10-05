"""SC-Controller - Global Settings.

Currently setups only one thing...
"""
from __future__ import annotations
import collections
import logging
import os
import threading
from io import StringIO

from gi.repository import Gdk, GObject, GLib

from scc.foreign.vdf import VDFProfile
from scc.foreign.vdffz import VDFFZProfile
from scc.lib.vdf import parse_vdf
from scc.tools import _, get_profiles_path

log = logging.getLogger("IE.ImportVdf")

class ImportVdf(object):
	PROFILE_LIST = "config/localconfig.vdf"
	STEAMPATH = "~/.steam/steam/"

	def __init__(self) -> None:
		self._profile = None
		self._lstVdfProfiles = self.builder.get_object("tvVdfProfiles").get_model()
		self._q_games    = collections.deque()
		self._q_profiles = collections.deque()
		self._s_games    = threading.Semaphore(0)
		self._s_profiles = threading.Semaphore(0)
		self._lock = threading.Lock()
		self.__profile_load_started = False
		self._on_preload_finished = None

	def on_grVdfImport_activated(self, *a) -> None:
		if not self.__profile_load_started:
			self.__profile_load_started = True
			threading.Thread(target=self._load_profiles).start()
			threading.Thread(target=self._load_game_names).start()
			threading.Thread(target=self._load_profile_names).start()
		self.on_tvVdfProfiles_cursor_changed()


	def _load_profiles(self) -> None:
		"""Search for file containing list of profiles and read it.

		This is done in thread, with crazy hope that it will NOT crash GTK in the process.
		"""
		p = os.path.join(os.path.expanduser(self.STEAMPATH), "userdata")
		if os.path.exists(p):
			for user in os.listdir(p):
				profilelist = os.path.join(p, user, self.PROFILE_LIST)
				if os.path.isfile(profilelist):
					self._lock.acquire()
					log.debug("Loading profile list from '%s'", profilelist)
					try:
						self._parse_profile_list(profilelist, user)
					except Exception as e:
						log.exception(e)
					self._lock.release()
		GLib.idle_add(self._load_finished)

	def _parse_profile_list(self, filename: str, userid: str) -> None | int:
		"""Parse localconfig.vdf and load game and profile IDs. That is later decoded into name of game and profile name.

		Called from _load_profiles, in thread. Exceptions are catched and logged from there.
		Calls GLib.idle_add to send loaded data into UI.
		"""
		# VDF file is a ISO-8859-1 encoded file. Not UTF-8
		data = parse_vdf(open(filename, "r", encoding = "ISO-8859-1"))
		# Sanity check
		if "UserLocalConfigStore" not in data:
			return
		if "controller_config" not in data["UserLocalConfigStore"]:
			return

		# Grab config - currently only grabs SC configs!
		cc = data["UserLocalConfigStore"]["controller_config"][userid]["controller_steamcontroller_gordon"]["DEFAULT_FOR_TYPE"]
		# Go through all games
		listitems = []
		i = 0
		for gameid in cc:
			# skip templates
			if 'selected' not in cc[gameid]:
				continue

			if not self._check_for_app_manifest(gameid):
				continue

			profile_id = cc[gameid]["selected"]
			listitems.append(( i, gameid, profile_id, None ))
			i += 1
			if len(listitems) > 10:
				GLib.idle_add(self.fill_list, listitems)
				listitems = []

		GLib.idle_add(self.fill_list, listitems)
		return i

	def _check_for_app_manifest(self, gameid: int) -> bool:
		"""Check if an app manifest exists for a game.

		It seems like a better idea to only worry about importing configs for games the user already has installed.
		"""
		sa_path = self._find_steamapps()
		if sa_path is None:
			return False
		filename = os.path.join(sa_path, "appmanifest_%s.acf" % (gameid))
		return os.path.exists(filename)


	def _load_game_names(self) -> None:
		"""Load names for game ids in q_games.

		This is done in thread (not in same thread as _load_profiles),
		because it involves searching for apropriate file and parsing it
		entirely.

		Calls GLib.idle_add to send loaded data into UI.
		"""
		sa_path = self._find_steamapps()
		if sa_path is None:
			return
		while True:
			self._s_games.acquire(True) # Wait until something is added to the queue
			try:
				index, gameid = self._q_games.popleft()
			except IndexError:
				break
			if gameid.isdigit():
				name = _("Unknown App ID %s") % (gameid)
				filename = os.path.join(sa_path, "appmanifest_%s.acf" % (gameid,))
				self._lock.acquire()
				if os.path.exists(filename):
					try:
						data = parse_vdf(open(filename, "r"))
						name = data['AppState']['name']
					except Exception as e:
						log.error("Failed to load app manifest for '%s'", gameid)
						log.exception(e)
				else:
					log.warning("Skiping non-existing app manifest '%s'", filename)
				self._lock.release()
			else:
				name = gameid
			GLib.idle_add(self._set_game_name, index, name)


	@staticmethod
	def _find_legacy_bin(path) -> str | None:
		"""Search specified folder for any file ending in '_legacy.bin'.

		and returns full path to first matching file.
		Returns None if path doesn't point to directory or there is
		no such file.
		"""
		if os.path.exists(path):
			for f in os.listdir(path):
				if f.endswith("_legacy.bin"):
					return os.path.join(path, f)
		return None


	def _load_profile_names(self) -> None:
		"""Load names for profiles ids in q_profiles.

		This is same as _load_game_names, but for profiles.
		"""
		steam_apps_dir = self._find_steamapps()
		if steam_apps_dir is None:
			return
		content_path = os.path.join(steam_apps_dir, "workshop/content")
		if not os.path.exists(content_path):
			log.warning("Cannot find '%s'; Cannot import anything without it", content_path)
			return
		while True:
			self._s_profiles.acquire(True)	# Wait until something is added to the queue
			try:
				index, gameid, profile_id = self._q_profiles.popleft()
			except IndexError:
				break
			self._lock.acquire()
			for user in os.listdir(content_path):
				filename = os.path.join(content_path, user, profile_id, "controller_configuration.vdf")
				if not os.path.exists(filename):
					# If there is no 'controller_configuration.vdf', try finding *_legacy.bin
					filename = self._find_legacy_bin(os.path.join(content_path, user, profile_id))
				if not filename or not os.path.exists(filename):
					# If not even *_legacy.bin is found, skip to next user
					continue
				log.info("Reading '%s'", filename)
				try:
					data = parse_vdf(open(filename, "r"))
					name = data['controller_mappings']['title']
					GLib.idle_add(self._set_profile_name, index, name, filename)
					break
				except Exception as e:
					log.error("Failed to read profile name from '%s'", filename)
					log.exception(e)
			else:
				log.warning("Profile %s for game %s not found.", profile_id, gameid)
				name = _("(not found)")
				GLib.idle_add(self._set_profile_name, index, name, None)
			self._lock.release()

	def _load_finished(self) -> None:
		"""Called in main thread after _load_profiles is finished."""
		self.builder.get_object("rvLoading").set_reveal_child(False)
		self.loading = False
		self._s_games.release()
		self._s_profiles.release()
		if self._on_preload_finished:
			cb, data = self._on_preload_finished
			GLib.idle_add(cb, *data)
			self._on_preload_finished = None

	def _find_steamapps(self) -> str | None:
		"""Return path to SteamApps folder or None if it cannot be found.

		This is done because Steam apparently supports both SteamApps and
		steamapps as name for this folder.
		"""
		for x in ("SteamApps", "steamapps", "Steamapps", "steamApps"):
			path = os.path.join(os.path.expanduser(self.STEAMPATH), x)
			if os.path.exists(path):
				return path
		log.warning("Cannot find SteamApps directory")
		return None


	def _set_game_name(self, index, name: str) -> None:
		self._lstVdfProfiles[index][1] = name


	def _set_profile_name(self, index, name: str, filename: str) -> None:
		self._lstVdfProfiles[index][2] = name
		self._lstVdfProfiles[index][3] = filename


	def fill_list(self, items) -> None:
		"""Add items to profile list. Has to run in main thread, otherwise, GTK will crash."""
		for i in items:
			self._lstVdfProfiles.append(i)
			self._q_games.append(( i[0], i[1] ))
			self._s_games.release()
			self._q_profiles.append(( i[0], i[1], i[2] ))
			self._s_profiles.release()


	def on_tvVdfProfiles_cursor_changed(self, *a) -> None:
		"""Called when user selects profile.

		Check if file for that profile is known and if yes, enables next page.
		"""
		tvVdfProfiles = self.builder.get_object("tvVdfProfiles")
		model, iter = tvVdfProfiles.get_selection().get_selected()
		filename = None
		if iter:
			filename = model.get_value(iter, 3)

		self.enable_next(filename is not None, self.import_vdf)


	@staticmethod
	def gen_aset_name(base_name: str, set_name: str) -> str:
		"""Generate name for profile converted from action set."""
		if set_name == "default":
			return base_name
		return "." + base_name + ":" + set_name.lower()


	def on_txName_changed(self, *a) -> None:
		"""Called when text in profile name field is changed.

		Basically enables 'Save' button if name is not empty string.
		"""
		txName         = self.builder.get_object("txName")
		lblASetsNotice = self.builder.get_object("lblASetsNotice")
		lblASetList    = self.builder.get_object("lblASetList")

		btNext = self.enable_next(True, self.vdf_import_confirmed)
		btNext.set_label('Apply')
		btNext.set_use_stock(True)
		if len(self._profile.action_sets) > 1:
			lblASetsNotice.set_visible(True)
			lblASetList.set_visible(True)
			log.info("Imported profile contains action sets")
			lblASetList.set_text("\n".join([
				self.gen_aset_name(txName.get_text().strip(), x)
				for x in self._profile.action_sets
				if x != 'default'
			]))
		else:
			lblASetsNotice.set_visible(False)
			lblASetList.set_visible(False)
		btNext.set_sensitive(self.check_name(txName.get_text()))


	def on_preload_finished(self, callback, *data) -> None:
		"""Schedules callback to be called after initial profile list is loaded."""
		self._on_preload_finished = (callback, data)


	def set_vdf_file(self, filename: str) -> None:
		# TODO: Jump directly to page
		tvVdfProfiles = self.builder.get_object("tvVdfProfiles")
		iter = self._lstVdfProfiles.append(( -1, _("No game"), _("Dropped profile"), filename ))
		tvVdfProfiles.get_selection().select_iter(iter)
		self.window.set_page_complete(self.window.get_nth_page(0), True)
		self.window.set_current_page(1)


	def on_btDump_clicked(self, *a) -> None:
		tvError = self.builder.get_object("tvError")
		swError = self.builder.get_object("swError")
		btDump = self.builder.get_object("btDump")
		tvVdfProfiles = self.builder.get_object("tvVdfProfiles")
		model, iter = tvVdfProfiles.get_selection().get_selected()
		filename = model.get_value(iter, 3)

		dump = StringIO()
		dump.write("\nProfile filename: %s\n" % (filename,))
		dump.write("\nProfile dump:\n")
		try:
			dump.write(open(filename, "r").read())
		except Exception as e:
			dump.write("(failed to write: %s)" % (e,))
		tvError.get_buffer().set_text(dump.getvalue())
		swError.set_visible(True)
		btDump.set_sensitive(False)


	def import_vdf(self, filename: str | None = None) -> None:
		grVdfImportFinished = self.builder.get_object("grVdfImportFinished")
		self.next_page(grVdfImportFinished)

		tvVdfProfiles = self.builder.get_object("tvVdfProfiles")
		lblVdfImportFinished = self.builder.get_object("lblVdfImportFinished")
		lblError = self.builder.get_object("lblError")
		tvError = self.builder.get_object("tvError")
		swError = self.builder.get_object("swError")
		lblName = self.builder.get_object("lblName")
		txName = self.builder.get_object("txName")
		btDump = self.builder.get_object("btDump")

		if filename is None:
			model, iter = tvVdfProfiles.get_selection().get_selected()
			filename = model.get_value(iter, 3)
		if filename.endswith(".vdffz"):
			self._profile = VDFFZProfile()
		else:
			# Best quess
			self._profile = VDFProfile()

		failed = False
		error_log = StringIO()
		self._lock.acquire()
		handler = logging.StreamHandler(error_log)
		logging.getLogger().addHandler(handler)
		swError.set_visible(False)
		lblError.set_visible(False)
		lblName.set_visible(True)
		txName.set_visible(True)
		btDump.set_sensitive(True)

		try:
			self._profile.load(filename)
		except Exception as e:
			log.exception(e)
			lblName.set_visible(False)
			txName.set_visible(False)
			txName.set_text("")
			self._profile = None
			failed = True

		logging.getLogger().removeHandler(handler)
		self._lock.release()

		if failed:
			swError.set_visible(True)
			lblError.set_visible(True)
			btDump.set_sensitive(False)

			lblVdfImportFinished.set_text(_("Import failed"))

			error_log.write("\nProfile filename: %s\n" % (filename,))
			error_log.write("\nProfile dump:\n")
			try:
				error_log.write(open(filename, "r").read())
			except Exception as e:
				error_log.write("(failed to write: %s)" % (e,))

			tvError.get_buffer().set_text(error_log.getvalue())
		else:
			if len(error_log.getvalue()) > 0:
				# Some warnings were displayed
				swError.set_visible(True)
				lblError.set_visible(True)

				lblVdfImportFinished.set_text(_("Profile imported with warnings"))

				tvError.get_buffer().set_text(error_log.getvalue())
				txName.set_text(self._profile.name)
			else:
				lblVdfImportFinished.set_text(_("Profile sucessfully imported"))
				txName.set_text(self._profile.name)
			self.on_txName_changed()


	def vdf_import_confirmed(self, *a) -> None:
		name = self.builder.get_object("txName").get_text().strip()

		if len(self._profile.action_sets) > 1:
			# Update ChangeProfileActions with correct profile names
			for x in self._profile.action_set_switches:
				id = int(x._profile.split(":")[-1])
				target_set = self._profile.action_set_by_id(id)
				x._profile = self.gen_aset_name(name, target_set)

			# Save action set profiles
			for k in self._profile.action_sets:
				if k != 'default':
					filename = self.gen_aset_name(name, k) + ".sccprofile"
					path = os.path.join(get_profiles_path(), filename)
					self._profile.action_sets[k].save(path)

		self.app.new_profile(self._profile, name)
		GLib.idle_add(self.window.destroy)
