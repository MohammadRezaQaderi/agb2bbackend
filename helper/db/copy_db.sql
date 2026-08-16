USE master;
GO


/* ============================================================
   STEP 1 - گرفتن Backup از دیتابیس اصلی
   ============================================================ */

BACKUP DATABASE [AGB2B]
TO DISK = N'D:\DB\AGB2B_COPY.bak'
WITH
    COPY_ONLY,
    INIT,
    COMPRESSION,
    CHECKSUM,
    STATS = 10;
GO


/* ============================================================
   STEP 2 - بررسی سالم بودن Backup
   ============================================================ */

RESTORE VERIFYONLY
FROM DISK = N'D:\DB\AGB2B_COPY.bak'
WITH CHECKSUM;
GO


/* ============================================================
   STEP 3 - حذف AGB2B_COPY قبلی در صورت وجود
   ============================================================ */

IF DB_ID(N'AGB2B_COPY') IS NOT NULL
BEGIN

    ALTER DATABASE [AGB2B_COPY]
    SET SINGLE_USER
    WITH ROLLBACK IMMEDIATE;

    DROP DATABASE [AGB2B_COPY];

END
GO


/* ============================================================
   STEP 4 - ساخت AGB2B_COPY از Backup
   ============================================================ */

RESTORE DATABASE [AGB2B_COPY]
FROM DISK = N'D:\DB\AGB2B_COPY.bak'
WITH
    MOVE N'AG'
        TO N'D:\DB\AGB2B_COPY.mdf',

    MOVE N'AG_log'
        TO N'D:\DB\AGB2B_COPY_log.ldf',

    RECOVERY,
    CHECKSUM,
    STATS = 10;
GO


/* ============================================================
   STEP 5 - اطمینان از Multi User بودن دیتابیس جدید
   ============================================================ */

ALTER DATABASE [AGB2B_COPY]
SET MULTI_USER;
GO


/* ============================================================
   STEP 6 - بررسی وضعیت دو دیتابیس
   ============================================================ */

SELECT
    name,
    state_desc,
    user_access_desc
FROM sys.databases
WHERE name IN (N'AGB2B', N'AGB2B_COPY');
GO


/* ============================================================
   STEP 7 - بررسی مسیر فایل‌های دیتابیس COPY
   ============================================================ */

SELECT
    name AS LogicalName,
    physical_name,
    type_desc
FROM sys.master_files
WHERE database_id = DB_ID(N'AGB2B_COPY');
GO


/* ============================================================
   STEP 8 - بررسی تعداد Table های دیتابیس COPY
   ============================================================ */

USE [AGB2B_COPY];
GO

SELECT COUNT(*) AS TableCount
FROM sys.tables;
GO