import ntpath
import os
from itertools import count
from pathlib import Path

from PyQt6.QtCore import QFile, QIODevice, QSaveFile


class TranscriptController:
    def __init__(self, directory=None):
        self.directory = Path(directory) if directory is not None else Path(__file__).resolve().parents[1] / "user_data"
        self.current_path = None

    def files(self):
        self.directory.mkdir(exist_ok=True)
        return sorted(
            (path for path in self.directory.iterdir() if path.suffix.lower() == ".txt" and path.is_file()),
            key=lambda path: path.name.casefold(),
        )

    def open(self, path):
        try:
            text = path.read_text(encoding="utf-8-sig")
        except FileNotFoundError:
            text = "" if self.recreate_missing_file(path) else path.read_text(encoding="utf-8-sig")
        self.current_path = path
        return text

    def recreate_missing_file(self, path, text=""):
        self.directory.mkdir(exist_ok=True)
        try:
            self._create_file(path, text)
        except FileExistsError:
            return False
        return True

    @staticmethod
    def _create_file(path, text):
        stream = path.open("x", encoding="utf-8", newline="\n")
        try:
            with stream:
                stream.write(text)
        except (OSError, UnicodeError):
            path.unlink(missing_ok=True)
            raise

    def create(self, text=""):
        self.directory.mkdir(exist_ok=True)
        for index in count():
            name = "New File.txt" if index == 0 else f"New File ({index}).txt"
            path = self.directory / name
            try:
                self._create_file(path, text)
            except FileExistsError:
                continue
            self.current_path = path
            return path

    def save(self, text):
        if self.current_path is None:
            return self.create(text)

        data = text.encode("utf-8")
        file = QSaveFile(str(self.current_path))
        if not file.open(QIODevice.OpenModeFlag.WriteOnly):
            raise OSError(file.errorString())
        if file.write(data) != len(data):
            file.cancelWriting()
            raise OSError(file.errorString())
        if not file.commit():
            raise OSError(file.errorString())
        return self.current_path

    @staticmethod
    def normalize_filename(name):
        name = name.strip(" ")
        stem = name[:-4] if name.lower().endswith(".txt") else name
        if not stem or stem in (".", "..") or "/" in stem or "\\" in stem or ntpath.isreserved(stem):
            raise ValueError("Enter a valid file name.")
        return name if stem != name else f"{stem}.txt"

    def rename(self, path, name):
        filename = self.normalize_filename(name)
        if path.name == filename or path.stem == name.strip(" "):
            return path

        target = self.directory / filename
        if os.name == "nt":
            # Windows rename rejects collisions and supports case-only changes.
            path.rename(target)
        else:
            file = QFile(str(path))
            if not file.rename(str(target)):
                raise OSError(file.errorString())
        if self.current_path == path:
            self.current_path = target
        return target

    def delete(self, path):
        path.unlink(missing_ok=True)
        if self.current_path == path:
            self.current_path = None
