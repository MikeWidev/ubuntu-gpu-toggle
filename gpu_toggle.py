#!/usr/bin/env python3
"""Small GTK app to switch the NVIDIA GPU on/off using envycontrol."""

import os
import subprocess

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

# Mode used when the GPU is switched on: "hybrid" (render offload) or "nvidia".
ON_MODE = "hybrid"
OFF_MODE = "integrated"


def configured_mode():
    """Mode envycontrol has configured (takes effect after reboot)."""
    try:
        out = subprocess.run(["envycontrol", "--query"], capture_output=True,
                             text=True, timeout=10)
        return out.stdout.strip().splitlines()[-1].strip()
    except (OSError, subprocess.SubprocessError, IndexError):
        return "unknown"


def gpu_active_now():
    """Whether the NVIDIA driver is loaded in the running session."""
    return os.path.isdir("/sys/module/nvidia")


class GpuToggleWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="NVIDIA GPU Toggle")
        self.set_border_width(18)
        self.set_resizable(False)
        self.set_icon_name("video-display")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.add(box)

        row = Gtk.Box(spacing=24)
        label = Gtk.Label(xalign=0)
        label.set_markup("<b><big>NVIDIA GPU</big></b>")
        row.pack_start(label, True, True, 0)
        self.switch = Gtk.Switch(valign=Gtk.Align.CENTER)
        self.switch.connect("state-set", self.on_state_set)
        row.pack_end(self.switch, False, False, 0)
        box.pack_start(row, False, False, 0)

        self.status = Gtk.Label(xalign=0)
        self.status.set_line_wrap(True)
        self.status.set_max_width_chars(42)
        box.pack_start(self.status, False, False, 0)

        self.spinner = Gtk.Spinner()
        box.pack_start(self.spinner, False, False, 0)

        self.busy = False
        self.refresh()

    def refresh(self):
        mode = configured_mode()
        self.busy = True
        self.switch.set_active(mode != OFF_MODE)
        self.busy = False

        running = "on" if gpu_active_now() else "off"
        text = f"Configured mode: <b>{mode}</b>\nRight now the GPU is: <b>{running}</b>"
        if (mode != OFF_MODE) != (running == "on"):
            text += "\n\n<i>Reboot required for the change to take effect.</i>"
        self.status.set_markup(text)

    def on_state_set(self, switch, state):
        if self.busy:
            return False
        target = ON_MODE if state else OFF_MODE
        self.switch.set_sensitive(False)
        self.spinner.start()
        # Runs async so the window stays responsive while pkexec asks for the password.
        cmd = ["pkexec", "envycontrol", "-s", target]
        pid, _, out_fd, err_fd = GLib.spawn_async(
            cmd, flags=GLib.SpawnFlags.SEARCH_PATH | GLib.SpawnFlags.DO_NOT_REAP_CHILD,
            standard_output=True, standard_error=True)
        GLib.child_watch_add(GLib.PRIORITY_DEFAULT, pid, self.on_done, (target, out_fd, err_fd))
        return False

    def on_done(self, pid, status, data):
        target, out_fd, err_fd = data
        with os.fdopen(out_fd) as f_out, os.fdopen(err_fd) as f_err:
            output = (f_out.read() + f_err.read()).strip()
        self.spinner.stop()
        self.switch.set_sensitive(True)
        ok = os.waitstatus_to_exitcode(status) == 0
        self.refresh()
        if ok:
            self.ask_reboot(target)
        else:
            self.show_error(output or "Cancelled or failed.")

    def ask_reboot(self, target):
        dialog = Gtk.MessageDialog(
            transient_for=self, modal=True, message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.NONE,
            text=f"Switched to '{target}' mode")
        dialog.format_secondary_text("A reboot is required for the change to take effect.")
        dialog.add_buttons("Later", Gtk.ResponseType.CANCEL, "Reboot now", Gtk.ResponseType.OK)
        if dialog.run() == Gtk.ResponseType.OK:
            subprocess.Popen(["systemctl", "reboot"])
        dialog.destroy()

    def show_error(self, message):
        dialog = Gtk.MessageDialog(
            transient_for=self, modal=True, message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK, text="Could not switch GPU mode")
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()


def main():
    win = GpuToggleWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
