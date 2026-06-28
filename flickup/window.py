import tempfile
import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, GObject, Gio, Gtk

from .converter import ConversionJob, check_tools, run_conversion


class FlickUpWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._input_file: str | None = None
        self._local_folder: str | None = None
        self._formats = [".mov", ".mp4", ".mkv", ".avi"]

        self.set_title("FlickUp")
        self.set_default_size(600, -1)

        self._build_ui()
        self._setup_bindings()
        self._check_tools()

    # ── UI construction ─────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self._toast_overlay = Adw.ToastOverlay()
        self._toolbar_view = Adw.ToolbarView()
        self._toast_overlay.set_child(self._toolbar_view)
        self.set_content(self._toast_overlay)

        # Header bar
        self._header_bar = Adw.HeaderBar()
        self._spinner = Adw.Spinner()
        self._spinner.set_visible(False)
        self._header_bar.pack_end(self._spinner)
        self._toolbar_view.add_top_bar(self._header_bar)

        # Banner (tool warnings)
        self._banner = Adw.Banner()
        self._banner.set_revealed(False)
        self._toolbar_view.add_top_bar(self._banner)

        # Preferences page (handles scroll + clamp internally)
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

        btn = Gtk.Button(label="Browse")
        btn.add_css_class("flat")
        btn.set_valign(Gtk.Align.CENTER)
        btn.connect("clicked", self._on_browse_input)
        self._btn_browse_input = btn

        self._row_input.add_suffix(btn)
        self._row_input.set_activatable_widget(btn)
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
        self._row_local_folder.set_subtitle("No folder selected")

        btn = Gtk.Button(label="Browse")
        btn.add_css_class("flat")
        btn.set_valign(Gtk.Align.CENTER)
        btn.connect("clicked", self._on_browse_folder)
        self._btn_browse_folder = btn

        self._row_local_folder.add_suffix(btn)
        self._row_local_folder.set_activatable_widget(btn)
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

        self._btn_convert = Gtk.Button(label="Convert")
        self._btn_convert.add_css_class("suggested-action")
        self._btn_convert.add_css_class("pill")
        self._btn_convert.set_hexpand(True)
        self._btn_convert.set_margin_top(8)
        self._btn_convert.set_margin_bottom(8)
        self._btn_convert.connect("clicked", self._on_convert_clicked)

        row = Adw.ActionRow()
        row.set_title("")
        row.add_suffix(self._btn_convert)
        row.set_activatable_widget(self._btn_convert)
        group.add(row)
        self._page.add(group)

    # ── Bindings ─────────────────────────────────────────────────────────────

    def _setup_bindings(self) -> None:
        self._row_send_to_drive.bind_property(
            "active",
            self._group_drive,
            "visible",
            GObject.BindingFlags.SYNC_CREATE,
        )
        self._row_send_to_drive.bind_property(
            "active",
            self._group_local,
            "visible",
            GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.INVERT_BOOLEAN,
        )
        self._row_send_to_drive.connect(
            "notify::active", lambda *_: self._check_tools()
        )

    # ── Tool availability ─────────────────────────────────────────────────────

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

    # ── File / folder pickers ─────────────────────────────────────────────────

    def _on_browse_input(self, _button) -> None:
        dialog = Gtk.FileDialog.new()
        dialog.set_title("Select Input Video")

        video_filter = Gtk.FileFilter()
        video_filter.set_name("Video files")
        video_filter.add_mime_type("video/*")

        all_filter = Gtk.FileFilter()
        all_filter.set_name("All files")
        all_filter.add_pattern("*")

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(video_filter)
        filters.append(all_filter)
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
        except GLib.Error as e:
            if e.code not in (Gtk.DialogError.CANCELLED, Gtk.DialogError.DISMISSED):
                self._show_toast(f"Error opening file: {e.message}")

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
                self._show_toast(f"Error selecting folder: {e.message}")

    # ── Validation ────────────────────────────────────────────────────────────

    def _validate(self) -> str | None:
        if not self._input_file:
            return "Please select an input file."
        if not self._row_output_name.get_text().strip():
            return "Please enter an output filename."
        if self._row_send_to_drive.get_active():
            path = self._row_rclone_path.get_text().strip()
            if not path:
                return "Please enter an rclone path (e.g. remote:folder)."
            if ":" not in path:
                return "rclone path must include a remote name (e.g. remote:folder)."
        else:
            if not self._local_folder:
                return "Please select an output folder."
        return None

    # ── Conversion ────────────────────────────────────────────────────────────

    def _on_convert_clicked(self, _button) -> None:
        error = self._validate()
        if error:
            self._show_toast(error)
            return

        output_name = self._row_output_name.get_text().strip()
        fmt = self._formats[self._row_format.get_selected()]
        send_to_drive = self._row_send_to_drive.get_active()

        if send_to_drive:
            output_dir = tempfile.mkdtemp(prefix="flickup_")
        else:
            output_dir = self._local_folder

        output_file = str(Path(output_dir) / (output_name + fmt))
        rclone_path = self._row_rclone_path.get_text().strip() if send_to_drive else ""

        job = ConversionJob(
            input_file=self._input_file,
            output_file=output_file,
            send_to_drive=send_to_drive,
            rclone_path=rclone_path,
        )

        self._set_processing(True)
        threading.Thread(
            target=run_conversion,
            args=(job, self._on_progress, self._on_done),
            daemon=True,
        ).start()

    def _set_processing(self, processing: bool) -> None:
        self._spinner.set_visible(processing)
        self._btn_convert.set_sensitive(not processing)
        self._btn_browse_input.set_sensitive(not processing)
        self._btn_browse_folder.set_sensitive(not processing)
        self._row_output_name.set_sensitive(not processing)
        self._row_format.set_sensitive(not processing)
        self._row_send_to_drive.set_sensitive(not processing)
        self._row_rclone_path.set_sensitive(not processing)

    def _on_progress(self) -> bool:
        return GLib.SOURCE_REMOVE

    def _on_done(self, success: bool, error: str | None) -> bool:
        self._set_processing(False)
        if success:
            self._show_toast("Conversion complete!")
        else:
            msg = (error or "Unknown error")[:200]
            self._show_toast(f"Error: {msg}", high=True)
        return GLib.SOURCE_REMOVE

    # ── Toast helper ──────────────────────────────────────────────────────────

    def _show_toast(self, message: str, *, high: bool = False) -> None:
        toast = Adw.Toast.new(message)
        toast.set_timeout(4)
        if high:
            toast.set_priority(Adw.ToastPriority.HIGH)
        self._toast_overlay.add_toast(toast)
