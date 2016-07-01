USE [FogBugz]
GO

/****** Object:  Table [dbo].[AccountHistory]    Script Date: 5/27/2016 9:06:04 AM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

-- DROP TABLES
IF OBJECT_ID('dbo.Case', 'U') IS NOT NULL 
  DROP TABLE dbo.[Case]; 
GO

IF OBJECT_ID('dbo.TimeTable', 'U') IS NOT NULL 
  DROP TABLE dbo.TimeTable;
GO

IF OBJECT_ID('dbo.lstKanban', 'U') IS NOT NULL 
  DROP TABLE dbo.[lstKanban]; 
GO

IF OBJECT_ID('dbo.lstKanbanColor', 'U') IS NOT NULL 
  DROP TABLE dbo.lstKanbanColor;
GO

-- RECREATE TABLES
Create Table dbo.TimeTable
(
    IdDate date PRIMARY KEY CLUSTERED,
    Day int,
    DayofYear int,
    DayofWeekName varchar(10),
    Week int,
    Month int,
    MonthName varchar(10),
    Quarter varchar(2),
    Year int,
)
 
-- Declare and set variables for loop
Declare
@StartDate datetime,
@EndDate datetime,
@Date datetime
 
Set @StartDate = '2015/01/01'
Set @EndDate = FORMAT(CAST(GETDATE() As date ), 'yyyy/MM/dd', 'en-US')
Set @Date = @StartDate
 
-- Loop through dates
WHILE @Date <=@EndDate
BEGIN 
    -- Insert record in dimension table
    INSERT Into TimeTable
    (
    [IdDate],
    [Day],
    [DayofYear],
    [Dayofweekname],
    [Week],
    [Month],
    [MonthName],
    [Quarter],
    [Year]
    )
    Values
    (
    @Date,
    --CONVERT(varchar(10), @Date, 105), -- DateString, removed See links for 105 explanation
    Day(@Date),
    DATEPART(dy, @Date),
    DATENAME(dw, @Date),
    DATEPART(wk, @Date),
    DATEPART(mm, @Date),
    DATENAME(mm, @Date),
    'Q'+Cast(DATENAME(qq, @Date) as varchar(1)),
    Year(@Date)
    )
 
    -- Goto next day
    Set @Date = @Date + 1
END
GO

CREATE TABLE [dbo].[Case](
	[IDCase] [int] NOT NULL, --ixBug field in Fogbugz
	[IDParentCase] [int], -- self reference for parent case
	-- useful info
	[Title] [nvarchar](500), --sTitle
	[Status] [nvarchar](70), --sStatus
	[Project] [nvarchar](100), --sProject
	[Area] [nvarchar](100), --sArea
	[Category] [nvarchar](100), --sCategory
	[Priority] [nvarchar](50), --sPriority
	[Milestone] [nvarchar](100), --sFixFor
	-- people names
	[AssignedTo] [nvarchar](100), --sPersonAssignedTo
	[OpenedBy] [nvarchar](100), --ixPersonOpenedBy to get sfullname
	[ResolvedBy] [nvarchar](100), --ixPersonResolvedBy to get sfullname
	[ClosedBy] [nvarchar](100), -- ixPersonClosedBy to get sfullname
	[LastEditedBy] [nvarchar](100), --ixPersonLastEdited
	-- people IDS (from Fogbugz)
	[IDAssignedTo] [int],
	[IDOpenedBy] [int],
	[IDResolvedBy] [int],
	[IDClosedBy] [int],
	[IDLastEditedBy] [int],
	-- dates
	[OpenedDate] [date],
	[ClosedDate] [date],
	[ResolvedDate] [date],
	[DueDate] [date],
	[LastUpdatedDate] [date],
	-- hours
    [hrsElapsed] [decimal](9,3),
    [hrsCurrEst] [decimal](9,3),
    [hrsOrigEst] [decimal](9,3),
    [hrsElapsedExtra] [decimal](9,3),
    -- kanban
    [IDKanban] [int],
    [IDKanbanColor] [int]

	CONSTRAINT PK_Case PRIMARY KEY NONCLUSTERED (IDCase)--,
--	CONSTRAINT FK_CaseOpenedDate FOREIGN KEY (OpenedDate) REFERENCES dbo.TimeTable (IdDate),
--	CONSTRAINT FK_CaseClosedDate FOREIGN KEY (ClosedDate) REFERENCES dbo.TimeTable (IdDate)
);

CREATE TABLE [dbo].[lstKanban](
	[IDKanban] [int] NOT NULL,
	[KanbanStr] [nvarchar](100)

	CONSTRAINT PK_lstKanban PRIMARY KEY CLUSTERED (IDKanban)
);

INSERT INTO [dbo].[lstKanban] (IDKanban, KanbanStr) VALUES
	(0, 'None'),
	(1, 'Functional Specifications'),
	(2, 'Ready for Programming'),
	(3, 'Programming in Progress'),
	(4, 'In Integration Testing'),
	(5, 'Ready to Ship'),
	(6, 'In QA for Testing')

CREATE TABLE [dbo].[lstKanbanColor](
	[IDKanbanColor] [int] NOT NULL,
	[KanbanColorStr] [nvarchar](100)

	CONSTRAINT PK_lstKanbanColor PRIMARY KEY CLUSTERED (IDKanbanColor)
);

INSERT INTO [dbo].[lstKanbanColor] VALUES
	(1, 'White'),
	(2, '4 - Medium'),
	(3, '3 - Third Priority'),
	(4, '1 - First Priority'),
	(5, '2 - Second Priority'),
	(6, '5 - Low'),
	(7, '6 - Very Low')

ALTER TABLE [dbo].[Case]
ADD FOREIGN KEY (IDKanban)
REFERENCES [dbo].[lstKanban] (IDKanban)

ALTER TABLE [dbo].[Case]
ADD FOREIGN KEY (IDKanbanColor)
REFERENCES [dbo].[lstKanbanColor] (IDKanbanColor)
