#This script will print a list of all overdue cases assigned to me

from fogbugz import FogBugz
from datetime import datetime, timedelta
import fbSettings # fbSettings.txt
import pyodbc
from datetime import datetime
from datetime import date
import calendar
import pytz

# Get FogBugz API connection information
print fbSettings.URL
print fbSettings.TOKEN


# --------------------------------------------------------------
# SECTION: System settings
# --------------------------------------------------------------


SETTINGSFILE='fbSettings.py' # if this changes, also change the "import fbSettings" abvoe
SERVER='PC-Longphi'
DATABASE='FogBugz'

fb = FogBugz(fbSettings.URL, fbSettings.TOKEN)

'''
#Get all cases assigned to me
resp = fb.search(cols='ixBug,sTitle,dtDue')

print 'The following cases are overdue:'

for case in resp.cases.childGenerator():
    #Check to see if we have a due date
    if case.dtdue.string: 
        #All dates returned are UTC, so parse the due date
        #into a datetime object.
        dtDueUtc = datetime.strptime(case.dtdue.string,'%Y-%m-%dT%H:%M:%SZ')
        fOverdue = dtDueUtc <= datetime.utcnow()
        if fOverdue:
            tdDays = (datetime.utcnow() - dtDueUtc).days
            sTitle = case.stitle.string.encode('UTF-8')
            print "%s: %s (%s days)" % (case['ixbug'], sTitle, tdDays)

for case in resp.cases.childGenerator():
    print case['ixbug'] + ':' + case.stitle.string
'''
'''
filters=fb.listFilters()
for filt in filters:
    print(filt)
'''


# --------------------------------------------------------------
# SECTION: Get all recently updated cases and their information.
# --------------------------------------------------------------


query='edited:"' + str(fbSettings.LASTRECORDED) + '..today"'
# SEARCH for all cases that were recently edited. These are the cases that needs their data updated.
resp=fb.search(q=query, cols='ixBug,sTitle,sProject,sArea,sCategory,sPersonAssignedTo,sPriority,sStatus,dtOpened,dtClosed,ixPersonOpenedBy,ixBugParent,sFixFor,ixPersonResolvedBy,ixPersonClosedBy,dtLastUpdated')

PersonsList = {} # A dictionary of people recorded in Fogbugz. Needed because SEARCH only gives ixPerson (an ID) not the name. Then VIEWPERSON is used to get the name. This helps avoid having to search the same person multiple times.
insertValues = [] # A list of tuples, where tuples are the case's information, to be inserted or updated into dbo.Case.
insertDates = set() # A set of dates to insert into dbo.TimeTable
maxDate = datetime.strptime(fbSettings.LASTRECORDED,'%Y-%m-%d %H:%M:%SZ')
print "previous update time = "
print maxDate

# Go through each case and get its information. Clean up the data along the way.
for case in resp.cases.childGenerator():
    # get Opened By user
    IDOpenedBy = case.ixpersonopenedby.string
    StrOpenedBy = ''
    if IDOpenedBy in PersonsList:
        StrOpenedBy = PersonsList[IDOpenedBy]
    else:
        # person was not recorded yet, search FogBugz for user
        person = fb.viewPerson(ixPerson=IDOpenedBy)
        PersonsList[IDOpenedBy] = StrOpenedBy = person.sfullname.string

    # get Resolved By user
    IDResolvedBy = case.ixpersonresolvedby.string
    StrResolvedBy = ''
    if IDResolvedBy == '0':
        StrResolvedBy = None
    else:
        if IDResolvedBy in PersonsList:
            StrResolvedBy = PersonsList[IDResolvedBy]
        else:
            person = fb.viewPerson(ixPerson=IDResolvedBy)
            PersonsList[IDResolvedBy] = StrResolvedBy = person.sfullname.string

    # get Closed By user
    IDClosedBy = case.ixpersonclosedby.string
    StrClosedBy = ''
    if IDClosedBy == '0':
        StrClosedBy = None
    else:
        if IDClosedBy in PersonsList:
            StrClosedBy = PersonsList[IDClosedBy]
        else:
            person = fb.viewPerson(ixPerson=IDClosedBy)
            PersonsList[IDClosedBy] = StrClosedBy = person.sfullname.string
        
    # get Date Closed
    StrDtClosed = ''
    if case.dtclosed.string is not None: # insert closed date and opened date
        StrDtClosed = datetime.strptime(case.dtclosed.string,'%Y-%m-%dT%H:%M:%SZ')
        insertDates.update([datetime.strptime(case.dtopened.string,'%Y-%m-%dT%H:%M:%SZ').strftime('%Y%m%d'), datetime.strptime(case.dtclosed.string,'%Y-%m-%dT%H:%M:%SZ').strftime('%Y%m%d')])
    else: # only insert opened date since closed date was empty
        StrDtClosed = None
        insertDates.update([datetime.strptime(case.dtopened.string,'%Y-%m-%dT%H:%M:%SZ')])

    # get Parent Case
    StrParentCase = case.ixbugparent.string
    if StrParentCase == '0':
        StrParentCase = None

    if case.dtlastupdated.string is not None:
        DtLastUpdate = datetime.strptime(case.dtlastupdated.string, '%Y-%m-%dT%H:%M:%SZ')
        
        if DtLastUpdate > maxDate:
            maxDate=DtLastUpdate
    
    # return IDcase, IDParentCase, Title, Project, Area, Category, AssignedTo, Priority, Status, OpenedDate, ClosedDate, OpenedBy, Milestone, ResolvedBy, ClosedBy
    insertValues.append((case['ixbug'], StrParentCase, case.stitle.string, case.sproject.string, case.sarea.string, case.scategory.string, case.spersonassignedto.string, case.spriority.string, case.sstatus.string, datetime.strptime(case.dtopened.string,'%Y-%m-%dT%H:%M:%SZ'), StrDtClosed, StrOpenedBy, case.sfixfor.string, StrResolvedBy, StrClosedBy))


# --------------------------------------------------------------
# SECTION: Update/Insert cases to the database
# --------------------------------------------------------------


# Connect to the database
conn = pyodbc.connect('DRIVER={SQL Server};SERVER='+SERVER+ ';DATABASE='+DATABASE)
cursor = conn.cursor()

# Insert dates into database
#   [NOTE:] Inserting dates does not check if the date is already in the database. Not sure if it should be implemented.
# Repeat dates to be inserted since the SQL statement needs it repeated.
insertDatesTuples = [((x),)*9 for x in insertDates]
for x in insertDatesTuples:
    try:
        cursor.execute("""INSERT INTO [dbo].[TimeTable] ([IdDate],[Day],[DayofYear],[Dayofweekname],[Week],[Month],[MonthName],[Quarter],[Year]) Values (?,Day(?),DATEPART(dy, ?),DATENAME(dw, ?),DATEPART(wk, ?),DATEPART(mm, ?),DATENAME(mm, ?),'Q'+Cast(DATENAME(qq, ?) as varchar(1)),Year(?))""", x)
        print 'inserted Time ' + x[0]
        conn.commit()
    except Exception as e:
        conn.rollback()

# Get a list of the case IDs to be looped over.
CaseIDs = []
for index in range(0,len(insertValues)):
    CaseIDs.append((insertValues[index][0], index))

# Loop through cases and determine if it needs to be inserted or updated in the database.
for CaseID, index in CaseIDs:
    caseInfo=insertValues[index]

    # check if case is in database
    invis=cursor.execute("SELECT IDCase from dbo.[Case] where IDCase=?", CaseID) # vectorizing this was not successful. Tried to use "IDCase IN (?)" where ? is ','.join(CaseIDs)
    row=cursor.fetchone()
    if row is None: # Case is not in database
        try: # insert the new case
            print 'inserting Case ' + caseInfo[0]
            # IDcase (0), IDParentCase (1), Title (2), Project (3), Area (4), Category (5), AssignedTo (6), Priority (7), Status (8), OpenedDate (9), ClosedDate (10), OpenedBy (11), Milestone (12), ResolvedBy (13), ClosedBy (14)
            cursor.execute('INSERT INTO dbo.[Case] (IDCase, IDParentCase, Title, Project, Area, Category, AssignedTo, Priority, Status, OpenedDate, ClosedDate, OpenedBy, Milestone, ResolvedBy, ClosedBy) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', caseInfo)
            conn.commit()
        except Exception as e:
            print(e)
            conn.rollback()
    else: # update the case
        try:
            print 'updating Case ' + caseInfo[0]
            cursor.execute('UPDATE dbo.[Case] SET AssignedTo=?, Priority=?, Status=?, OpenedDate=?, ClosedDate=?, Milestone=?, ResolvedBy=?, ClosedBy=?, IDParentCase=? WHERE IDCase=?', (caseInfo[6],caseInfo[7],caseInfo[8],caseInfo[9],caseInfo[10],caseInfo[12],caseInfo[13],caseInfo[14],caseInfo[1],caseInfo[0]))
        except Exception as e:
            print(e)
            conn.rollback()

cursor.close()
conn.close()


# --------------------------------------------------------------
# SECTION: Update fbSettings to tell it the latest case that was looked at.
# --------------------------------------------------------------


with open(SETTINGSFILE, 'r') as file:
    data=file.readlines()

data[2] = 'LASTRECORDED="' + str(maxDate.replace(second=0,microsecond=0).strftime('%Y-%m-%d %H:%M:%SZ')) + '"'

print "last update time = "
print maxDate

with open(SETTINGSFILE, 'w') as file:
    file.writelines(data)

'''
# get all newly OPENED cases
respOpened = fb.listCases(sFilter="1056", cols='ixBug,sTitle,sProject,sArea,sCategory,sPersonAssignedTo,sPriority,sStatus,dtOpened')
# get all newly CLOSED cases
respClosed = fb.listCases(sFilter="1057", cols='ixBug,sStatus,dtClosed')

#print respOpen.prettify()

#resp2 = fb.search(q="106085", cols="dtOpened")
#print datetime.strptime(resp2.cases.case.dtopened.string,'%Y-%m-%dT%H:%M:%SZ').strftime('%Y%m%d')
#print datetime.strptime(resp2.cases.case.dtopened.string,'%Y-%m-%dT%H:%M:%SZ')

#print datetime.strptime(respOpened.cases.case.dtopened.string,'%Y-%m-%dT%H:%M:%SZ')
#print datetime.strptime(respClosed.cases.case.dtclosed.string,'%Y-%m-%dT%H:%M:%SZ')

insertValues = []
for case in respOpened.cases.childGenerator():
    # get Opened By user
    IDOpenedBy = case.ixpersonopenedby.string
    StrOpenedBy = ''
    if IDOpenedBy in PersonsList:
        StrOpenedBy = PersonsList[IDOpenedBy]
    else:
        # person was not recorded yet, search FogBugz for user
        person = fb.viewPerson(ixPerson=IDOpenedBy)
        PersonsList[IDOpenedBy] = StrOpenedBy = person.sfullname.string

    # get Parent Case
    StrParentCase = case.ixbugparent.string
    if StrParentCase == '0':
        StrParentCase = None

    # return IDcase, IDParentCase, Title, Project, Area, Category, AssignedTo, Priority, Status, OpenedDate, OpenedBy, Milestone
    insertValues.append((case['ixbug'], StrParentCase, case.stitle.string, case.sproject.string, case.sarea.string, case.scategory.string, case.spersonassignedto.string, case.spriority.string, case.sstatus.string, datetime.strptime(case.dtopened.string,'%Y-%m-%dT%H:%M:%SZ'), StrOpenedBy, case.sfixfor.string))

for case in respOpened.cases.childGenerator():
    # Must put in this order: IDCase, Title, Project, Area, Category, AssignedTo, Priority, Status, OpenedDate
    insertValues.append((case['ixbug'], case.stitle.string, case.sproject.string, case.sarea.string, case.scategory.string, case.spersonassignedto.string, case.spriority.string, case.sstatus.string, datetime.strptime(case.dtopened.string,'%Y-%m-%dT%H:%M:%SZ')))

updateValues = []
for case in respClosed.cases.childGenerator():
    # get Date Closed
    StrDtClosed = ''
    if case.dtclosed.string is not None:
        StrDtClosed = datetime.strptime(case.dtclosed.string,'%Y-%m-%dT%H:%M:%SZ')
        insertDates.update([datetime.strptime(case.dtopened.string,'%Y-%m-%dT%H:%M:%SZ').strftime('%Y%m%d'), datetime.strptime(case.dtclosed.string,'%Y-%m-%dT%H:%M:%SZ').strftime('%Y%m%d')])
    else:
        StrDtClosed = None
        insertDates.update([datetime.strptime(case.dtopened.string,'%Y-%m-%dT%H:%M:%SZ').strftime('%Y%m%d')])
    
    # get Resolved By user
    IDResolvedBy = case.ixpersonresolvedby.string
    StrResolvedBy = ''
    if IDResolvedBy == '0':
        StrResolvedBy = None
    else:
        if IDResolvedBy in PersonsList:
            StrResolvedBy = PersonsList[IDResolvedBy]
        else:
            person = fb.viewPerson(ixPerson=IDResolvedBy)
            PersonsList[IDResolvedBy] = StrResolvedBy = person.sfullname.string

    # get Closed By user
    IDClosedBy = case.ixpersonclosedby.string
    StrClosedBy = ''
    if IDClosedBy == '0':
        StrClosedBy = None
    else:
        if IDClosedBy in PersonsList:
            StrClosedBy = PersonsList[IDClosedBy]
        else:
            person = fb.viewPerson(ixPerson=IDClosedBy)
            PersonsList[IDClosedBy] = StrClosedBy = person.sfullname.string
    
    # Must put in this order: ClosedDate, Status, ResolvedBy, ClosedBy, IDCase
    updateValues.append((StrDtClosed, case.sstatus.string, StrResolvedBy, StrClosedBy, case['ixbug']))

for val in insertValues:
    print val

print '-------UPDATE:-------'
for val in updateValues:
    print val


# Connect to SQL and add/change data
conn = pyodbc.connect('DRIVER={SQL Server};SERVER=PC-Longphi;DATABASE=FogBugz')
cursor = conn.cursor()

# Add today to Time Table
try:
    dt = date.today().strftime('%Y-%m-%d')
    cursor.execute("""INSERT Into dbo.[TimeTable]
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
    ?,
    Day(?),
    DATEPART(dy, ?),
    DATENAME(dw, ?),
    DATEPART(wk, ?),
    DATEPART(mm, ?),
    DATENAME(mm, ?),
    'Q'+Cast(DATENAME(qq, ?) as varchar(1)),
    Year(?)
    )""", ((dt),)*9 #(dt, dt, dt, dt, dt, dt, dt, dt, dt)
    )
    #dayOfYear = dt.timetuple().tm_yday
    #dayOfWeek = calendar.day_name[dt.weekday()]
    #cursor.execute('INSERT INTO dbo.[TimeTable] (IdDate, Day, DayofYear, DayofWeekName, Week, Month, MonthName, Quarter, Year) VALUES (?,?,?,?,?,?,?,?,?)', dt, dt.day, dayOfYear, )
    conn.commit()
except:
    conn.rollback()

for x in insertValues:
    try:
        # IDcase, IDParentCase, Title, Project, Area, Category, AssignedTo, Priority, Status, OpenedDate, ClosedDate, OpenedBy, Milestone, ResolvedBy, ClosedBy
        cursor.execute('INSERT INTO dbo.[Case] (IDCase, IDParentCase, Title, Project, Area, Category, AssignedTo, Priority, Status, OpenedDate, ClosedDate, OpenedBy, Milestone, ResolvedBy, ClosedBy) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', x)
        print 'inserted Case ' + x[0]
        conn.commit()
    except Exception as e:
        print(e)
        conn.rollback()

for x in updateValues:
    try:
        cursor.execute('UPDATE dbo.[Case] SET ClosedDate=?, Status=?, ResolvedBy, ClosedBy WHERE IDCase=?', x)
        conn.commit()
    except:
        conn.rollback()
cursor.close()
conn.close()

# INSERT New cases into database
try:
    cursor.executemany('INSERT INTO dbo.[Case] (IDCase, Title, Project, Area, Category, AssignedTo, Priority, Status, OpenedDate) VALUES (?,?,?,?,?,?,?,?,?)', insertValues)
    conn.commit()
except:
    conn.rollback()

# UPDATE status of cases to CLOSED
try:
    cursor.executemany('UPDATE dbo.[Case] SET ClosedDate=?, Status=? WHERE IDCase=?', updateValues)
    conn.commit()
except:
    conn.rollback()

cursor.close()
conn.close()
'''
