DECLARE @threshold INT = 100 --Set the size in MB, if it grows larger than this it should be truncated to 1MB
DECLARE @truncsize INT = 1 --Set the size to this after truncating
DECLARE @logsize FLOAT;
Declare @sql table (id int identity(1,1) primary key, sql nvarchar(max))
Declare @tempsql nvarchar(max);
Declare @counter int = 1
Declare @total int= 0
DECLARE @Log TABLE
(
DatabaseName VARCHAR(255),
[log_size] FLOAT,
[log_perc] FLOAT,
[status] INT)

INSERT INTO @Log
EXECUTE('DBCC SQLPERF(''logspace'')')

--Select * from @Log 
INSERT INTO @sql(sql)
SELECT concat( '; USE [', D.name, '] ; 
ALTER DATABASE ', D.name,'
SET RECOVERY SIMPLE;
DBCC SHRINKFILE (',f.name,',',@truncsize,');
ALTER DATABASE ',D.name,'
SET RECOVERY FULL;
')
FROM @Log L
JOIN sys.databases D ON L.DatabaseName = D.name
JOIN sys.master_files f on d.database_id = f.database_id and f.type_desc = 'LOG'
WHERE D.database_id > 4
AND L.log_size > @threshold
ORDER BY L.log_size DESC

set @total = (select count(*) from @sql)

--exec ('select sql from @sql where id = 1')

WHILE @total >= @counter 
Begin
    Set @tempsql = (select sql from @sql where id = @counter)
    exec sp_executesql @tempsql 
    --select @tempsql
    SET @counter = @counter + 1
END;