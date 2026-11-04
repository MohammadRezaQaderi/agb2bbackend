from helper.db.copy_agb2b import (
    resolve_backup_directory,
    server_path_dirname,
    server_path_join,
)


class BackupPathCursor:
    def __init__(self, default_directory):
        self.default_directory = default_directory
        self.executed = False

    def execute(self, _sql):
        self.executed = True

    def fetchone(self):
        return (self.default_directory,)


def test_windows_server_paths_are_handled_on_any_client_os():
    assert server_path_dirname(r"D:\DB\AGB2B.mdf") == r"D:\DB"
    assert server_path_join(r"D:\SQLBackup", "copy.bak") == r"D:\SQLBackup\copy.bak"


def test_sql_server_default_backup_directory_is_preferred(monkeypatch):
    monkeypatch.delenv("AG_DB_BACKUP_DIRECTORY", raising=False)
    cursor = BackupPathCursor("E:\\MSSQL\\Backup\\")

    result = resolve_backup_directory(cursor, r"D:\DB")

    assert result == r"E:\MSSQL\Backup"
    assert cursor.executed


def test_explicit_backup_directory_avoids_server_default_lookup(monkeypatch):
    monkeypatch.setenv("AG_DB_BACKUP_DIRECTORY", r"E:\FromEnvironment")
    cursor = BackupPathCursor(r"E:\Default")

    result = resolve_backup_directory(cursor, r"D:\DB", "F:\\Explicit\\")

    assert result == r"F:\Explicit"
    assert not cursor.executed


def test_environment_backup_directory_is_supported(monkeypatch):
    monkeypatch.setenv("AG_DB_BACKUP_DIRECTORY", "E:\\SqlBackup\\")
    cursor = BackupPathCursor(None)

    result = resolve_backup_directory(cursor, r"D:\DB")

    assert result == r"E:\SqlBackup"
    assert not cursor.executed
