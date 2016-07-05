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

#maxDate = datetime.strptime(fbSettings.LASTRECORDED,'%Y-%m-%d %H:%M:%SZ')
# class for cases, to improve readability
class Case:
    def __init__(self):
        # case info
        self.IDCase = 0
        self.IDParentCase = 0
        self.Title = ""
        self.Status = ""
        self.Project = ""
        self.Area = ""
        self.Category = ""
        self.Priority = ""
        self.Milestone = ""
        # people and IDS
        self.IDAssignedTo = 0
        self.AssignedTo = ""
        self.IDOpenedBy = 0
        self.OpenedBy = ""
        self.IDResolvedBy = 0
        self.ResolvedBy = ""
        self.IDClosedBy = 0
        self.ClosedBy = ""
        self.IDLastEditedBy = 0
        self.LastEditedBy = ""
        # dates
        self.OpenedDate = None
        self.ClosedDate = None
        self.ResolvedDate = None
        self.DueDate = None
        self.LastUpdatedDate = None
        # hours
        self.hrsElapsed = 0.00
        self.hrsCurrEst = 0.00
        self.hrsOrigEst = 0.00
        self.hrsElapsedExtra = 0.00
        # kanban
        self.IDKanban = 0
        self.IDKanbanColor = 0
    
    def returnInfo(self):
        return (self.IDCase, self.IDParentCase, self.Title, self.Status, self.Project, self.Area, self.Category, self.Priority, self.Milestone,
                self.IDAssignedTo, self.AssignedTo, self.IDOpenedBy, self.OpenedBy, self.IDResolvedBy, self.ResolvedBy, self.IDClosedBy,
                self.ClosedBy, self.IDLastEditedBy, self.LastEditedBy, self.OpenedDate, self.ClosedDate, self.ResolvedDate, self.DueDate,
                self.LastUpdatedDate, self.hrsElapsed, self.hrsCurrEst, self.hrsOrigEst, self.hrsElapsedExtra, self.IDKanban, self.IDKanbanColor)

# requires PersonsList = {} to be defined in parent scope
def insertToSQL(localminID, localmaxID, PersonsList):
    "Go through case=minID to case=maxID and get their attributes. Then insert those values into the database."
    # Now iterate from minID to maxID
    insertValues = [] # values to insert into dbo.Case
    insertDates = set() # values to insert into dbo.TimeTable
    caseNumbers = ','.join([str(s) for s in range(localminID, localmaxID+1)])
    #for i in range(localminID,localmaxID+1):
    #    case=fb.search(q="case:"+str(i), cols='ixBug,sTitle,sProject,sArea,sCategory,sPersonAssignedTo,sPriority,sStatus,dtOpened,dtClosed')

    # --------------------------
    # defining functions to be used
    # --------------------------
    def getUserName(userID):
        if userID == '0' or userID == '-1':
            return None, None
        else:
            if userID in PersonsList:
                return userID, PersonsList[userID]
            else:
                print 'userID: ' + str(userID)
                person = fb.viewPerson(ixPerson=userID)
                if person.sfullname is None: # no name returned
                    return None, None
                PersonsList[userID] = userName = person.sfullname.string
                return userID, userName

    # formatDt(dt) takes in a date string (case.dt.string) and formats it to be inserted into dbo.Case. Also places the date into insertDates set to be inserted into dbo.Time
    def formatDt(dt):
        if dt is not None:
            formatted=datetime.strptime(dt,'%Y-%m-%dT%H:%M:%SZ')
            insertDates.update([formatted.strftime('%Y%m%d')])

            #if formatted > maxDate:
                #maxDate=formatted
            return formatted
        else:
            return None
    
    resp=fb.search(q=caseNumbers, cols='ixBug,sTitle,sProject,sArea,sCategory,ixPersonAssignedTo,sPersonAssignedTo,sPriority,sStatus,dtOpened,dtClosed,ixPersonOpenedBy,ixBugParent,sFixFor,ixPersonResolvedBy,ixPersonClosedBy,dtResolved,dtDue,dtLastUpdated,ixKanban,ixPersonLastEditedBy,hrsElapsed,hrsCurrEst,hrsOrigEst,hrsElapsedExtra,plugin_kanbanboard_at_ergonlabs_com_ixkanbancolumn,plugin_kanbanboard_at_ergonlabs_com_ncolor')#include Kanban to see other Kanban fields (though not useful)
    for case in resp.cases.childGenerator():
        CaseObj = Case()
        CaseObj.IDCase = case['ixbug']
        # ----------
        # user name stuff
        # ----------
        print CaseObj.IDCase
        # get Opened By user
        CaseObj.IDOpenedBy, CaseObj.OpenedBy = getUserName(case.ixpersonopenedby.string)
        # get Resolved By user
        CaseObj.IDResolvedBy, CaseObj.ResolvedBy = getUserName(case.ixpersonresolvedby.string)
        # get Closed By user
        CaseObj.IDClosedBy, CaseObj.ClosedBy = getUserName(case.ixpersonclosedby.string)
        # get Last Edited By user
        CaseObj.IDLastEditedBy, CaseObj.LastEditedBy = getUserName(case.ixpersonlasteditedby.string)
        # get Assigned To user
        CaseObj.IDAssignedTo = case.ixpersonassignedto.string
        CaseObj.AssignedTo = case.spersonassignedto.string # oddly, this is the only name that can be obtained directly from the query

        # ----------
        # date stuff
        # ----------

        # get Date Opened
        CaseObj.OpenedDate = formatDt(case.dtopened.string)
        # get Date Closed
        CaseObj.ClosedDate = formatDt(case.dtclosed.string)
        # get Date Resolved
        CaseObj.ResolvedDate = formatDt(case.dtresolved.string)
        # get Date Due
        CaseObj.DueDate = formatDt(case.dtdue.string)
        # get Last Updated
        CaseObj.LastUpdatedDate = formatDt(case.dtlastupdated.string)

        # ----------
        # other info
        # ----------
        
        # get Parent Case
        StrParentCase = case.ixbugparent.string
        if StrParentCase == '0':
            StrParentCase = None
        CaseObj.IDParentCase = StrParentCase
        
        # Kanban
        CaseObj.IDKanban= case.plugin_kanbanboard_at_ergonlabs_com_ixkanbancolumn.string
        CaseObj.IDKanbanColor= case.plugin_kanbanboard_at_ergonlabs_com_ncolor.string

        # hours elapsed, estimated, original, extra
        CaseObj.hrsElapsed = case.hrselapsed.string#round(float(case.hrselapsed.string),3)
        CaseObj.hrsCurrEst = case.hrscurrest.string#round(float(case.hrscurrest.string),3)
        CaseObj.hrsOrigEst = case.hrsorigest.string#round(float(case.hrsorigest.string),3)
        CaseObj.hrsElapsedExtra = case.hrselapsedextra.string#round(float(case.hrselapsedextra.string),3)

        # (StrKanban)
        CaseObj.Title = case.stitle.string
        CaseObj.Status = case.sstatus.string
        CaseObj.Project = case.sproject.string
        CaseObj.Area = case.sarea.string
        CaseObj.Category = case.scategory.string
        CaseObj.Priority = case.spriority.string
        CaseObj.Milestone = case.sfixfor.string
        
        # return the values as a tuple, ordered as in Case.returnInfo()
        insertValues.append(CaseObj.returnInfo())
    
    #insertDatesTuples = [((x),)*9 for x in insertDates]
    
    # Connect to SQL and add/change data
    conn = pyodbc.connect('DRIVER={SQL Server};SERVER='+SERVER+ ';DATABASE='+DATABASE)
    cursor = conn.cursor()
    
    # Add all unique dates to Time Table
    #for x in insertDatesTuples:
    #    try:
    #        cursor.execute("""INSERT INTO [dbo].[TimeTable] ([IdDate],[Day],[DayofYear],[Dayofweekname],[Week],[Month],[MonthName],[Quarter],[Year]) Values (?,Day(?),DATEPART(dy, ?),DATENAME(dw, ?),DATEPART(wk, ?),DATEPART(mm, ?),DATENAME(mm, ?),'Q'+Cast(DATENAME(qq, ?) as varchar(1)),Year(?))""", x)
    #        print 'inserted Time ' + x[0]
    #        conn.commit()
    #    except Exception as e:
    #        conn.rollback()

    for x in insertValues:
        try:
            #(IDCase, IDParentCase, Title, Status, Project, Area, Category, Priority, Milestone, IDAssignedTo, AssignedTo, IDOpenedBy, OpenedBy, IDResolvedBy, ResolvedBy, IDClosedBy, ClosedBy, IDLastEditedBy, LastEditedBy, OpenedDate, ClosedDate, ResolvedDate, DueDate, LastUpdatedDate, hrsElapsed, hrsCurrEst, hrsOrigEst, hrsElapsedExtra, IDKanban, IDKanbanColor)
            cursor.execute("""INSERT INTO dbo.[Case]
                                   (IDCase, IDParentCase, Title, Status, Project, Area, Category, Priority, Milestone, IDAssignedTo, AssignedTo, IDOpenedBy, OpenedBy, IDResolvedBy, ResolvedBy, IDClosedBy, ClosedBy, IDLastEditedBy, LastEditedBy, OpenedDate, ClosedDate, ResolvedDate, DueDate, LastUpdatedDate, hrsElapsed, hrsCurrEst, hrsOrigEst, hrsElapsedExtra, IDKanban, IDKanbanColor)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", x)
            print 'inserted Case ' + x[0]
            conn.commit()
        except Exception as e:
            #print(e)
            print x[0] + ' failed'
            print(e)
            conn.rollback()
    
    cursor.close()
    conn.close()
    return PersonsList;

# --------------------------
# Get all cases by using a sequential iteration, not in bulk. Not done in bulk because I couldn't figure out how to do the SQL insert in bulk
# --------------------------
respOpened = fb.listCases(sFilter="1056", cols='ixBug')#,sTitle,sProject,sArea,sCategory,sPersonAssignedTo,sPriority,sStatus,dtOpened,dtClosed')
# get max ID
maxID=0
for case in respOpened.cases.childGenerator():
    if case['ixbug']>maxID:
        maxID=case['ixbug']

maxID=int(maxID)

PersonsList = {}
minID=0
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
    time.sleep(3)



# --------------------------------------------------------------
# SECTION: Update fbSettings to tell it the latest case that was looked at.
# --------------------------------------------------------------

'''
with open(SETTINGSFILE, 'r') as file:
    data=file.readlines()

data[2] = 'LASTRECORDED="' + str(maxDate.replace(second=0,microsecond=0).strftime('%Y-%m-%d %H:%M:%SZ')) + '"'

print "last update time = "
print maxDate

with open(SETTINGSFILE, 'w') as file:
    file.writelines(data)
'''

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
