SELECT
    BackupRawId,
    SourceServer,
    DatabaseName,
    BackupType,
    BackupStartDate,
    BackupFinishDate,
    CompressedSizeBytes,
    PhysicalDeviceName
FROM [DBAdmin].[dbo].[ProdBackup_Raw]
WHERE SourceServer = 'LAWLDBP1LAS1'
  AND DatabaseName = 'lawprod'
  AND CAST(BackupStartDate AS DATE) = CAST(GETDATE() AS DATE)
ORDER BY BackupStartDate DESC;