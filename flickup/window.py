from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, GObject, Gio, Gtk

from .converter import check_tools
from .presenter import FlickUpPresenter
from . import settings


class FlickUpWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        _videos = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_VIDEOS)
        self._input_file: str | None = None
        self._local_folder: str = _videos or str(Path(GLib.get_home_dir()) / "Videos")
        self._formats = [".mov", ".mp4", ".mkv", ".avi"]
        self._presenter = FlickUpPresenter(self)

        self.set_title("FlickUp")
        self.set_default_size(600, -1)

        self._build_ui()
        self._setup_bindings()
        self._check_tools()

    # ── Form value properties (read by presenter) ─────────────────────────────

    @property
    def input_file(self) -> str | None:
        return self._input_file

    @property
    def output_name(self) -> str:
        return self._row_output_name.get_text().strip()

    @property
    def selected_format(self) -> str:
        return self._formats[self._row_format.get_selected()]

    @property
    def send_to_drive(self) -> bool:
        return self._row_send_to_drive.get_active()

    @property
    def local_folder(self) -> str:
        return self._local_folder

    @property
    def rclone_path(self) -> str:
        return self._row_rclone_path.get_text().strip()

    # ── Public UI update methods (called by presenter) ────────────────────────

    def begin_processing(self) -> None:
        self._btn_spinner.set_visible(True)
        self._btn_label.set_label("Converting…")
        self._set_ui_sensitive(False)

    def end_processing(self) -> None:
        self._btn_spinner.set_visible(False)
        self._btn_label.set_label("Convert")
        self._set_ui_sensitive(True)

    def show_toast(self, message: str, *, high: bool = False) -> None:
        toast = Adw.Toast.new(message)
        toast.set_timeout(4)
        if high:
            toast.set_priority(Adw.ToastPriority.HIGH)
        self._toast_overlay.add_toast(toast)

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self._toast_overlay = Adw.ToastOverlay()
        self._toolbar_view = Adw.ToolbarView()
        self._toast_overlay.set_child(self._toolbar_view)
        self.set_content(self._toast_overlay)

        self._header_bar = Adw.HeaderBar()
        self._toolbar_view.add_top_bar(self._header_bar)

        self._banner = Adw.Banner()
        self._banner.set_revealed(False)
        self._toolbar_view.add_top_bar(self._banner)

        self._page = Adw.PreferencesPage()
        self._toolbar_view.set_content(self._page)

        self._build_input_group()
        self._build_output_group()
        self._build_destination_group()
        self._build_local_group()
        self._build_drive_group()
        self._build_action_group()

    def _build_input_group(self) -> None:
        group = Adw.PreferencesGroup()
        group.set_title("Source")

        self._row_input = Adw.ActionRow()
        self._row_input.set_title("Input File")
        self._row_input.set_subtitle("No file selected")

        self._btn_browse_input = Gtk.Button(label="Browse")
        self._btn_browse_input.add_css_class("flat")
        self._btn_browse_input.set_valign(Gtk.Align.CENTER)
        self._btn_browse_input.connect("clicked", self._on_browse_input)

        self._row_input.add_suffix(self._btn_browse_input)
        self._row_input.set_activatable_widget(self._btn_browse_input)
        group.add(self._row_input)
        self._page.add(group)

    def _build_output_group(self) -> None:
        group = Adw.PreferencesGroup()
        group.set_title("Output")

        self._row_output_name = Adw.EntryRow()
        self._row_output_name.set_title("Output Filename")
        self._row_output_name.set_show_apply_button(False)

        self._row_format = Adw.ComboRow()
        self._row_format.set_title("Format")
        self._row_format.set_model(Gtk.StringList.new(self._formats))

        last_fmt = settings.get_last_format()
        if last_fmt in self._formats:
            self._row_format.set_selected(self._formats.index(last_fmt))

        self._row_format.connect("notify::selected", self._on_format_changed)

        group.add(self._row_output_name)
        group.add(self._row_format)
        self._page.add(group)

    def _build_destination_group(self) -> None:
        group = Adw.PreferencesGroup()
        group.set_title("Destination")

        self._row_send_to_drive = Adw.SwitchRow()
        self._row_send_to_drive.set_title("Send to Drive")
        self._row_send_to_drive.set_subtitle("Upload via rclone after conversion")

        group.add(self._row_send_to_drive)
        self._page.add(group)

    def _build_local_group(self) -> None:
        self._group_local = Adw.PreferencesGroup()
        self._group_local.set_title("Local Destination")

        self._row_local_folder = Adw.ActionRow()
        self._row_local_folder.set_title("Output Folder")
        self._row_local_folder.set_subtitle(self._local_folder)

        self._btn_browse_folder = Gtk.Button(label="Browse")
        self._btn_browse_folder.add_css_class("flat")
        self._btn_browse_folder.set_valign(Gtk.Align.CENTER)
        self._btn_browse_folder.connect("clicked", self._on_browse_folder)

        self._row_local_folder.add_suffix(self._btn_browse_folder)
        self._row_local_folder.set_activatable_widget(self._btn_browse_folder)
        self._group_local.add(self._row_local_folder)
        self._page.add(self._group_local)

    def _build_drive_group(self) -> None:
        self._group_drive = Adw.PreferencesGroup()
        self._group_drive.set_title("rclone Destination")
        self._group_drive.set_description('Example: "remote:MyFolder"')
        self._group_drive.set_visible(False)

        self._row_rclone_path = Adw.EntryRow()
        self._row_rclone_path.set_title("rclone Path")
        self._row_rclone_path.set_show_apply_button(False)

        self._group_drive.add(self._row_rclone_path)
        self._page.add(self._group_drive)

    def _build_action_group(self) -> None:
        group = Adw.PreferencesGroup()

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_halign(Gtk.Align.CENTER)

        self._btn_spinner = Adw.Spinner()
        self._btn_spinner.set_visible(False)
        box.append(self._btn_spinner)

        self._btn_label = Gtk.Label(label="Convert")
        box.append(self._btn_label)

        self._btn_convert = Gtk.Button()
        self._btn_convert.set_child(box)
        self._btn_convert.add_css_class("suggested-action")
        self._btn_convert.add_css_class("pill")
        self._btn_convert.set_hexpand(True)
        self._btn_convert.set_margin_top(8)
        self._btn_convert.set_margin_bottom(8)
        self._btn_convert.connect(
            "clicked", lambda _: self._presenter.on_convert_clicked()
        )

        group.add(self._btn_convert)
        self._page.add(group)

    # ── Bindings ──────────────────────────────────────────────────────────────

    def _setup_bindings(self) -> None:
        self._row_send_to_drive.bind_property(
            "active", self._group_drive, "visible",
            GObject.BindingFlags.SYNC_CREATE,
        )
        self._row_send_to_drive.bind_property(
            "active", self._group_local, "visible",
            GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.INVERT_BOOLEAN,
        )
        self._row_send_to_drive.connect("notify::active", lambda *_: self._check_tools())

    # ── Tool availability warning ─────────────────────────────────────────────

    def _check_tools(self) -> None:
        missing = check_tools(self._row_send_to_drive.get_active())
        if missing:
            names = " and ".join(missing)
            self._banner.set_title(
                f"{names} is not installed. Please install it to use FlickUp."
            )
            self._banner.set_revealed(True)
        else:
            self._banner.set_revealed(False)

    # ── File / folder dialogs ─────────────────────────────────────────────────

    def _on_browse_input(self, _button) -> None:
        video_filter = Gtk.FileFilter()
        video_filter.set_name("Video files")
        video_filter.add_mime_type("video/*")

        all_filter = Gtk.FileFilter()
        all_filter.set_name("All files")
        all_filter.add_pattern("*")

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(video_filter)
        filters.append(all_filter)

        dialog = Gtk.FileDialog.new()
        dialog.set_title("Select Input Video")
        dialog.set_filters(filters)
        dialog.set_default_filter(video_filter)
        dialog.set_initial_folder(Gio.File.new_for_path(GLib.get_home_dir()))
        dialog.open(self, None, self._on_input_file_chosen)

    def _on_input_file_chosen(self, dialog, result) -> None:
        try:
            file = dialog.open_finish(result)
            if file:
                self._input_file = file.get_path()
                self._row_input.set_subtitle(file.get_basename())
                self._row_output_name.set_text(Path(self._input_file).stem)
        except GLib.Error as e:
            if e.code not in (Gtk.DialogError.CANCELLED, Gtk.DialogError.DISMISSED):
                self.show_toast(f"Error opening file: {e.message}")

    def _on_browse_folder(self, _button) -> None:
        dialog = Gtk.FileDialog.new()
        dialog.set_title("Select Output Folder")
        dialog.set_initial_folder(Gio.File.new_for_path(GLib.get_home_dir()))
        dialog.select_folder(self, None, self._on_folder_chosen)

    def _on_folder_chosen(self, dialog, result) -> None:
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                self._local_folder = folder.get_path()
                self._row_local_folder.set_subtitle(self._local_folder)
        except GLib.Error as e:
            if e.code not in (Gtk.DialogError.CANCELLED, Gtk.DialogError.DISMISSED):
                self.show_toast(f"Error selecting folder: {e.message}")

    def _on_format_changed(self, *_) -> None:
        settings.save_last_format(self.selected_format)

    # ── Internal UI state helpers ─────────────────────────────────────────────

    def _set_ui_sensitive(self, sensitive: bool) -> None:
        self._btn_browse_input.set_sensitive(sensitive)
        self._btn_browse_folder.set_sensitive(sensitive)
        self._row_output_name.set_sensitive(sensitive)
        self._row_format.set_sensitive(sensitive)
        self._row_send_to_drive.set_sensitive(sensitive)
        self._row_rclone_path.set_sensitive(sensitive)
