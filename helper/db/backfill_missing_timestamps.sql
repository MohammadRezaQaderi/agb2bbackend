/*
Backfill rows that were inserted through SQLAlchemy before ORM timestamp
defaults were added. Run this against the target database, for example:

    USE [AGB2B_COPY];
    :r helper/db/backfill_missing_timestamps.sql
*/

DECLARE @sql NVARCHAR(MAX) = N'';

SELECT @sql = @sql + N'
UPDATE ' + QUOTENAME(SCHEMA_NAME(t.schema_id)) + N'.' + QUOTENAME(t.name) + N'
SET
    created_time = COALESCE(created_time, edited_time, GETDATE()),
    edited_time = COALESCE(edited_time, created_time, GETDATE())
WHERE created_time IS NULL OR edited_time IS NULL;
'
FROM sys.tables AS t
WHERE EXISTS (
    SELECT 1
    FROM sys.columns AS c
    WHERE c.object_id = t.object_id
      AND c.name = N'created_time'
)
AND EXISTS (
    SELECT 1
    FROM sys.columns AS c
    WHERE c.object_id = t.object_id
      AND c.name = N'edited_time'
);

EXEC sp_executesql @sql;

UPDATE nr
SET created_time = GETDATE()
FROM dbo.notification_reads AS nr
WHERE nr.created_time IS NULL;
