from helper.db.copy_agb2b import (
    execute_and_drain,
    resolve_backup_directory,
    server_file_exists,
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


class CommandCursor:
    def __init__(self, nextsets=(), file_exists=1):
        self.nextsets = iter(nextsets)
        self.file_exists = file_exists
        self.calls = []

    def execute(self, sql, *params):
        self.calls.append((sql, params))

    def nextset(self):
        return next(self.nextsets, None)

    def fetchone(self):
        return (self.file_exists,)


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


def test_backup_command_result_sets_are_drained():
    cursor = CommandCursor(nextsets=(True, True, None))

    execute_and_drain(cursor, "BACKUP DATABASE [AGB2B]")

    assert cursor.calls == [("BACKUP DATABASE [AGB2B]", ())]


def test_server_file_check_uses_sql_server_view():
    cursor = CommandCursor(file_exists=1)

    assert server_file_exists(cursor, r"D:\DB\Backup\copy.bak")
    assert cursor.calls == [("EXEC master.dbo.xp_fileexist ?", (r"D:\DB\Backup\copy.bak",))]
