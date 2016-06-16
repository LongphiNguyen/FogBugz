#This script will print a list of all overdue cases assigned to me
from fogbugz import FogBugz
from datetime import datetime, timedelta
import fbSettings # fbSettings.txt
import pyodbc
from datetime import datetime
from datetime import date
import calendar
import time
'''
# Fill in the following values as appropriate to your installation
#S_FOGBUGZ_URL   = 'https://vsg.fogbugz.com/'
#S_EMAIL         = 'longphi.nguyen@vsgsolutions.com'
#S_PASSWORD      = '---'

#fb = FogBugz(S_FOGBUGZ_URL)
#fb.logon(S_EMAIL, S_PASSWORD)
'''
print fbSettings.URL
print fbSettings.TOKEN

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

# Remake: Get all cases by using a sequential iteration, not in bulk
respOpened = fb.listCases(sFilter="1056", cols='ixBug')#,sTitle,sProject,sArea,sCategory,sPersonAssignedTo,sPriority,sStatus,dtOpened,dtClosed')
# get max ID
maxID=0
for case in respOpened.cases.childGenerator():
    if case['ixbug']>maxID:
        maxID=case['ixbug']

def insertToSQL(localminID, localmaxID, PersonsList):
    "Go through case=minID to case=maxID and get their attributes. Then insert those values into the database."
    # Now iterate from minID to maxID
    insertValues = [] # values to insert into dbo.Case
    insertDates = set() # values to insert into dbo.TimeTable
    caseNumbers = ','.join([str(s) for s in range(localminID, localmaxID+1)])
    #for i in range(localminID,localmaxID+1):
    #    case=fb.search(q="case:"+str(i), cols='ixBug,sTitle,sProject,sArea,sCategory,sPersonAssignedTo,sPriority,sStatus,dtOpened,dtClosed')
    resp=fb.search(q=caseNumbers, cols='ixBug,sTitle,sProject,sArea,sCategory,sPersonAssignedTo,sPriority,sStatus,dtOpened,dtClosed,ixPersonOpenedBy,ixBugParent,sFixFor,ixPersonResolvedBy,ixPersonClosedBy,ixKanban')
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
        if case.dtclosed.string is not None:
            StrDtClosed = datetime.strptime(case.dtclosed.string,'%Y-%m-%dT%H:%M:%SZ')
            insertDates.update([datetime.strptime(case.dtopened.string,'%Y-%m-%dT%H:%M:%SZ').strftime('%Y%m%d'), datetime.strptime(case.dtclosed.string,'%Y-%m-%dT%H:%M:%SZ').strftime('%Y%m%d')])
        else:
            StrDtClosed = None
            insertDates.update([datetime.strptime(case.dtopened.string,'%Y-%m-%dT%H:%M:%SZ').strftime('%Y%m%d')])

        # get Parent Case
        StrParentCase = case.ixbugparent.string
        if StrParentCase == '0':
            StrParentCase = None

        # Kanban
        StrKanban = None
        if case.ixkanban.string is not None:
            StrKanban = case.ixkanban.string
        
        # return IDcase, IDParentCase, Title, Project, Area, Category, AssignedTo, Priority, Status, OpenedDate, ClosedDate, OpenedBy, Milestone, ResolvedBy, ClosedBy, Kanban
        insertValues.append((case['ixbug'], StrParentCase, case.stitle.string, case.sproject.string, case.sarea.string, case.scategory.string, case.spersonassignedto.string, case.spriority.string, case.sstatus.string, datetime.strptime(case.dtopened.string,'%Y-%m-%dT%H:%M:%SZ'), StrDtClosed, StrOpenedBy, case.sfixfor.string, StrResolvedBy, StrClosedBy, StrKanban))
    
    insertDatesTuples = [((x),)*9 for x in insertDates]
    
    # Connect to SQL and add/change data
    conn = pyodbc.connect('DRIVER={SQL Server};SERVER=PC-Longphi;DATABASE=FogBugz')
    cursor = conn.cursor()
    
    # Add all unique dates to Time Table
    for x in insertDatesTuples:
        try:
            cursor.execute("""INSERT INTO [dbo].[TimeTable] ([IdDate],[Day],[DayofYear],[Dayofweekname],[Week],[Month],[MonthName],[Quarter],[Year]) Values (?,Day(?),DATEPART(dy, ?),DATENAME(dw, ?),DATEPART(wk, ?),DATEPART(mm, ?),DATENAME(mm, ?),'Q'+Cast(DATENAME(qq, ?) as varchar(1)),Year(?))""", x)
            print 'inserted Time ' + x[0]
            conn.commit()
        except Exception as e:
            print(e)
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
    
    cursor.close()
    conn.close()
    return PersonsList;

PersonsList = {}
minID=1
step=4999 # 1-10000, 10001-20000, etc
while True:
    if minID+step < maxID:
        print "LOOKING AT CASES: " + str(minID) + " to " + str(minID+step) + ", stopping at " + str(maxID) 
        PersonsList = insertToSQL(minID, minID+step, PersonsList)
        minID=minID+step+1
    else:
        PersonsList = insertToSQL(minID, maxID, PersonsList)
        print "LOOKING AT CASES: " + str(minID) + " to " + str(maxID)
        minID=maxID
        break
    time.sleep(5)

''' Best so far
# get ALL cases
respOpened = fb.listCases(sFilter="1058", cols='ixBug,sTitle,sProject,sArea,sCategory,sPersonAssignedTo,sPriority,sStatus,dtOpened,dtClosed', max=10)

insertValues = []
insertDates = set()
for case in respOpened.cases.childGenerator():
    # Must put in this order: IDCase, Title, Project, Area, Category, AssignedTo, Priority, Status, OpenedDate, ClosedDate
    if case.dtclosed.string is not None:
        insertValues.append((case['ixbug'], case.stitle.string, case.sproject.string, case.sarea.string, case.scategory.string, case.spersonassignedto.string, case.spriority.string, case.sstatus.string, datetime.strptime(case.dtopened.string,'%Y-%m-%dT%H:%M:%SZ'), datetime.strptime(case.dtclosed.string,'%Y-%m-%dT%H:%M:%SZ')))
        #insertDates.update([case.dtopened.string, case.dtclosed.string])
        insertDates.update([datetime.strptime(case.dtopened.string,'%Y-%m-%dT%H:%M:%SZ').strftime('%Y%m%d'), datetime.strptime(case.dtclosed.string,'%Y-%m-%dT%H:%M:%SZ').strftime('%Y%m%d')])
    else:
        insertValues.append((case['ixbug'], case.stitle.string, case.sproject.string, case.sarea.string, case.scategory.string, case.spersonassignedto.string, case.spriority.string, case.sstatus.string, datetime.strptime(case.dtopened.string,'%Y-%m-%dT%H:%M:%SZ'), 'NULL'))
        insertDates.update([datetime.strptime(case.dtopened.string,'%Y-%m-%dT%H:%M:%SZ').strftime('%Y%m%d')])

insertDatesTuples = [((x),)*9 for x in insertDates]

# Connect to SQL and add/change data
conn = pyodbc.connect('DRIVER={SQL Server};SERVER=PC-Longphi;DATABASE=FogBugz')
cursor = conn.cursor()

# Add all unique dates to Time Table
for x in insertDatesTuples:
    try:
        cursor.execute("""INSERT INTO [dbo].[TimeTable] ([IdDate],[Day],[DayofYear],[Dayofweekname],[Week],[Month],[MonthName],[Quarter],[Year]) Values (?,Day(?),DATEPART(dy, ?),DATENAME(dw, ?),DATEPART(wk, ?),DATEPART(mm, ?),DATENAME(mm, ?),'Q'+Cast(DATENAME(qq, ?) as varchar(1)),Year(?))""", x)
        print 'inserted Time ' + x[0]
        conn.commit()
    except:
        conn.rollback()

for x in insertValues:
    try:
        cursor.execute('INSERT INTO dbo.[Case] (IDCase, Title, Project, Area, Category, AssignedTo, Priority, Status, OpenedDate, ClosedDate) VALUES (?,?,?,?,?,?,?,?,?,?)', x)
        print 'inserted Case ' + x[0]
        conn.commit()
    except:
        conn.rollback()

'''

''' # do the inserts in one go, rather than iterating over each row and inserting (but a single error will cause it to fail)
try:
    #dt = date.today().strftime('%Y-%m-%d')
    cursor.executemany("""INSERT INTO [dbo].[TimeTable] ([IdDate],[Day],[DayofYear],[Dayofweekname],[Week],[Month],[MonthName],[Quarter],[Year]) Values (?,Day(?),DATEPART(dy, ?),DATENAME(dw, ?),DATEPART(wk, ?),DATEPART(mm, ?),DATENAME(mm, ?),'Q'+Cast(DATENAME(qq, ?) as varchar(1)),Year(?))""", insertDatesTuples)
    #dayOfYear = dt.timetuple().tm_yday
    #dayOfWeek = calendar.day_name[dt.weekday()]
    #cursor.execute('INSERT INTO dbo.[TimeTable] (IdDate, Day, DayofYear, DayofWeekName, Week, Month, MonthName, Quarter, Year) VALUES (?,?,?,?,?,?,?,?,?)', dt, dt.day, dayOfYear, )
    conn.commit()
except:
    conn.rollback()

# INSERT All cases into database
try:
    cursor.executemany('INSERT INTO dbo.[Case] (IDCase, Title, Project, Area, Category, AssignedTo, Priority, Status, OpenedDate, ClosedDate) VALUES (?,?,?,?,?,?,?,?,?,?)', insertValues)
    conn.commit()
except:
    conn.rollback()

cursor.close()
conn.close()
'''
